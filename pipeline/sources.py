"""Source discovery, download, and verification.

`sources.yml` is a lockfile: every data file and every guidance document the project
uses is listed with its URL, size, checksum, and access date. `make ingest` downloads
the data files listed there and refuses to continue if a checksum does not match.

Run `python -m pipeline.sources refresh` to re-discover sources (e.g. when NHTSA
publishes a new FARS final year) and rewrite `sources.yml`.

FARS discovery
--------------
FARS files are discovered from NHTSA's official download listing. The human-facing
page (https://www.nhtsa.gov/file-downloads?p=nhtsa/downloads/FARS/) is served from the
S3 bucket behind https://static.nhtsa.gov; the page returns HTTP 403 to cloud IP ranges
(Akamai), so the pipeline reads the bucket's own XML listing instead. No URL is
constructed by guessing: each year's file key comes from the listing.

Whether a year is FINAL or an Annual Report File (ARF) is read from that year's
"Release Notes" text in the same listing ("first release of the YYYY FARS final file").
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import requests
import yaml

from pipeline.config import (
    FARS_BUCKET,
    FARS_HUMAN_LISTING,
    FARS_PREFIX,
    N_FINAL_YEARS,
    RAW,
    SOURCES_YML,
)

S3_NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
SESSION = requests.Session()  # default python-requests User-Agent


# --------------------------------------------------------------------------- HTTP


def http_get(url: str, *, stream: bool = False, timeout: int = 120) -> requests.Response:
    """GET with retries and exponential backoff. Raises on non-200."""
    last_exc: Exception | None = None
    for attempt in range(4):
        try:
            resp = SESSION.get(url, stream=stream, timeout=timeout)
            if resp.status_code == 200:
                return resp
            last_exc = RuntimeError(f"HTTP {resp.status_code} for {url}")
            if resp.status_code in (403, 404):
                break  # not transient
        except requests.RequestException as exc:  # network error: retry
            last_exc = exc
        time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_exc}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_file(path: Path) -> str:
    h = hashlib.md5()  # noqa: S324 - compared to S3 ETag, not used for security
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    resp = http_get(url, stream=True, timeout=600)
    with tmp.open("wb") as fh:
        for chunk in resp.iter_content(chunk_size=1 << 20):
            fh.write(chunk)
    tmp.replace(dest)
    return dest


# --------------------------------------------------------------------------- S3 listing


@dataclass(frozen=True)
class S3Object:
    key: str
    size: int
    etag: str
    last_modified: str

    @property
    def url(self) -> str:
        return f"{FARS_BUCKET}/{quote(self.key)}"

    @property
    def md5(self) -> str | None:
        # Single-part uploads have ETag == MD5 of the object; multipart ETags contain "-".
        return None if "-" in self.etag else self.etag


def list_bucket(prefix: str, delimiter: str | None = "/") -> tuple[list[S3Object], list[str]]:
    url = f"{FARS_BUCKET}/?prefix={quote(prefix)}"
    if delimiter:
        url += f"&delimiter={quote(delimiter)}"
    # Listing comes from NHTSA's own bucket; stdlib ElementTree does not resolve external entities.
    root = ET.fromstring(http_get(url).content)  # noqa: S314
    objects = [
        S3Object(
            key=c.findtext("s3:Key", namespaces=S3_NS),
            size=int(c.findtext("s3:Size", namespaces=S3_NS)),
            etag=c.findtext("s3:ETag", namespaces=S3_NS).strip('"'),
            last_modified=c.findtext("s3:LastModified", namespaces=S3_NS),
        )
        for c in root.findall("s3:Contents", S3_NS)
    ]
    prefixes = [p.findtext("s3:Prefix", namespaces=S3_NS) for p in root.findall("s3:CommonPrefixes", S3_NS)]
    return objects, prefixes


FINAL_PATTERNS = (
    r"first release of the {y} FARS final file",  # 2019+ wording
    r"first release of the FARS {y} final file",  # 2017 wording
    r"FARS {y} final (?:data|files?)",  # 2016, 2018 wording
    r"FARS final data for {y}",  # 2015 wording
)
ANNUAL_PATTERNS = (
    r"{y} FARS annual file",
    r"FARS {y} annual (?:data|files?)",
)


def classify_release(notes: str, year: int) -> str:
    """Classify a FARS year from its release-notes text.

    Returns 'final', 'annual_report_file', or 'not_stated'. A year whose notes ever announce
    the final file is final (the final file replaces the ARF in the same folder).
    """
    if any(re.search(p.format(y=year), notes, re.I) for p in FINAL_PATTERNS):
        return "final"
    if any(re.search(p.format(y=year), notes, re.I) for p in ANNUAL_PATTERNS):
        return "annual_report_file"
    return "not_stated"


def resolve_unstated(years: list[FarsYear]) -> None:
    """Resolve years whose release notes do not state ARF/final status.

    Per the FARS Analytical User's Manual (DOT HS 813 794, Introduction), the ARF "is replaced
    about a year later with a final file". Final files are therefore released in year order, so a
    year older than any year whose notes explicitly announce a final file must itself be final.
    """
    explicit_finals = [y.year for y in years if y.status == "final"]
    newest_final = max(explicit_finals) if explicit_finals else None
    for y in years:
        if y.status == "not_stated" and newest_final and y.year < newest_final:
            y.status = "final"
            y.status_basis = (
                "release notes do not state status; inferred final because a newer year "
                f"({newest_final}) is explicitly final and ARFs are replaced by finals in year order"
            )


@dataclass
class FarsYear:
    year: int
    status: str
    release_notes: S3Object
    national_csv: S3Object
    auxiliary_csv: S3Object
    status_basis: str = "stated in release notes"


def discover_fars_years() -> list[FarsYear]:
    """Read the official FARS listing and classify each year."""
    _, year_prefixes = list_bucket(FARS_PREFIX)
    years: list[FarsYear] = []
    for pfx in year_prefixes:
        m = re.fullmatch(rf"{re.escape(FARS_PREFIX)}(\d{{4}})/", pfx)
        if not m:
            continue
        year = int(m.group(1))
        if year < 2010:
            continue  # out of scope; keeps discovery fast
        top, _ = list_bucket(pfx)
        notes = next((o for o in top if re.search(r"release notes?\.txt$", o.key, re.I)), None)
        nat, _ = list_bucket(f"{pfx}National/")
        csv = next((o for o in nat if o.key.endswith(f"FARS{year}NationalCSV.zip")), None)
        aux = next((o for o in nat if o.key.endswith(f"FARS{year}NationalAuxiliaryCSV.zip")), None)
        if not (notes and csv and aux):
            continue
        status = classify_release(http_get(notes.url).text, year)
        years.append(FarsYear(year, status, notes, csv, aux))
    years.sort(key=lambda y: y.year)
    resolve_unstated(years)
    return years


def select_analysis_years(years: list[FarsYear], n: int = N_FINAL_YEARS) -> tuple[list[FarsYear], list[FarsYear]]:
    finals = [y for y in years if y.status == "final"]
    chosen = finals[-n:]
    newer_nonfinal = [y for y in years if y.year > chosen[-1].year and y.status != "final"]
    return chosen, newer_nonfinal


# --------------------------------------------------------------------------- static registry

CENSUS_INTERCENSAL = {
    "id": "census_popest_intercensal_2010_2020_state_alldata6",
    "name": (
        "SC-EST2020INT-ALLDATA6: Annual Intercensal State Resident Population Estimates for 6 Race "
        "Groups (5 Race Alone Groups and Two or More Races) by Age, Sex, and Hispanic Origin: "
        "April 1, 2010 to April 1, 2020"
    ),
    "publisher": "U.S. Census Bureau, Population Division",
    "table_id": "SC-EST2020INT-ALLDATA6",
    "url": "https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/intercensal/state/asrh/sc-est2020int-alldata6.csv",
    "documentation_url": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2020/intercensal/state/SC-EST2020INT-ALLDATA6.pdf",
    "years_used": "2014-2019",
    "role": "denominator: resident population (July 1), summed over SEX=0, ORIGIN=0, all races and ages",
    "local_path": "census/sc-est2020int-alldata6.csv",
}

CENSUS_VINTAGE = {
    "id": "census_popest_vintage2025_state_totals",
    "name": (
        "NST-EST2025-ALLDATA: Annual Population Estimates, Estimated Components of Resident Population "
        "Change, and Rates of the Components of Resident Population Change for the United States, States, "
        "District of Columbia, and Puerto Rico: April 1, 2020 to July 1, 2025"
    ),
    "publisher": "U.S. Census Bureau, Population Division",
    "table_id": "NST-EST2025-ALLDATA",
    "url": "https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/state/totals/NST-EST2025-ALLDATA.csv",
    "documentation_url": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2025/NST-EST2025-ALLDATA.pdf",
    "years_used": "2020-2023 (and any newer analysis year covered by the vintage)",
    "role": "denominator: resident population (July 1)",
    "local_path": "census/NST-EST2025-ALLDATA.csv",
}


def vmt_entry(year: int) -> dict:
    page = f"https://www.fhwa.dot.gov/policyinformation/statistics/{year}/vm2.cfm"
    html = http_get(page).text
    m = re.search(r'href="(xls/vm2\.xlsx?)"', html)
    if not m:
        raise RuntimeError(f"No VM-2 spreadsheet link found on {page}")
    url = f"https://www.fhwa.dot.gov/policyinformation/statistics/{year}/{m.group(1)}"
    return {
        "id": f"fhwa_highway_statistics_{year}_vm2",
        "name": f"Highway Statistics {year}, Table VM-2: Functional System Travel - {year}, Annual Vehicle-Miles",
        "publisher": "Federal Highway Administration, Office of Highway Policy Information",
        "table_id": "VM-2",
        "url": url,
        "documentation_url": page,
        "years_used": str(year),
        "role": "denominator: vehicle miles traveled (millions), state total, rural total, urban total",
        "local_path": f"vmt/{year}/{Path(m.group(1)).name}",
    }


DOCUMENTS = [
    {
        "id": "ctw_11th_2023",
        "name": (
            "Countermeasures That Work: A Highway Safety Countermeasure Guide for State Highway Safety "
            "Offices, 11th Edition, 2023 (Report No. DOT HS 813 490)"
        ),
        "publisher": "National Highway Traffic Safety Administration",
        "url": "https://rosap.ntl.bts.gov/view/dot/72947/dot_72947_DS1.pdf",
        "landing_url": "https://rosap.ntl.bts.gov/view/dot/72947",
        "edition_note": (
            "11th edition (November 2023) is the most recent edition that could be opened and verified. "
            "NHTSA's own site (nhtsa.gov/book/countermeasures-that-work) returned HTTP 403 from the build "
            "environment; a 2025 NHTSA procurement notice refers to a 12th edition, which could not be "
            "opened and is therefore not used."
        ),
    },
    {
        "id": "fhwa_psc_booklet",
        "name": (
            "Making Our Roads Safer: One Countermeasure at a Time - 28 Proven Safety Countermeasures (FHWA-SA-21-071)"
        ),
        "publisher": "Federal Highway Administration, Office of Safety",
        "url": "https://rosap.ntl.bts.gov/view/dot/88186/dot_88186_DS1.pdf",
        "landing_url": "https://rosap.ntl.bts.gov/view/dot/88186",
        "edition_note": (
            "Archived copy in the USDOT National Transportation Library (ROSA P). The live FHWA page "
            "highways.dot.gov/safety/proven-safety-countermeasures returned HTTP 403 from the build environment."
        ),
    },
    {
        "id": "usdot_nrss_2022",
        "name": "National Roadway Safety Strategy (U.S. DOT, January 2022)",
        "publisher": "U.S. Department of Transportation",
        "url": "https://rosap.ntl.bts.gov/view/dot/66388/dot_66388_DS1.pdf",
        "landing_url": "https://rosap.ntl.bts.gov/view/dot/66388",
        "edition_note": "Archived copy in ROSA P; transportation.gov/NRSS returned HTTP 403 from the build environment.",
    },
    {
        "id": "nhtsa_tsf_alcohol_2024_data",
        "name": "Traffic Safety Facts 2024 Data: Alcohol-Impaired Driving (DOT HS 813 815, June 2026)",
        "publisher": "National Highway Traffic Safety Administration, National Center for Statistics and Analysis",
        "url": "https://rosap.ntl.bts.gov/view/dot/91903/dot_91903_DS1.pdf",
        "landing_url": "https://rosap.ntl.bts.gov/view/dot/91903",
        "role": (
            "validation only: states the 2023 Final File totals (41,025 traffic fatalities; 12,382 "
            "alcohol-impaired-driving fatalities) used to check this pipeline's national figures"
        ),
    },
    {
        "id": "fars_analytical_users_manual_1975_2024",
        "name": "Fatality Analysis Reporting System Analytical User's Manual, 1975-2024 (DOT HS 813 794)",
        "publisher": "National Highway Traffic Safety Administration",
        "url": "https://crashstats.nhtsa.dot.gov/Api/Public/ViewPublication/813794",
        "landing_url": "https://crashstats.nhtsa.dot.gov/Api/Public/ViewPublication/813794",
    },
    {
        "id": "fars_auxiliary_manual_1982_2019",
        "name": "Fatality Analysis Reporting System (FARS) Auxiliary Datasets Analytical User's Manual, 1982-2019 (DOT HS 813 071)",
        "publisher": "National Highway Traffic Safety Administration",
        "url": "https://crashstats.nhtsa.dot.gov/Api/Public/ViewPublication/813071",
        "landing_url": "https://crashstats.nhtsa.dot.gov/Api/Public/ViewPublication/813071",
    },
]

CDC_PAGES = [
    (
        "cdc_mv_interventions",
        "Motor Vehicle Injury Prevention Interventions",
        "https://www.cdc.gov/transportation-safety/calculator/index.html",
    ),
    (
        "cdc_interlocks",
        "MV PICCS Intervention: Alcohol Ignition Interlocks",
        "https://www.cdc.gov/transportation-safety/calculator/interlocks.html",
    ),
    (
        "cdc_red_light",
        "MV PICCS Intervention: Automated Red Light Cameras",
        "https://www.cdc.gov/transportation-safety/calculator/red-light.html",
    ),
    (
        "cdc_speed",
        "MV PICCS Intervention: Automated Speed Camera Enforcement",
        "https://www.cdc.gov/transportation-safety/calculator/speed.html",
    ),
    (
        "cdc_bike_helmet",
        "MV PICCS Intervention: Bicycle Helmet Laws for Children",
        "https://www.cdc.gov/transportation-safety/calculator/bike-helmet.html",
    ),
    (
        "cdc_increased_fines",
        "MV PICCS Intervention: Increased Seat Belt Fines",
        "https://www.cdc.gov/transportation-safety/calculator/increased-fines.html",
    ),
    (
        "cdc_license_renewal",
        "MV PICCS Intervention: In-Person License Renewal",
        "https://www.cdc.gov/transportation-safety/calculator/license-renewal.html",
    ),
    (
        "cdc_license_plate",
        "MV PICCS Intervention: License Plate Impoundment",
        "https://www.cdc.gov/transportation-safety/calculator/license-plate.html",
    ),
    (
        "cdc_plea_limits",
        "MV PICCS Intervention: Limits on Diversion",
        "https://www.cdc.gov/transportation-safety/calculator/plea-limits.html",
    ),
    (
        "cdc_seat_belt",
        "MV PICCS Intervention: Primary Enforcement of Seat Belt Laws",
        "https://www.cdc.gov/transportation-safety/calculator/seat-belt.html",
    ),
    (
        "cdc_patrols",
        "MV PICCS Intervention: Saturation Patrols",
        "https://www.cdc.gov/transportation-safety/calculator/patrols.html",
    ),
    (
        "cdc_highvis",
        "MV PICCS Intervention: Seat belt enforcement campaign",
        "https://www.cdc.gov/transportation-safety/calculator/highvis.html",
    ),
    (
        "cdc_checkpoints",
        "MV PICCS Intervention: Sobriety Checkpoints",
        "https://www.cdc.gov/transportation-safety/calculator/checkpoints.html",
    ),
    (
        "cdc_mchelmet",
        "MV PICCS Intervention: Universal Motorcycle Helmet Laws",
        "https://www.cdc.gov/transportation-safety/calculator/mchelmet.html",
    ),
    (
        "cdc_impoundment",
        "MV PICCS Intervention: Vehicle Impoundment",
        "https://www.cdc.gov/transportation-safety/calculator/impoundment.html",
    ),
]


# --------------------------------------------------------------------------- refresh


def _today() -> str:
    return dt.date.today().isoformat()


def _fetch_and_hash(url: str, dest: Path, expected_size: int | None = None, expected_md5: str | None = None) -> dict:
    download(url, dest)
    size = dest.stat().st_size
    if expected_size is not None and size != expected_size:
        raise RuntimeError(f"Size mismatch for {url}: listing says {expected_size}, got {size}")
    md5 = md5_file(dest)
    if expected_md5 and md5 != expected_md5:
        raise RuntimeError(f"MD5 mismatch for {url}: listing ETag {expected_md5}, got {md5}")
    if dest.suffix.lower() == ".zip":
        with zipfile.ZipFile(dest) as zf:
            bad = zf.testzip()
            if bad:
                raise RuntimeError(f"Corrupt member {bad} in {dest}")
    return {"size_bytes": size, "md5": md5, "sha256": sha256_file(dest)}


def refresh(n_years: int = N_FINAL_YEARS) -> dict:
    """Re-discover every source, download + verify it, and return the sources.yml document."""
    today = _today()
    years = discover_fars_years()
    chosen, newer = select_analysis_years(years, n_years)
    print(f"FARS years in listing: {[(y.year, y.status) for y in years]}", file=sys.stderr)
    print(f"Analysis years (final): {[y.year for y in chosen]}", file=sys.stderr)

    fars = []
    for fy in chosen:
        for kind, obj in (("national_csv", fy.national_csv), ("auxiliary_csv", fy.auxiliary_csv)):
            local = f"fars/{fy.year}/{Path(obj.key).name}"
            meta = _fetch_and_hash(obj.url, RAW / local, obj.size, obj.md5)
            fars.append(
                {
                    "id": f"fars_{fy.year}_{kind}",
                    "name": f"NHTSA FARS {fy.year} National {'Auxiliary ' if kind == 'auxiliary_csv' else ''}CSV",
                    "publisher": "National Highway Traffic Safety Administration",
                    "year": fy.year,
                    "file_status": fy.status,
                    "file_status_basis": fy.status_basis,
                    "url": obj.url,
                    "listing_url": f"{FARS_BUCKET}/?prefix={quote(f'{FARS_PREFIX}{fy.year}/National/')}",
                    "release_notes_url": fy.release_notes.url,
                    "last_modified": obj.last_modified,
                    "local_path": local,
                    "accessed": today,
                    **meta,
                }
            )

    census = []
    for entry in (CENSUS_INTERCENSAL, CENSUS_VINTAGE):
        meta = _fetch_and_hash(entry["url"], RAW / entry["local_path"])
        census.append({**entry, "accessed": today, **meta})

    vmt = []
    for fy in chosen:
        entry = vmt_entry(fy.year)
        meta = _fetch_and_hash(entry["url"], RAW / entry["local_path"])
        vmt.append({**entry, "accessed": today, **meta})

    documents = []
    for d in DOCUMENTS:
        meta = _fetch_and_hash(d["url"], RAW / "docs" / f"{d['id']}.pdf")
        documents.append({**d, "accessed": today, **meta})

    cdc = []
    for cid, name, url in CDC_PAGES:
        http_get(url)  # verify it opens
        cdc.append(
            {
                "id": cid,
                "name": name,
                "publisher": "Centers for Disease Control and Prevention, NCIPC",
                "url": url,
                "accessed": today,
                "verification": "HTTP 200; HTML page (no checksum recorded because page chrome changes)",
            }
        )

    return {
        "about": (
            "Lockfile of every public source used by Road Safety Action Explorer. Generated by "
            "`python -m pipeline.sources refresh`; verified by `make ingest`."
        ),
        "fars_discovery": {
            "human_listing_url": FARS_HUMAN_LISTING,
            "machine_listing_url": f"{FARS_BUCKET}/?prefix={FARS_PREFIX}&delimiter=/",
            "method": (
                "Year folders and file keys are read from the S3 bucket listing that backs NHTSA's File "
                "Downloads page; FINAL vs Annual Report File status is read from each year's release notes."
            ),
            "crashapi_note": (
                "The FARS CrashAPI (crashviewer.nhtsa.dot.gov/CrashAPI) and www.nhtsa.gov returned HTTP 403 "
                "(Akamai 'Access Denied') from cloud build environments; the API is not used anywhere."
            ),
            "years_in_listing": [{"year": y.year, "status": y.status, "basis": y.status_basis} for y in years],
            "analysis_years": [y.year for y in chosen],
            "excluded_newer_years": [
                {"year": y.year, "status": y.status, "reason": "not a FINAL file; excluded from analysis"}
                for y in newer
            ],
        },
        "fars": fars,
        "population": census,
        "vmt": vmt,
        "documents": documents,
        "cdc_pages": cdc,
    }


def load_sources() -> dict:
    return yaml.safe_load(SOURCES_YML.read_text())


def write_sources(doc: dict) -> None:
    SOURCES_YML.write_text(yaml.safe_dump(doc, sort_keys=False, width=110, allow_unicode=True))


def data_entries(doc: dict) -> list[dict]:
    return [*doc["fars"], *doc["population"], *doc["vmt"]]


def ensure_raw(doc: dict | None = None) -> None:
    """Download any missing data file listed in sources.yml and verify its SHA-256."""
    doc = doc or load_sources()
    for e in data_entries(doc):
        dest = RAW / e["local_path"]
        if not dest.exists():
            print(f"download {e['url']}", file=sys.stderr)
            download(e["url"], dest)
        got = sha256_file(dest)
        if got != e["sha256"]:
            raise SystemExit(
                f"Checksum mismatch for {e['id']} ({dest}).\n  expected {e['sha256']}\n  got      {got}\n"
                "The publisher may have revised the file. Review the change, then run "
                "`python -m pipeline.sources refresh` to update sources.yml."
            )
    print(f"verified {len(data_entries(doc))} data files against sources.yml", file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("refresh", help="re-discover + download + verify all sources, rewrite sources.yml")
    sub.add_parser("verify", help="download missing data files and verify checksums")
    args = ap.parse_args(argv)
    if args.cmd == "refresh":
        write_sources(refresh())
        print(f"wrote {SOURCES_YML}", file=sys.stderr)
    else:
        ensure_raw()


if __name__ == "__main__":
    main()
