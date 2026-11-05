"""Schema and integrity checks on actions/actions.yaml and actions/signal_rules.yaml."""

import csv
import re

import yaml

from pipeline.config import ACTIONS_YAML, DBT_DIR, SIGNAL_RULES_YAML, SOURCES_YML
from pipeline.yaml_to_seeds import ordered_actions

DOC = yaml.safe_load(ACTIONS_YAML.read_text(encoding="utf-8"))
ACTIONS = DOC["actions"]
RULES = yaml.safe_load(SIGNAL_RULES_YAML.read_text(encoding="utf-8"))["rules"]
DOCS = {d["id"]: d for d in yaml.safe_load(SOURCES_YML.read_text(encoding="utf-8"))["documents"]}
REQUIRED = [
    "id",
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
    "lead_sectors",
    "topic_tags",
    "evidence",
]


def test_counts_and_unique_ids():
    ids = [a["id"] for a in ACTIONS]
    assert len(ids) == len(set(ids)) == 107
    by_source = {s: sum(a["source_id"] == s for a in ACTIONS) for s in DOCS}
    assert by_source["ctw_11th_2023"] == 77 and by_source["fhwa_psc_booklet"] == 28


def test_required_fields_and_vocabularies():
    vocab = DOC["vocabularies"]
    for a in ACTIONS:
        missing = [k for k in REQUIRED if a.get(k) in (None, "", [])]
        assert not missing, (a["id"], missing)
        assert a["safe_system_element"] in vocab["safe_system_element"]
        assert a["prevention_level"] in vocab["prevention_level"]
        assert set(a["lead_sectors"]) <= set(vocab["lead_sectors"])


def test_citations_point_into_verified_documents():
    for a in ACTIONS:
        doc = DOCS[a["source_id"]]
        assert a["source_url"] == f"{doc['url']}#page={a['pdf_page']}", a["id"]
        assert a["source_landing_url"] == doc["landing_url"]


def test_ratings_are_verbatim_or_explicitly_unrated():
    for a in ACTIONS:
        ev = a["evidence"]
        assert ev["rating_status"] in {"published", "not_rated_by_source", "not_verified"}
        if a["source_id"] == "ctw_11th_2023":
            assert 1 <= ev["stars"] <= 5 and ev["rating"] == "★" * ev["stars"]
            assert re.search(r"summary table, p\. \d+-\d+ \(PDF p\. \d+\)", ev["rating_source"])
        else:
            assert ev["stars"] is None


def test_no_advice_language_in_titles():
    for a in ACTIONS:
        assert not re.search(r"\b(should|must|recommend)", a["title"], re.I), a["title"]


def test_rules_reference_measures_and_reach_actions():
    with (DBT_DIR / "seeds" / "measures.csv").open() as fh:
        measures = {r["measure_id"]: r for r in csv.DictReader(fh)}
    tags = {t for a in ACTIONS for t in a["topic_tags"]}
    ids = [r["id"] for r in RULES]
    assert len(ids) == len(set(ids))
    for r in RULES:
        assert r["measure_id"] in measures, r["id"]
        assert set(r["show_tags"]) <= tags, r["id"]
        assert r["comparator"] in {"state_median", "national_rate"} and r["operator"] in {"above", "below"}
        assert r["min_n"] >= 20


def test_default_order_is_upstream_first():
    levels = [a["prevention_level"] for a in ordered_actions()]
    order = {"primary_upstream": 0, "individual_behavior": 1, "post_crash": 2}
    assert levels == sorted(levels, key=order.get)
    behavior = [a["evidence"]["stars"] for a in ordered_actions() if a["safe_system_element"] == "Safe Road Users"]
    assert behavior == sorted(behavior, reverse=True)
