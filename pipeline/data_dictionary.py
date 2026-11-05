"""Generate docs/data_dictionary.md from the dbt manifest (model/column descriptions) and the
measures seed (measure definitions). Run after any dbt command that writes target/manifest.json.
"""

from __future__ import annotations

import csv
import json
import sys

from pipeline.config import DBT_DIR, ROOT

OUT = ROOT / "docs" / "data_dictionary.md"
LAYERS = [
    ("Committed aggregates (data/aggregates/)", "models/aggregates/"),
    ("Marts (data/marts/, read by the app and site)", "models/marts/"),
]


def _cell(text: str) -> str:
    return " ".join((text or "").split()).replace("|", "\\|")


def main() -> int:
    manifest = json.loads((DBT_DIR / "target" / "manifest.json").read_text())
    nodes = [
        n for n in manifest["nodes"].values() if n["resource_type"] == "model" and n["package_name"] == "road_safety"
    ]
    lines = [
        "# Data dictionary",
        "",
        "_Generated from the dbt project by `python -m pipeline.data_dictionary`; do not edit by hand._",
        "",
        "All counts are deaths in fatal crashes on public roads in the 50 states and DC, from NHTSA FARS final "
        "files. `state_fips = 0` denotes the United States. See [methods.md](methods.md) for derivations.",
        "",
        "## Measures",
        "",
        "| measure_id | Label | VMT denominator | Definition |",
        "|---|---|---|---|",
    ]
    with (DBT_DIR / "seeds" / "measures.csv").open(encoding="utf-8") as fh:
        for m in sorted(csv.DictReader(fh), key=lambda r: int(r["display_order"])):
            lines.append(
                f"| `{m['measure_id']}` | {_cell(m['label'])} | {m['vmt_denominator'] or 'n/a'} | {_cell(m['definition'])} |"
            )
    for title, prefix in LAYERS:
        lines += ["", f"## {title}", ""]
        for n in sorted((n for n in nodes if n["original_file_path"].startswith(prefix)), key=lambda n: n["name"]):
            lines += [f"### `{n['name']}`", "", _cell(n.get("description")), ""]
            cols = n.get("columns") or {}
            if cols:
                lines += ["| Column | Description |", "|---|---|"]
                lines += [f"| `{c}` | {_cell(v.get('description'))} |" for c, v in cols.items()]
                lines.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"wrote {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
