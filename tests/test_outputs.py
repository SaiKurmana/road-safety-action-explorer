"""Smoke tests: the static site builds and the Streamlit app runs without exceptions."""

from pathlib import Path

from explorer.content import DISCLAIMER

ROOT = Path(__file__).resolve().parent.parent
EXACT = (
    "Independent portfolio project. Not affiliated with, endorsed by, or produced for CDC, NHTSA, FHWA, or USDOT. "
    "Uses only public data and published guidance."
)


def test_disclaimer_text_is_exact_everywhere():
    assert DISCLAIMER == EXACT
    assert EXACT in (ROOT / "README.md").read_text(encoding="utf-8")


def test_site_builds(tmp_path, monkeypatch):
    import sitegen.build as b

    monkeypatch.setattr(b, "OUT", tmp_path / "site")
    assert b.main() == 0
    pages = list((tmp_path / "site").rglob("*.html"))
    assert len(pages) == 4 + 1 + 51  # landing, actions, methods, sources + states index + 51 states
    for p in pages:
        assert EXACT in p.read_text(encoding="utf-8"), p.name  # footer on every page
    mt = (tmp_path / "site" / "states" / "MT.html").read_text(encoding="utf-8")
    assert "What the data suggest looking at" in mt and "rosap.ntl.bts.gov" in mt


def test_app_runs_for_several_states():
    from streamlit.testing.v1 import AppTest

    for abbr in ("MT", "DC", "VA", "CA"):  # rural, urban, sparse EMS data, large
        at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=60)
        at.query_params["state"] = abbr
        at.run()
        assert not at.exception, (abbr, at.exception)
        assert any(EXACT in i.value for i in at.info), abbr  # sidebar disclaimer
