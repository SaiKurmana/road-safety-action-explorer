"""Convert actions/actions.yaml and actions/signal_rules.yaml into dbt seed CSVs.

The YAML files are the human-edited source of truth; the CSVs in dbt/seeds/generated/
are regenerated on every build (git-ignored) so dbt can test them.

Default sort order of actions (shown in the app and site):
  1. prevention level: primary/upstream -> individual behavior -> post-crash
  2. Safe System element: Safe Roads, Safe Speeds, Safe Vehicles, Safe Road Users, Post-Crash Care
  3. published star rating, highest first (entries without stars after rated ones)
  4. title A-Z, then id
"""

from __future__ import annotations

import csv
from pathlib import Path

import yaml

from pipeline.config import ACTIONS_YAML, GENERATED_SEEDS, SIGNAL_RULES_YAML, SOURCES_YML

PREVENTION_ORDER = {"primary_upstream": 1, "individual_behavior": 2, "post_crash": 3}
ELEMENT_ORDER = {"Safe Roads": 1, "Safe Speeds": 2, "Safe Vehicles": 3, "Safe Road Users": 4, "Post-Crash Care": 5}
SORT_RULE = (
    "Upstream first: actions are ordered by prevention level (primary/upstream system design, then "
    "individual behavior, then post-crash), then Safe System element (roads, speeds, vehicles, road users, "
    "post-crash care), then published star rating (highest first; unrated after rated), then title."
)


def sort_key(a: dict) -> tuple:
    stars = a["evidence"].get("stars")
    return (
        PREVENTION_ORDER[a["prevention_level"]],
        ELEMENT_ORDER[a["safe_system_element"]],
        -(stars or 0),
        a["title"].lower(),
        a["id"],
    )


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def load_actions() -> list[dict]:
    return yaml.safe_load(ACTIONS_YAML.read_text(encoding="utf-8"))["actions"]


def load_rules() -> dict:
    return yaml.safe_load(SIGNAL_RULES_YAML.read_text(encoding="utf-8"))


def ordered_actions() -> list[dict]:
    return sorted(load_actions(), key=sort_key)


def main() -> None:
    actions = ordered_actions()
    write_csv(
        GENERATED_SEEDS / "actions.csv",
        [
            "action_id",
            "default_order",
            "title",
            "source_id",
            "source",
            "source_url",
            "source_landing_url",
            "section",
            "page",
            "pdf_page",
            "safe_system_element",
            "prevention_level",
            "rating",
            "stars",
            "rating_status",
            "rating_definition",
            "rating_source",
            "evidence_detail",
        ],
        [
            [
                a["id"],
                i,
                a["title"],
                a["source_id"],
                a["source"],
                a["source_url"],
                a["source_landing_url"],
                a["section"],
                a["page"],
                a["pdf_page"],
                a["safe_system_element"],
                a["prevention_level"],
                a["evidence"]["rating"],
                a["evidence"].get("stars") or "",
                a["evidence"]["rating_status"],
                a["evidence"]["rating_definition"],
                a["evidence"]["rating_source"],
                a["evidence"].get("published_benefits") or a["evidence"].get("objective_text") or "",
            ]
            for i, a in enumerate(actions, start=1)
        ],
    )
    write_csv(
        GENERATED_SEEDS / "action_tags.csv",
        ["action_id", "tag"],
        sorted([a["id"], t] for a in actions for t in a["topic_tags"]),
    )
    write_csv(
        GENERATED_SEEDS / "action_sectors.csv",
        ["action_id", "lead_sector"],
        sorted([a["id"], s] for a in actions for s in a["lead_sectors"]),
    )

    rules = load_rules()
    write_csv(
        GENERATED_SEEDS / "signal_rules.csv",
        ["rule_id", "rule_order", "label", "measure_id", "metric", "comparator", "operator", "min_n"],
        [
            [r["id"], i, r["label"], r["measure_id"], r["metric"], r["comparator"], r["operator"], r.get("min_n") or 0]
            for i, r in enumerate(rules["rules"], start=1)
        ],
    )
    write_csv(
        GENERATED_SEEDS / "signal_rule_tags.csv",
        ["rule_id", "tag"],
        sorted([r["id"], t] for r in rules["rules"] for t in r["show_tags"]),
    )
    docs = yaml.safe_load(SOURCES_YML.read_text(encoding="utf-8"))["documents"]
    write_csv(
        GENERATED_SEEDS / "source_documents.csv",
        ["source_id", "url", "landing_url", "sha256"],
        sorted([d["id"], d["url"], d["landing_url"], d["sha256"]] for d in docs),
    )
    print(f"wrote seeds for {len(actions)} actions and {len(rules['rules'])} rules to {GENERATED_SEEDS}")


if __name__ == "__main__":
    main()
