"""Load the committed marts (data/marts/*.csv). Everything the app and site show comes from here."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
MARTS = ROOT / "data" / "marts"


@cache
def table(name: str) -> pd.DataFrame:
    return pd.read_csv(MARTS / f"{name}.csv")


def states() -> pd.DataFrame:
    """The 50 states + DC (excludes the U.S. row)."""
    s = table("states")
    return s[s.state_fips != 0].reset_index(drop=True)


def measures() -> pd.DataFrame:
    return table("measures")


def years() -> list[int]:
    return sorted(table("fct_state_year_measures").year.unique().tolist())


@cache
def sources_doc() -> dict:
    return yaml.safe_load((ROOT / "sources.yml").read_text(encoding="utf-8"))


@cache
def signal_rules_doc() -> dict:
    return yaml.safe_load((ROOT / "actions" / "signal_rules.yaml").read_text(encoding="utf-8"))


def actions() -> pd.DataFrame:
    return table("dim_actions").sort_values("default_order").reset_index(drop=True)


@dataclass
class Snapshot:
    fips: int
    abbr: str
    name: str
    profile: pd.Series
    us_profile: pd.Series
    window: pd.DataFrame  # fct_window_measures for state, joined with measure metadata, + U.S.
    trend: pd.DataFrame  # fct_state_year_measures for state and U.S.
    ems: pd.DataFrame  # fct_ems_times rows for state and U.S.
    signals: pd.DataFrame  # fct_state_signals for state
    linked_actions: pd.DataFrame  # dim_actions rows linked to triggered signals, upstream-first
    peers: pd.DataFrame  # peer states with names

    @property
    def window_label(self) -> str:
        w = self.window.iloc[0]
        return f"{int(w.window_start)}-{int(w.window_end)}"

    @property
    def latest_year(self) -> int:
        return int(self.trend.year.max())


def snapshot(fips: int) -> Snapshot:
    st = table("states").set_index("state_fips")
    prof = table("dim_state_profile").set_index("state_fips")
    m = measures()
    wm = table("fct_window_measures")
    window = wm[wm.state_fips == fips].merge(m, on="measure_id").sort_values("display_order")
    us_w = wm[wm.state_fips == 0][["measure_id", "count_window", "count_annual_avg"]].rename(
        columns={"count_window": "us_count_window", "count_annual_avg": "us_count_annual_avg"}
    )
    window = window.merge(us_w, on="measure_id", how="left")
    sym = table("fct_state_year_measures")
    trend = sym[sym.state_fips.isin([fips, 0])]
    ems = table("fct_ems_times")
    ems = ems[ems.state_fips.isin([fips, 0])]
    sig = table("fct_state_signals")
    sig = sig[sig.state_fips == fips].sort_values("rule_order").reset_index(drop=True)
    sa = table("fct_signal_actions")
    sa = sa[sa.state_fips == fips][["action_id", "triggered_by_rules"]]
    linked = actions().merge(sa, on="action_id").sort_values("default_order").reset_index(drop=True)
    peers = table("dim_peers")
    peers = peers[peers.state_fips == fips].merge(
        st.reset_index()[["state_fips", "state_abbr", "state_name"]].rename(columns={"state_fips": "peer_fips"}),
        on="peer_fips",
    )
    return Snapshot(
        fips=fips,
        abbr=st.loc[fips, "state_abbr"],
        name=st.loc[fips, "state_name"],
        profile=prof.loc[fips],
        us_profile=prof.loc[0],
        window=window.reset_index(drop=True),
        trend=trend.reset_index(drop=True),
        ems=ems.reset_index(drop=True),
        signals=sig,
        linked_actions=linked,
        peers=peers.sort_values("peer_rank").reset_index(drop=True),
    )


def data_quality_notes(s: Snapshot) -> list[str]:
    """Plain-language data-quality notes for a state snapshot (computed, never hand-written)."""
    notes = []
    w = s.window.set_index("measure_id")
    pv = w.loc["fatalities_pv_occupant", "count_window"]
    unk = w.loc["fatalities_pv_occupant_restraint_unknown", "count_window"]
    if pv > 0:
        notes.append(
            f"Restraint use was unknown for {unk / pv:.0%} of passenger-vehicle occupants killed in "
            f"{s.window_label}; the unrestrained count is a lower bound."
        )
    tot = w.loc["fatalities_total", "count_window"]
    lu = w.loc["fatalities_land_use_unknown", "count_window"]
    fc = w.loc["fatalities_fc_unknown", "count_window"]
    if tot > 0 and (lu + fc) > 0:
        notes.append(
            f"Rural/urban land use was unknown for {lu / tot:.1%} and road function class for {fc / tot:.1%} "
            f"of fatalities in {s.window_label}."
        )
    low = w[w.low_count_flag & (w.unit == "deaths")].label.tolist()
    if low:
        notes.append("Fewer than 20 deaths in the window (rates are unstable): " + "; ".join(low) + ".")
    e = s.ems[(s.ems.state_fips == s.fips) & s.ems.is_signal_window]
    if len(e):
        e = e.iloc[0]
        notes.append(
            f"EMS times: crash-to-scene interval usable for {e.pct_crashes_scene_time_valid:.0f}% and "
            f"crash-to-hospital interval for {e.pct_crashes_hospital_time_valid:.0f}% of fatal crashes in "
            f"{e.period_label} ({int(e.n_hospital_not_applicable):,} crashes coded not transported / not "
            "applicable)."
        )
        if pd.isna(e.median_minutes_to_hospital):
            notes.append(
                "Too few valid hospital-arrival times were recorded to report a median; the post-crash "
                "signal is not evaluated for this state."
            )
    notes.append(
        "Alcohol-impaired-driving fatalities use NHTSA's multiply-imputed BAC files and can be fractional "
        "(mean of 10 imputations)."
    )
    return notes
