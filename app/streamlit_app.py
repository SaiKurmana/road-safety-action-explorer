"""Road Safety Action Explorer - Streamlit app.

Runs offline from the committed marts in data/marts/. Run with `make app`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from explorer import content as C  # noqa: E402
from explorer import data as D  # noqa: E402

# Validated categorical slots 1-3 (blue, orange, aqua) + neutral gray for the median of states.
COLORS = {"state": "#2a78d6", "us": "#eb6834", "peers": "#1baf7a", "median": "#8a8984"}

st.set_page_config(page_title=C.PROJECT, page_icon="🛣️", layout="wide")


# --------------------------------------------------------------------------- sidebar

state_df = D.states()
abbr_to_fips = dict(zip(state_df.state_abbr, state_df.state_fips, strict=True))
names = dict(zip(state_df.state_fips, state_df.state_name, strict=True))
qp = st.query_params.get("state", "MT")
default_fips = abbr_to_fips.get(str(qp).upper(), 30)

with st.sidebar:
    st.title(C.PROJECT)
    fips = st.selectbox(
        "State",
        options=list(names),
        index=list(names).index(default_fips),
        format_func=lambda f: names[f],
    )
    st.query_params["state"] = state_df.set_index("state_fips").loc[fips, "state_abbr"]
    yrs = D.years()
    st.caption(
        f"NHTSA FARS final files {yrs[0]}-{yrs[-1]}; Census population estimates; FHWA Highway Statistics VM-2. "
        f"The {yrs[-1] + 1} FARS Annual Report File is provisional and excluded."
    )
    st.info(C.DISCLAIMER, icon="ℹ️")
    st.caption(f"Author: {C.AUTHOR}")

snap = D.snapshot(fips)
tab_snap, tab_lib, tab_methods = st.tabs(["State snapshot", "Action library", "Methods & sources"])


# --------------------------------------------------------------------------- helpers


def wrow(measure_id: str) -> pd.Series:
    return snap.window.set_index("measure_id").loc[measure_id]


def trend_chart(measure_id: str, metric: str) -> go.Figure:
    t = snap.trend[snap.trend.measure_id == measure_id].sort_values("year")
    fig = go.Figure()
    for fips_, name, key in ((snap.fips, snap.name, "state"), (0, "United States", "us")):
        d = t[t.state_fips == fips_]
        fig.add_trace(
            go.Scatter(
                x=d.year,
                y=d[metric],
                name=name,
                mode="lines+markers",
                line={"color": COLORS[key], "width": 2},
                marker={"size": 8},
                hovertemplate=f"{name}<br>%{{x}}: %{{y:.2f}}<extra></extra>",
            )
        )
        last = d.iloc[-1]
        fig.add_annotation(
            x=last.year,
            y=last[metric],
            text=name if key == "us" else snap.abbr,
            showarrow=False,
            xanchor="left",
            xshift=8,
            font={"size": 12},
        )
    fig.update_layout(
        height=340,
        margin={"l": 10, "r": 60, "t": 10, "b": 10},
        hovermode="x unified",
        legend={"orientation": "h", "y": -0.18},
        yaxis_title=C.METRIC_LABELS[metric],
        xaxis={"tickvals": sorted(t.year.unique()), "range": [t.year.min() - 0.4, t.year.max() + 1.2]},
        yaxis={"rangemode": "tozero", "gridcolor": "rgba(128,128,128,0.15)"},
    )
    return fig


def comparison_chart(rows: pd.DataFrame, metric: str) -> go.Figure:
    """Dot plot: state vs U.S., median of states, and peer median for each measure (one axis)."""
    fig = go.Figure()
    series = [
        (metric, snap.name, "state", 13, "circle"),
        (f"national_{metric}", "United States", "us", 10, "diamond"),
        (f"state_median_{metric}", "Median of states", "median", 10, "line-ns-open"),
        (f"peer_median_{metric}", "Peer median", "peers", 10, "square"),
    ]
    for col, name, key, size, symbol in series:
        fig.add_trace(
            go.Scatter(
                x=rows[col],
                y=rows.measure_id.map(C.SHORT_LABELS).fillna(rows.label),
                name=name,
                mode="markers",
                marker={
                    "color": COLORS[key],
                    "size": size,
                    "symbol": symbol,
                    "line": {"width": 2, "color": COLORS[key]},
                },
                hovertemplate=f"{name}: %{{x:.2f}}<extra>%{{y}}</extra>",
            )
        )
    fig.update_layout(
        height=60 + 42 * len(rows),
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        legend={"orientation": "h", "y": 1.08},
        xaxis_title=C.METRIC_LABELS[metric],
        yaxis={"autorange": "reversed"},
        xaxis={"rangemode": "tozero", "gridcolor": "rgba(128,128,128,0.15)"},
    )
    return fig


def action_card(a: pd.Series) -> None:
    rating = a.rating if a.rating_status != "not_rated_by_source" else "Not rated by source"
    st.markdown(f"**{a.title}** — {rating}")
    st.caption(
        f"{C.PREVENTION_LABELS[a.prevention_level]} · Lead sectors (generic roles): {a.lead_sectors} · "
        f"[{C.SOURCE_SHORT[a.source_id]}, {a.page}]({a.source_url})"
    )
    if a.rating_status == "published" and pd.notna(a.stars):
        st.caption(f"Rating definition (source): {a.rating_definition}")
    if isinstance(a.evidence_detail, str) and a.evidence_detail:
        st.caption(f"Published safety benefits / objective (verbatim): {a.evidence_detail}")


# --------------------------------------------------------------------------- snapshot tab

with tab_snap:
    st.header(f"{snap.name}: traffic fatality snapshot")
    tot = wrow("fatalities_total")
    t_tot = snap.trend[(snap.trend.measure_id == "fatalities_total") & (snap.trend.state_fips == fips)]
    latest = t_tot[t_tot.year == snap.latest_year].iloc[0]
    prev = t_tot[t_tot.year == snap.latest_year - 1].iloc[0]
    n_trig = int(snap.signals.triggered.sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        f"Fatalities, {snap.latest_year}",
        f"{latest['count']:,.0f}",
        f"{latest['count'] - prev['count']:+,.0f} vs {snap.latest_year - 1}",
        delta_color="inverse",
    )
    c2.metric(f"Per 100k population, {snap.window_label}", f"{tot.rate_per_100k:.1f}")
    c2.caption(f"U.S. {tot.national_rate_per_100k:.1f} · median of states {tot.state_median_rate_per_100k:.1f}")
    c3.metric(f"Per 100M VMT, {snap.window_label}", f"{tot.rate_per_100m_vmt:.2f}")
    c3.caption(f"U.S. {tot.national_rate_per_100m_vmt:.2f} · median of states {tot.state_median_rate_per_100m_vmt:.2f}")
    c4.metric("Signals triggered", f"{n_trig} of {len(snap.signals)}")
    c4.caption(f"{len(snap.linked_actions)} linked resources")

    st.subheader("Trend")
    m = D.measures()
    death_measures = m[m.unit == "deaths"]
    left, right = st.columns([2, 1])
    with right:
        msel = st.selectbox(
            "Measure", death_measures.measure_id, format_func=lambda x: m.set_index("measure_id").loc[x, "label"]
        )
        metric_sel = st.radio("Rate", ["rate_per_100k", "rate_per_100m_vmt"], format_func=C.METRIC_LABELS.get)
        st.caption("Rates for each year; the U.S. line is all 50 states + DC.")
    with left:
        if (
            metric_sel == "rate_per_100m_vmt"
            and snap.trend[snap.trend.measure_id == msel].rate_per_100m_vmt.isna().all()
        ):
            st.info("No VMT denominator applies to this measure.")
        else:
            st.plotly_chart(trend_chart(msel, metric_sel), width="stretch")

    st.subheader(f"Measures vs. national and peers ({snap.window_label}, pooled)")
    peers_txt = ", ".join(snap.peers.state_name)
    st.caption(
        f"Peers (most similar rural share of VMT and VMT per capita, {int(snap.profile.profile_year)}): {peers_txt}. "
        "Method: z-scored Euclidean distance on those two features; see Methods."
    )
    core = snap.window[
        snap.window.measure_group.isin(["Overall", "Road users", "Behaviors", "Drivers", "Roadway"])
        & ~snap.window.measure_id.isin(["fatalities_pv_occupant_restraint_unknown", "fatalities_land_use_unknown"])
    ]
    st.plotly_chart(comparison_chart(core, "rate_per_100k"), width="stretch")
    table = core[
        [
            "label",
            "count_annual_avg",
            "rate_per_100k",
            "national_rate_per_100k",
            "state_median_rate_per_100k",
            "peer_median_rate_per_100k",
            "rate_per_100m_vmt",
            "national_rate_per_100m_vmt",
            "pct_change_rate_per_100k",
            "rank_rate_per_100k",
            "low_count_flag",
        ]
    ]
    st.dataframe(
        table.rename(
            columns={
                "label": "Measure",
                "count_annual_avg": "Deaths/yr (avg)",
                "rate_per_100k": "Rate /100k",
                "national_rate_per_100k": "U.S. /100k",
                "state_median_rate_per_100k": "Median of states /100k",
                "peer_median_rate_per_100k": "Peer median /100k",
                "rate_per_100m_vmt": "Rate /100M VMT",
                "national_rate_per_100m_vmt": "U.S. /100M VMT",
                "pct_change_rate_per_100k": "% change vs prior 3 yrs",
                "rank_rate_per_100k": "Rank (1 = highest)",
                "low_count_flag": "<20 deaths",
            }
        ),
        column_config={
            c: st.column_config.NumberColumn(format="%.2f")
            for c in (
                "Rate /100k",
                "U.S. /100k",
                "Median of states /100k",
                "Peer median /100k",
                "Rate /100M VMT",
                "U.S. /100M VMT",
            )
        }
        | {
            "Deaths/yr (avg)": st.column_config.NumberColumn(format="%.1f"),
            "% change vs prior 3 yrs": st.column_config.NumberColumn(format="%+.1f%%"),
        },
        hide_index=True,
        width="stretch",
    )

    with st.expander("Roadway function class (rates per 100M VMT on that class)"):
        fc = snap.window[snap.window.measure_group == "Function class"].dropna(subset=["rate_per_100m_vmt"])
        st.plotly_chart(comparison_chart(fc, "rate_per_100m_vmt"), width="stretch")

    st.subheader("Post-crash care signal: EMS times")
    e = snap.ems[snap.ems.is_signal_window].set_index("state_fips")
    ecols = st.columns(2)
    for col, fips_, label in ((ecols[0], fips, snap.name), (ecols[1], 0, "United States")):
        r = e.loc[fips_]
        col.markdown(f"**{label}, {r.period_label}**")
        col.markdown(
            f"- Crash → EMS at scene: median **{C.fmt_num(r.median_minutes_to_scene)} min** "
            f"(90th pct {C.fmt_num(r.p90_minutes_to_scene)}); usable for {r.pct_crashes_scene_time_valid:.0f}% of crashes\n"
            f"- Crash → hospital arrival: median **{C.fmt_num(r.median_minutes_to_hospital)} min** "
            f"(90th pct {C.fmt_num(r.p90_minutes_to_hospital)}); usable for {r.pct_crashes_hospital_time_valid:.0f}% of crashes"
        )

    st.subheader("Data-quality notes")
    for note in D.data_quality_notes(snap):
        st.markdown(f"- {note}")

    st.subheader("What the data suggest looking at")
    st.caption(C.SIGNAL_EXPLAINER)
    for r in snap.signals.to_dict("records"):
        icon = "🔶" if r["triggered"] else ("⚪" if r["evaluable"] else "➖")
        status = "Signal" if r["triggered"] else ("No signal" if r["evaluable"] else "Not evaluated")
        st.markdown(f"{icon} **{status}** — {C.rule_sentence(r)}")
    with st.expander("Rule logic (exactly as configured)"):
        rules = pd.DataFrame(D.signal_rules_doc()["rules"])
        rules["show_tags"] = rules.show_tags.map(", ".join)
        st.dataframe(rules, hide_index=True, width="stretch")
        st.caption(D.signal_rules_doc()["min_n"])

    st.markdown(f"**Linked resources ({len(snap.linked_actions)})** — grouped by Safe System element. {C.SORT_RULE}")
    if snap.linked_actions.empty:
        st.info("No signals triggered for this state; browse the full Action library tab.")
    for element in C.ELEMENTS:
        grp = snap.linked_actions[snap.linked_actions.safe_system_element == element]
        if grp.empty:
            continue
        with st.expander(f"{element} ({len(grp)})", expanded=element in ("Safe Roads", "Safe Speeds")):
            for _, a in grp.iterrows():
                action_card(a)
                st.caption(f"Linked by: {a.triggered_by_rules}")


# --------------------------------------------------------------------------- library tab

with tab_lib:
    st.header("Action library")
    st.caption(
        "Every entry is taken from a published source that was opened and read; titles and ratings are verbatim. "
        "Safe System element, prevention level, lead sectors, and topic tags are curator classifications (see "
        "docs/action_library_curation.md). " + C.SORT_RULE
    )
    lib = D.actions()
    f1, f2, f3, f4 = st.columns(4)
    src = f1.multiselect("Source", sorted(lib.source_id.unique()), format_func=C.SOURCE_SHORT.get)
    elem = f2.multiselect("Safe System element", C.ELEMENTS)
    lvl = f3.multiselect("Prevention level", list(C.PREVENTION_LABELS), format_func=C.PREVENTION_LABELS.get)
    tags = sorted({t for v in lib.topic_tags.dropna() for t in v.split("; ")})
    tag = f4.multiselect("Topic", tags)
    g1, g2 = st.columns([1, 3])
    min_stars = g1.selectbox(
        "Minimum CTW stars", [0, 1, 2, 3, 4, 5], format_func=lambda s: "Any" if s == 0 else "★" * s
    )
    q = g2.text_input("Search titles")
    view = lib
    if src:
        view = view[view.source_id.isin(src)]
    if elem:
        view = view[view.safe_system_element.isin(elem)]
    if lvl:
        view = view[view.prevention_level.isin(lvl)]
    if tag:
        view = view[view.topic_tags.fillna("").map(lambda v: any(t in v.split("; ") for t in tag))]
    if min_stars:
        view = view[view.stars.fillna(0) >= min_stars]
    if q:
        view = view[view.title.str.contains(q, case=False, regex=False)]
    st.caption(f"{len(view)} of {len(lib)} entries")
    st.dataframe(
        view[
            [
                "title",
                "rating",
                "safe_system_element",
                "prevention_level",
                "topic_tags",
                "lead_sectors",
                "source_id",
                "page",
                "source_url",
            ]
        ].assign(
            prevention_level=lambda d: d.prevention_level.map(C.PREVENTION_LABELS),
            source_id=lambda d: d.source_id.map(C.SOURCE_SHORT),
        ),
        column_config={
            "title": "Title (verbatim)",
            "rating": "Published rating",
            "safe_system_element": "Safe System element",
            "prevention_level": "Prevention level",
            "topic_tags": "Topics",
            "lead_sectors": "Lead sectors (generic)",
            "source_id": "Source",
            "page": "Page / section",
            "source_url": st.column_config.LinkColumn("Citation", display_text="Open cited page"),
        },
        hide_index=True,
        width="stretch",
        height=520,
    )


# --------------------------------------------------------------------------- methods tab

with tab_methods:
    root = Path(__file__).resolve().parent.parent
    st.markdown((root / "docs" / "methods.md").read_text(encoding="utf-8"))
    st.subheader("Sources")
    doc = D.sources_doc()
    rows = [
        {
            "Source": e["name"],
            "Years": e.get("years_used", e.get("year", "")),
            "Accessed": e["accessed"],
            "URL": e["url"],
        }
        for e in [*doc["population"], *doc["vmt"], *doc["documents"]]
    ]
    rows.insert(
        0,
        {
            "Source": "NHTSA FARS National CSV + Auxiliary CSV (final files)",
            "Years": ", ".join(str(y) for y in doc["fars_discovery"]["analysis_years"]),
            "Accessed": doc["fars"][0]["accessed"],
            "URL": doc["fars_discovery"]["machine_listing_url"],
        },
    )
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        column_config={"URL": st.column_config.LinkColumn("URL")},
    )
    st.subheader("Limitations")
    for item in C.LIMITATIONS_SHORT:
        st.markdown(f"- {item}")
    st.caption(C.DISCLAIMER)
