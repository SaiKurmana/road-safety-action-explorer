"""`make site`: build the static GitHub Pages site into site/_build/ from committed data only."""

from __future__ import annotations

import math
import re
import shutil
import sys
from pathlib import Path

import markdown
import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from explorer import content as C
from explorer import data as D
from sitegen.charts import dot_chart, line_chart

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "site" / "_build"
EXAMPLE_STATE = 30  # Montana: example snapshot on the landing page

env = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape(["html"]))


def trusted_html(html: str) -> Markup:
    """Mark generated HTML as safe. Only used for SVG built by sitegen.charts (all text escaped there)
    and for Markdown rendered from this repository's own docs; never for external or user input."""
    return Markup(html)  # noqa: S704


def _nan(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def fmt1(x) -> str:
    return "n/a" if _nan(x) else f"{x:.1f}"


def fmt2(x) -> str:
    return "n/a" if _nan(x) else f"{x:.2f}"


def pct(x) -> str:
    return "n/a" if _nan(x) else f"{x:+.1f}%"


def records(df: pd.DataFrame) -> list[dict]:
    return [{k: (None if _nan(v) else v) for k, v in r.items()} for r in df.to_dict("records")]


COMMON = {
    "C": C,
    "PREV": C.PREVENTION_LABELS,
    "SRC": C.SOURCE_SHORT,
    "fmt1": fmt1,
    "fmt2": fmt2,
    "pct": pct,
    "sentence": C.rule_sentence,
}


def render(template: str, dest: Path, root: str, **ctx) -> None:
    html = env.get_template(template).render(**COMMON, root=root, years=D.years(), **ctx)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")


def trend_svg(s: D.Snapshot) -> Markup:
    t = s.trend[s.trend.measure_id == "fatalities_total"]
    yrs = sorted(t.year.unique().tolist())
    st = t[t.state_fips == s.fips].set_index("year").rate_per_100k
    us = t[t.state_fips == 0].set_index("year").rate_per_100k
    return trusted_html(
        line_chart(
            yrs,
            [(s.abbr, "--series-1", [st[y] for y in yrs]), ("U.S.", "--series-2", [us[y] for y in yrs])],
            "Deaths per 100,000 population",
        )
    )


def state_page(s: D.Snapshot) -> dict:
    t = s.trend[s.trend.measure_id == "fatalities_total"]
    st = t[t.state_fips == s.fips].set_index("year")
    us = t[t.state_fips == 0].set_index("year")
    trend_rows = [
        {
            "year": y,
            "count": st.loc[y, "count"],
            "rate": st.loc[y, "rate_per_100k"],
            "us_rate": us.loc[y, "rate_per_100k"],
            "vmt_rate": st.loc[y, "rate_per_100m_vmt"],
            "us_vmt_rate": us.loc[y, "rate_per_100m_vmt"],
        }
        for y in sorted(st.index)
    ]
    core_groups = ["Overall", "Road users", "Behaviors", "Drivers", "Roadway"]
    hide = ["fatalities_pv_occupant_restraint_unknown", "fatalities_land_use_unknown"]
    core = s.window[s.window.measure_group.isin(core_groups) & ~s.window.measure_id.isin(hide)]
    dot_rows = [{**r, "label": C.SHORT_LABELS.get(r["measure_id"], r["label"])} for r in records(core)]
    dot = dot_chart(
        dot_rows,
        [
            ("rate_per_100k", s.name, "--series-1", "circle"),
            ("national_rate_per_100k", "U.S.", "--series-2", "diamond"),
            ("state_median_rate_per_100k", "Median of states", "--median", "tick"),
            ("peer_median_rate_per_100k", "Peer median", "--series-3", "square"),
        ],
        "Deaths per 100,000 population",
    )
    ems = s.ems[s.ems.is_signal_window].set_index("state_fips")
    linked = records(s.linked_actions)
    groups = [(e, [a for a in linked if a["safe_system_element"] == e]) for e in C.ELEMENTS]
    w0 = s.window.iloc[0]
    return {
        "s": s,
        "peers": ", ".join(s.peers.state_name),
        "latest": {"year": s.latest_year, "count": st.loc[s.latest_year, "count"]},
        "prev": {"count": st.loc[s.latest_year - 1, "count"]},
        "tot": s.window.set_index("measure_id").loc["fatalities_total"],
        "n_trig": int(s.signals.triggered.sum()),
        "signals": records(s.signals),
        "linked": linked,
        "groups": [(e, items) for e, items in groups if items],
        "trend_svg": trend_svg(s),
        "trend_rows": trend_rows,
        "dot_svg": trusted_html(dot),
        "measures": records(core),
        "prior_label": f"{int(w0.prior_window_start)}-{int(w0.prior_window_end)}",
        "fc": records(s.window[s.window.measure_group == "Function class"].dropna(subset=["rate_per_100m_vmt"])),
        "ems": [(s.name, ems.loc[s.fips]), ("United States", ems.loc[0])],
        "notes": D.data_quality_notes(s),
    }


def md_page(md_files: list[Path], title: str) -> Markup:
    text = "\n\n".join(p.read_text(encoding="utf-8") for p in md_files)
    # Relative repo links -> GitHub so they work on Pages.
    text = re.sub(r"\]\((\.\./)?((?:sources\.yml|actions/[^)]+|docs/[^)]+))\)", rf"]({C.REPO_URL}/blob/main/\2)", text)
    text = re.sub(
        r"\]\((data_dictionary|action_library_curation|usability_test_plan)\.md\)",
        rf"]({C.REPO_URL}/blob/main/docs/\1.md)",
        text,
    )
    text = text.replace("](limitations.md)", "](#limitations)").replace("](methods.md)", "](methods.html)")
    html = markdown.markdown(text, extensions=["tables", "toc", "fenced_code"])
    return trusted_html(html)


def sources_md() -> str:
    doc = D.sources_doc()
    lines = [
        "# Sources",
        "",
        "Every source below was fetched and verified; URLs, checksums, and access dates are recorded in "
        f"[`sources.yml`]({C.REPO_URL}/blob/main/sources.yml).",
        "",
        "## Data",
        "",
        "| Source | Publisher | Years | File / table | Accessed |",
        "|---|---|---|---|---|",
    ]
    for e in doc["fars"]:
        lines.append(
            f"| [{e['name']}]({e['url']}) ({e['file_status']}) | {e['publisher']} | {e['year']} | "
            f"`{e['url'].rsplit('/', 1)[-1]}` (sha256 `{e['sha256'][:12]}…`) | {e['accessed']} |"
        )
    for e in [*doc["population"], *doc["vmt"]]:
        lines.append(
            f"| [{e['name']}]({e['url']}) | {e['publisher']} | {e['years_used']} | {e['table_id']} "
            f"(sha256 `{e['sha256'][:12]}…`) | {e['accessed']} |"
        )
    excl = doc["fars_discovery"]["excluded_newer_years"]
    lines += [
        "",
        "FARS files are discovered from NHTSA's official download listing "
        f"([machine-readable listing]({doc['fars_discovery']['machine_listing_url']})). "
        + "; ".join(f"FARS {x['year']} is an {x['status'].replace('_', ' ')} and is excluded" for x in excl)
        + ".",
        "",
        "## Guidance documents",
        "",
        "| Document | Publisher | Accessed | Note |",
        "|---|---|---|---|",
    ]
    for d in doc["documents"]:
        note = d.get("edition_note") or d.get("role") or ""
        lines.append(f"| [{d['name']}]({d['landing_url']}) | {d['publisher']} | {d['accessed']} | {note} |")
    lines += ["", "## CDC pages (linked as related resources)", "", "| Page | Accessed |", "|---|---|"]
    lines += [f"| [{c['name']}]({c['url']}) | {c['accessed']} |" for c in doc["cdc_pages"]]
    return "\n".join(lines)


def landing_ctx() -> dict:
    sym = D.table("fct_state_year_measures")
    tot = sym[(sym.measure_id == "fatalities_total")]
    yrs = D.years()
    wm = D.table("fct_window_measures")
    wt = wm[wm.measure_id == "fatalities_total"]
    us_w = wt[wt.state_fips == 0].iloc[0]
    st_w = wt[wt.state_fips != 0]
    ex = D.snapshot(EXAMPLE_STATE)
    sig = D.table("fct_state_signals")
    tags = D.signal_rules_doc()["rules"]
    lib = D.actions()
    rules = []
    for r in tags:
        n_actions = int(
            lib.topic_tags.fillna("").map(lambda v, r=r: any(t in v.split("; ") for t in r["show_tags"])).sum()
        )
        rules.append(
            {
                "label": r["label"],
                "metric_label": C.METRIC_LABELS[r["metric"]],
                "comparator_label": C.COMPARATOR_LABELS[r["comparator"]],
                "min_n": r.get("min_n", 0),
                "tags": ", ".join(r["show_tags"]),
                "n_actions": n_actions,
                "n_states": int(sig[(sig.rule_id == r["id"]) & sig.triggered].shape[0]),
            }
        )
    nrss = next(d for d in D.sources_doc()["documents"] if d["id"] == "usdot_nrss_2022")
    return {
        "us": {
            "latest_year": yrs[-1],
            "latest_count": tot[(tot.state_fips == 0) & (tot.year == yrs[-1])]["count"].iloc[0],
            "total_10y": tot[tot.state_fips == 0]["count"].sum(),
            "window": f"{int(us_w.window_start)}-{int(us_w.window_end)}",
            "prior_window": f"{int(us_w.prior_window_start)}-{int(us_w.prior_window_end)}",
            "rate": us_w.rate_per_100k,
            "pct_change": us_w.pct_change_rate_per_100k,
            "min_rate": st_w.rate_per_100k.min(),
            "max_rate": st_w.rate_per_100k.max(),
        },
        "ex": ex,
        "ex_trend": trend_svg(ex),
        "ex_trig": records(ex.signals[ex.signals.triggered]),
        "ex_nrules": len(ex.signals),
        "rules": rules,
        "nrss_url": nrss["url"] + "#page=10",
    }


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "static").mkdir(parents=True)
    for f in (HERE / "static").iterdir():
        shutil.copy2(f, OUT / "static" / f.name)
    (OUT / ".nojekyll").write_text("")

    render("index.html", OUT / "index.html", "", nav="home", title=C.PROJECT, description=C.TAGLINE, **landing_ctx())

    sig = D.table("fct_state_signals")
    n_trig = sig[sig.triggered].groupby("state_fips").size()
    st = D.states().assign(n_trig=lambda d: d.state_fips.map(n_trig).fillna(0).astype(int))
    render(
        "states_index.html",
        OUT / "states" / "index.html",
        "../",
        nav="states",
        title=f"State snapshots | {C.PROJECT}",
        description="Static traffic fatality snapshots for the 50 states and DC.",
        states=records(st),
    )
    for fips in st.state_fips:
        s = D.snapshot(int(fips))
        render(
            "state.html",
            OUT / "states" / f"{s.abbr}.html",
            "../",
            nav="states",
            title=f"{s.name} snapshot | {C.PROJECT}",
            description=f"Traffic fatality snapshot for {s.name} linked to published Safe System countermeasures.",
            **state_page(s),
        )

    lib = D.actions()
    tags = sorted({t for v in lib.topic_tags.dropna() for t in v.split("; ")})
    render(
        "actions.html",
        OUT / "actions.html",
        "",
        nav="actions",
        title=f"Action library | {C.PROJECT}",
        description="Published Safe System countermeasures with verbatim evidence ratings and page citations.",
        actions=records(lib),
        n=len(lib),
        elements=C.ELEMENTS,
        tags=tags,
    )

    render(
        "prose.html",
        OUT / "methods.html",
        "",
        nav="methods",
        title=f"Methods | {C.PROJECT}",
        description="How the data are fetched, verified, and transformed.",
        body=md_page([ROOT / "docs" / "methods.md", ROOT / "docs" / "limitations.md"], "Methods"),
    )
    sources_html = trusted_html(markdown.markdown(sources_md(), extensions=["tables"]))
    render(
        "prose.html",
        OUT / "sources.html",
        "",
        nav="sources",
        title=f"Sources | {C.PROJECT}",
        description="Verified public data sources and guidance documents.",
        body=sources_html,
    )
    n_pages = len(list(OUT.rglob("*.html")))
    print(f"built {n_pages} pages into {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
