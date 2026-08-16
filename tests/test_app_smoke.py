"""AppTest-based smoke tests — each registered page is tested deliberately
and separately (AppTest simulates one running page per test), rather than
attempting cross-page session-state flows in a single run, matching
AppTest's real limitations for multipage apps built with callable-based
st.Page objects. Pure models/repositories/helpers are tested elsewhere,
independent of any Streamlit runtime.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.ui.ui import PRIMARY_NAV, FOOTER_NAV

HARNESS_DIR = Path(__file__).parent / "apptest_pages"

PRIMARY_PAGES = [
    "home_page.py",
    "dashboard_page.py",
    "themes_page.py",
    "signals_page.py",
    "research_page.py",
    "methodology_page.py",
    "disclaimer_page.py",
    "about_page.py",
]


@pytest.mark.parametrize("harness_file", PRIMARY_PAGES)
def test_primary_page_renders_without_exception(harness_file):
    at = AppTest.from_file(str(HARNESS_DIR / harness_file), default_timeout=10)
    at.run()
    assert not at.exception, f"{harness_file} raised: {at.exception}"


@pytest.mark.parametrize("harness_file", PRIMARY_PAGES)
def test_primary_page_renders_footer(harness_file):
    # Demo status lives in the sidebar (see test_sidebar_status_renders), not
    # per-page — with_chrome only guarantees the footer.
    at = AppTest.from_file(str(HARNESS_DIR / harness_file), default_timeout=10)
    at.run()
    all_html = " ".join(m.value for m in at.markdown)
    assert "does not provide investment advice" in all_html
    assert "EevaResearch AI v" in all_html


def test_company_page_receives_demo_symbol_via_query_params():
    at = AppTest.from_file(str(HARNESS_DIR / "company_page.py"), default_timeout=10)
    at.query_params["symbol"] = "DEMO"
    at.run()
    assert not at.exception
    all_markdown = " ".join(m.value for m in at.markdown)
    assert "Nova Aperture Systems" in all_markdown


def test_company_page_unknown_symbol_shows_empty_state_not_exception():
    at = AppTest.from_file(str(HARNESS_DIR / "company_page.py"), default_timeout=10)
    at.query_params["symbol"] = "NOTREAL"
    at.run()
    assert not at.exception
    all_markdown = " ".join(m.value for m in at.markdown)
    assert "No ticker found" in all_markdown


def test_company_page_shows_demo_evidence_with_no_fabricated_source():
    at = AppTest.from_file(str(HARNESS_DIR / "company_page.py"), default_timeout=10)
    at.query_params["symbol"] = "DEMO"
    at.run()
    assert not at.exception
    all_markdown = " ".join(m.value for m in at.markdown)
    assert "EevaResearch Demo Data" in all_markdown
    assert "no external source" in all_markdown


def test_sidebar_status_renders():
    at = AppTest.from_file(str(HARNESS_DIR / "sidebar_rail.py"), default_timeout=10)
    at.run()
    assert not at.exception
    all_html = " ".join(m.value for m in at.markdown)
    assert "EevaResearch" in all_html
    assert "Demo mode" in all_html
    # Every primary + footer nav item renders as a real st.page_link.
    # (Watchlist entries also render as page_links, filtering into Signals
    # — brief §4 — so this checks a subset, not exact equality.)
    nav_link_labels = {pl.label for pl in at.get("page_link")}
    expected = {label for _, label in PRIMARY_NAV + FOOTER_NAV}
    missing = expected - nav_link_labels
    assert not missing, f"missing nav items: {missing}"


def test_watchlists_page_renders_without_exception():
    # Not in primary nav (brief §4: watchlists are sidebar filter entries
    # into Signals, not a standalone page) but still a real, reachable
    # hidden route — the add-a-ticker entry point independent of any
    # specific company page.
    at = AppTest.from_file(str(HARNESS_DIR / "watchlists_page.py"), default_timeout=10)
    at.run()
    assert not at.exception


def test_themes_page_all_five_themes_present():
    at = AppTest.from_file(str(HARNESS_DIR / "themes_page.py"), default_timeout=10)
    at.run()
    assert not at.exception
    tab_labels = [t.label for t in at.tabs]
    # Outer tab is one per theme; each theme also nests Map/Rotation/
    # Companies/Catalysts tabs (brief §4), so all labels appear together
    # in the flattened tab list rather than as five bare top-level tabs.
    for name in ["AI Buildout", "Humanoids", "Space", "Memory", "Photonics"]:
        assert name in tab_labels
    for name in ["Map", "Rotation", "Companies", "Catalysts"]:
        assert tab_labels.count(name) == 5
