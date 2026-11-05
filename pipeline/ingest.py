"""`make ingest`: fetch raw public files, verify checksums, and stage the columns we use.

Raw files (data/raw/, git-ignored) -> column-pruned Parquet (data/staging/, git-ignored).
All aggregation happens in dbt (`make transform`).
"""

from __future__ import annotations

import re
import sys
import warnings
import zipfile
from pathlib import Path

import pandas as pd

from pipeline.config import RAW, STAGING, STATE_FIPS
from pipeline.sources import ensure_raw, load_sources

# FARS table -> (zip kind, columns kept). Column names are identical in every year 2014-2023.
FARS_TABLES: dict[str, tuple[str, list[str]]] = {
    "accident": (
        "national_csv",
        [
            "STATE",
            "ST_CASE",
            "FATALS",
            "HOUR",
            "MINUTE",
            "NOT_HOUR",
            "NOT_MIN",
            "ARR_HOUR",
            "ARR_MIN",
            "HOSP_HR",
            "HOSP_MN",
        ],
    ),
    "person": ("national_csv", ["STATE", "ST_CASE", "VEH_NO", "PER_NO", "PER_TYP", "INJ_SEV"]),
    "midrvacc": ("national_csv", ["ST_CASE"] + [f"A{i}" for i in range(1, 11)]),
    "acc_aux": (
        "auxiliary_csv",
        [
            "STATE",
            "ST_CASE",
            "FATALS",
            "A_RU",
            "A_ROADFC",
            "A_SPCRA",
            "A_PED_F",
            "A_PEDAL_F",
            "A_MC",
            "A_D15_20",
            "A_D65PLS",
            "A_RD",
            "A_INTSEC",
        ],
    ),
    "per_aux": ("auxiliary_csv", ["ST_CASE", "VEH_NO", "PER_NO", "A_PTYPE", "A_PERINJ", "A_RESTUSE"]),
    "veh_aux": ("auxiliary_csv", ["ST_CASE", "VEH_NO", "A_BODY"]),
}


def _norm(col: str) -> str:
    """Normalize a header cell: drop quotes, whitespace, and a UTF-8 BOM decoded as latin-1."""
    return col.replace("\u00ef\u00bb\u00bf", "").strip('"\ufeff ')


def _find_member(zf: zipfile.ZipFile, table: str) -> zipfile.ZipInfo:
    """Locate a table inside a FARS zip; names differ in case and folder across years."""
    hits = [i for i in zf.infolist() if re.fullmatch(rf"{table}\.csv", Path(i.filename).name, re.I)]
    if len(hits) != 1:
        raise RuntimeError(f"Expected one {table}.csv in {zf.filename}, found {[h.filename for h in hits]}")
    return hits[0]


def stage_fars(doc: dict) -> None:
    by_year: dict[int, dict[str, Path]] = {}
    for e in doc["fars"]:
        if e["file_status"] != "final":
            raise SystemExit(f"{e['id']} is not a FINAL file; refusing to stage it for analysis")
        kind = "auxiliary_csv" if e["id"].endswith("auxiliary_csv") else "national_csv"
        by_year.setdefault(e["year"], {})[kind] = RAW / e["local_path"]

    for table, (kind, cols) in FARS_TABLES.items():
        out_dir = STAGING / "fars" / table
        out_dir.mkdir(parents=True, exist_ok=True)
        for year, paths in sorted(by_year.items()):
            with zipfile.ZipFile(paths[kind]) as zf, zf.open(_find_member(zf, table)) as fh:
                # Only integer-coded columns are kept, so latin-1 decoding is safe for every year.
                df = pd.read_csv(
                    fh, usecols=lambda c, cols=cols: _norm(c) in cols, encoding="latin-1", low_memory=False
                )
            df.columns = [_norm(c) for c in df.columns]
            missing = set(cols) - set(df.columns)
            if missing:
                raise RuntimeError(f"{table} {year}: missing columns {sorted(missing)}")
            df = df[cols].apply(pd.to_numeric, errors="raise").astype("int64")
            df.insert(0, "YEAR", year)
            df.to_parquet(out_dir / f"{year}.parquet", index=False)
        print(f"staged fars/{table}: {sorted(by_year)}", file=sys.stderr)


def stage_population(doc: dict, years: list[int]) -> None:
    frames = []
    for e in doc["population"]:
        df = pd.read_csv(RAW / e["local_path"], dtype={"STATE": "int64", "SUMLEV": str}, encoding="latin-1")
        df = df[df["SUMLEV"].astype(str).str.zfill(3) == "040"]
        if "SEX" in df.columns:  # intercensal characteristics file: sum totals over race and age
            df = df[(df["SEX"] == 0) & (df["ORIGIN"] == 0)]
        pop_cols = {int(c[-4:]): c for c in df.columns if re.fullmatch(r"POPESTIMATE\d{4}", c)}
        use = [y for y in years if y in pop_cols]
        g = df.groupby("STATE")[[pop_cols[y] for y in use]].sum()
        g.columns = use
        long = g.reset_index().melt(id_vars="STATE", var_name="YEAR", value_name="POPULATION")
        long["SOURCE_ID"] = e["id"]
        frames.append(long)
    pop = pd.concat(frames)
    # Prefer the newest source when years overlap (none expected, but be explicit).
    pop = pop.sort_values(["STATE", "YEAR", "SOURCE_ID"]).drop_duplicates(["STATE", "YEAR"], keep="last")
    pop = pop[pop["STATE"].isin(STATE_FIPS)]
    check = pop.groupby("YEAR").size()
    if (check != len(STATE_FIPS)).any() or sorted(check.index) != years:
        raise RuntimeError(f"Population coverage incomplete: {check.to_dict()}")
    out = STAGING / "population.parquet"
    pop.astype({"STATE": "int64", "YEAR": "int64", "POPULATION": "int64"}).to_parquet(out, index=False)
    print(f"staged population: {len(pop)} rows", file=sys.stderr)


