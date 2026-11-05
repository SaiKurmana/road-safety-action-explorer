"""Smoke tests: the static site builds and the Streamlit app runs without exceptions."""

from pathlib import Path

from explorer.content import APP_URL, DISCLAIMER

ROOT = Path(__file__).resolve().parent.parent
EXACT = (
    "Independent portfolio project. Not affiliated with, endorsed by, or produced for CDC, NHTSA, FHWA, or USDOT. "
    "Uses only public data and published guidance."
)


def test_disclaimer_text_is_exact_everywhere():
    assert DISCLAIMER == EXACT
    assert EXACT in (ROOT / "README.md").read_text(encoding="utf-8")


DEPLOYED_APP_URL = "https://road-safety-explorer.streamlit.app/"
PLACEHOLDER = "APP_URL"  # the literal placeholder text used before the app was deployed


def test_app_url_is_the_deployed_app():
    assert APP_URL == DEPLOYED_APP_URL


def test_no_app_url_placeholder_in_readme_or_docs():
    files = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
    offenders = [f.relative_to(ROOT).as_posix() for f in files if PLACEHOLDER in f.read_text(encoding="utf-8")]
    assert not offenders, f"placeholder text {PLACEHOLDER!r} found in {offenders}"


def test_site_builds(tmp_path, monkeypatch):
    import sitegen.build as b

    monkeypatch.setattr(b, "OUT", tmp_path / "site")
    assert b.main() == 0
    pages = list((tmp_path / "site").rglob("*.html"))
    assert len(pages) == 4 + 1 + 51  # landing, actions, methods, sources + states index + 51 states
    for p in pages:
        html = p.read_text(encoding="utf-8")
        assert EXACT in html, p.name  # footer on every page
        assert PLACEHOLDER not in html, f"placeholder text {PLACEHOLDER!r} rendered in {p.name}"
        header, footer = html.split("<main>", 1)[0], html.split("<footer", 1)[1]
        assert f'href="{DEPLOYED_APP_URL}"' in header, p.name  # nav link to the app
        assert f'href="{DEPLOYED_APP_URL}"' in footer, p.name  # footer link to the app
    mt = (tmp_path / "site" / "states" / "MT.html").read_text(encoding="utf-8")
    assert "What the data suggest looking at" in mt and "rosap.ntl.bts.gov" in mt
    assert f'href="{DEPLOYED_APP_URL}?state=MT"' in mt  # state page deep-links to the app


def test_app_runs_for_several_states():
    from streamlit.testing.v1 import AppTest

    for abbr in ("MT", "DC", "VA", "CA"):  # rural, urban, sparse EMS data, large
        at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=60)
        at.query_params["state"] = abbr
        at.run()
        assert not at.exception, (abbr, at.exception)
        assert any(EXACT in i.value for i in at.info), abbr  # sidebar disclaimer
