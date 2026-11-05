"""Sanity checks on the committed marts the app and site read."""

import pandas as pd

from explorer import data as D


def test_published_benchmarks_reproduced():
    sym = D.table("fct_state_year_measures")
    us23 = sym[(sym.state_fips == 0) & (sym.year == 2023)].set_index("measure_id")["count"]
    assert us23["fatalities_total"] == 41025
    assert round(us23["fatalities_alcohol_impaired_driving"]) == 12382


ANALYSIS_YEARS = D.sources_doc()["fars_discovery"]["analysis_years"]
WINDOW = f"{ANALYSIS_YEARS[-1] - 2}-{ANALYSIS_YEARS[-1]}"


def test_years_are_final_only_and_complete():
    assert D.years() == ANALYSIS_YEARS == list(range(ANALYSIS_YEARS[-1] - 9, ANALYSIS_YEARS[-1] + 1))
    assert all(e["file_status"] == "final" for e in D.sources_doc()["fars"])
    assert len(D.states()) == 51


def test_every_state_snapshot_builds():
    for fips in D.states().state_fips:
        s = D.snapshot(int(fips))
        assert len(s.signals) == 12
        assert s.window_label == WINDOW
        assert len(s.peers) == 5 and s.fips not in s.peers.peer_fips.tolist()
        assert set(s.linked_actions.action_id) <= set(D.actions().action_id)
        assert D.data_quality_notes(s)


def test_signals_consistent_with_values():
    sig = D.table("fct_state_signals")
    ev = sig[sig.evaluable]
    assert (ev.triggered == (ev.value > ev.comparator_value)).all()
    ne = sig[~sig.evaluable]
    assert not ne.triggered.any()
    assert ((ne.n < ne.min_n) | ne.value.isna()).all()


def test_committed_data_under_size_budget():
    total = sum(p.stat().st_size for p in D.ROOT.joinpath("data").glob("*/*.csv"))
    assert total < 10 * 1024 * 1024
    assert pd.read_csv(D.MARTS / "dim_actions.csv").default_order.is_unique
