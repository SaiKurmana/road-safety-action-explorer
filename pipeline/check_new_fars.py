"""Weekly check: has NHTSA released a FARS FINAL year newer than the one in sources.yml?

Reads NHTSA's official FARS download listing (static.nhtsa.gov bucket) and each year's release
notes - never the CrashAPI, which returns HTTP 403 to cloud runners. Prints a summary and, when
running in GitHub Actions, writes `new_final_year=<year>` (or empty) to $GITHUB_OUTPUT.
"""

from __future__ import annotations

import os
import sys

from pipeline.sources import discover_fars_years, load_sources


def main() -> int:
    current = max(load_sources()["fars_discovery"]["analysis_years"])
    years = discover_fars_years()
    finals = [y.year for y in years if y.status == "final"]
    newest = max(finals) if finals else None
    new_year = newest if newest and newest > current else None
    print(f"current newest final year in sources.yml: {current}")
    print(f"listing: {[(y.year, y.status) for y in years if y.year >= current - 1]}")
    print(f"new final year available: {new_year or 'no'}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"new_final_year={new_year or ''}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