VM2_CLASSES = [
    "INTERSTATE",
    "OTHER FREEWAYS AND EXPRESSWAYS",
    "OTHER PRINCIPAL ARTERIAL",
    "MINOR ARTERIAL",
    "MAJOR COLLECTOR",
    "MINOR COLLECTOR",
    "LOCAL",
    "TOTAL",
]
# VM-2 functional systems -> FARS auxiliary A_ROADFC groups (collectors combined, as in A_ROADFC).
VM2_TO_FC = {
    "INTERSTATE": "interstate",
    "OTHER FREEWAYS AND EXPRESSWAYS": "freeway_expressway",
    "OTHER PRINCIPAL ARTERIAL": "other_principal_arterial",
    "MINOR ARTERIAL": "minor_arterial",
    "MAJOR COLLECTOR": "collector",
    "MINOR COLLECTOR": "collector",
    "LOCAL": "local",
}


def parse_vm2(path: Path, year: int) -> pd.DataFrame:
    """Parse an FHWA Highway Statistics VM-2 sheet into state rows (millions of VMT).

    Layout (identical 2014-2023): STATE | 8 rural columns (7 functional systems + TOTAL) |
    8 urban columns | grand TOTAL. Header text is checked before any value is read.
    """
    with warnings.catch_warnings():  # xlrd deprecation notice for legacy .xls files
        warnings.simplefilter("ignore")
        sheet = pd.read_excel(path, sheet_name="A", header=None)
    hdr = next(i for i in range(len(sheet)) if str(sheet.iat[i, 0]).strip().upper() == "STATE")

    def header(j: int) -> str:
        parts = [str(sheet.iat[r, j]) for r in range(hdr - 2, hdr + 2) if str(sheet.iat[r, j]) != "nan"]
        return re.sub(r"\s+", " ", " ".join(parts)).replace("RURAL ", "").replace("URBAN ", "").strip()

    got = [header(j) for j in range(1, 18)]
    expected = VM2_CLASSES + VM2_CLASSES + ["TOTAL"]
    if got != expected:
        raise RuntimeError(f"VM-2 {year}: unexpected header layout {got}")
    name_to_fips = {name.upper(): fips for fips, (_, name) in STATE_FIPS.items()}
    rows = []
    for i in range(hdr + 1, len(sheet)):
        name = re.sub(r"\s*\(\d+\)\s*$", "", str(sheet.iat[i, 0])).strip().upper()
        if name not in name_to_fips:
            continue
        vals = [float(sheet.iat[i, j]) for j in range(1, 18)]
        row = {
            "STATE": name_to_fips[name],
            "YEAR": year,
            "VMT_RURAL_MILLIONS": vals[7],
            "VMT_URBAN_MILLIONS": vals[15],
            "VMT_TOTAL_MILLIONS": vals[16],
        }
        for fc in dict.fromkeys(VM2_TO_FC.values()):
            row[f"VMT_FC_{fc.upper()}_MILLIONS"] = sum(
                v for k, v in zip(VM2_CLASSES[:7] * 2, vals[:7] + vals[8:15], strict=True) if VM2_TO_FC[k] == fc
            )
        rows.append(row)
    df = pd.DataFrame(rows)
    if len(df) != len(STATE_FIPS):
        raise RuntimeError(f"VM-2 {year}: parsed {len(df)} states, expected {len(STATE_FIPS)}")
    gap = (df["VMT_RURAL_MILLIONS"] + df["VMT_URBAN_MILLIONS"] - df["VMT_TOTAL_MILLIONS"]).abs().max()
    fc_gap = (df.filter(like="VMT_FC_").sum(axis=1) - df["VMT_TOTAL_MILLIONS"]).abs().max()
    if gap > 1.0 or fc_gap > 1.0:
        raise RuntimeError(f"VM-2 {year}: components do not sum to total (rural/urban {gap}, classes {fc_gap})")
    return df


def stage_vmt(doc: dict) -> None:
    df = pd.concat([parse_vm2(RAW / e["local_path"], int(e["years_used"])) for e in doc["vmt"]])
    df.sort_values(["STATE", "YEAR"]).to_parquet(STAGING / "vmt.parquet", index=False)
    print(f"staged vmt: {len(df)} rows", file=sys.stderr)


def main() -> None:
    doc = load_sources()
    ensure_raw(doc)
    STAGING.mkdir(parents=True, exist_ok=True)
    years = sorted({e["year"] for e in doc["fars"]})
    stage_fars(doc)
    stage_population(doc, years)
    stage_vmt(doc)


if __name__ == "__main__":
    main()
