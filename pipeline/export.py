"""Export dbt models to committed CSVs with fixed column order and sort keys.

python -m pipeline.export --aggregates   # after a raw-mode build: data/aggregates/*.csv
python -m pipeline.export --marts        # data/marts/*.csv (read by the app and site)
python -m pipeline.export --marts --check  # rebuild check: fail if committed marts differ
"""

from __future__ import annotations

import argparse
import filecmp
import os
import sys
import tempfile
from pathlib import Path

import duckdb

from pipeline.config import AGGREGATES, DATA, MARTS

AGGREGATE_TABLES = {
    "agg_fars_state_year_counts": ("fars_state_year_counts", "state_fips, year, measure_id"),
    "agg_fars_ems_summary": ("fars_ems_summary", "state_fips, period_start, period_end"),
    "agg_population_state_year": ("population_state_year", "state_fips, year"),
    "agg_vmt_state_year": ("vmt_state_year", "state_fips, year"),
}

MART_TABLES = {
    "fct_state_year_measures": "state_fips, year, measure_id",
    "fct_window_measures": "state_fips, measure_id",
    "fct_ems_times": "state_fips, period_start, period_end",
    "fct_signal_inputs": "state_fips, measure_id, metric",
    "fct_state_signals": "state_fips, rule_order",
    "fct_signal_actions": "state_fips, default_order",
    "dim_state_profile": "state_fips",
    "dim_peers": "state_fips, peer_rank",
    "dim_actions": "default_order",
    "measures": "display_order",
    "states": "state_fips",
}


def default_db() -> Path:
    return Path(os.environ.get("RSAE_DUCKDB_PATH_ABS", DATA / "warehouse" / "road_safety.duckdb"))


def _copy(con: duckdb.DuckDBPyConnection, table: str, order: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    # table/order come from the constant maps above, never from user input.
    con.execute(f"COPY (SELECT * FROM {table} ORDER BY {order}) TO '{dest}' (HEADER, DELIMITER ',')")  # noqa: S608


def export_aggregates(con: duckdb.DuckDBPyConnection) -> None:
    for model, (name, order) in AGGREGATE_TABLES.items():
        _copy(con, model, order, AGGREGATES / f"{name}.csv")
    print(f"exported {len(AGGREGATE_TABLES)} aggregate tables to {AGGREGATES}", file=sys.stderr)


def export_marts(con: duckdb.DuckDBPyConnection, out_dir: Path = MARTS) -> None:
    for model, order in MART_TABLES.items():
        _copy(con, model, order, out_dir / f"{model}.csv")
    print(f"exported {len(MART_TABLES)} mart tables to {out_dir}", file=sys.stderr)


def check_marts(con: duckdb.DuckDBPyConnection) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        export_marts(con, Path(tmp))
        diffs = [m for m in MART_TABLES if not filecmp.cmp(Path(tmp) / f"{m}.csv", MARTS / f"{m}.csv", shallow=False)]
    if diffs:
        print(f"Committed marts differ from a rebuild: {diffs}. Run `make transform` and commit.", file=sys.stderr)
        return 1
    print("committed marts match the rebuild", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--aggregates", action="store_true")
    ap.add_argument("--marts", action="store_true")
    ap.add_argument("--check", action="store_true", help="with --marts: compare instead of writing")
    ap.add_argument("--db", type=Path, default=None)
    args = ap.parse_args(argv)
    con = duckdb.connect(str(args.db or default_db()), read_only=True)
    if args.aggregates:
        export_aggregates(con)
    if args.marts:
        return check_marts(con) if args.check else (export_marts(con) or 0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
