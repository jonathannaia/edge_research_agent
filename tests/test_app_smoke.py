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

HARNESS_DIR = Path(__file__).parent / "apptest_pages"

PRIMARY_PAGES = [
    "overview_page.py",
    "themes_page.py",
    "research_chat_page.py",
    "capital_rotation_page.py",
    "signal_board_page.py",
    "watchlists_page.py",
    "methodology_page.py",
]


@pytest.mark.parametrize("harness_file", PRIMARY_PAGES)
def test_primary_page_renders_without_exception(harness_file):
    at = AppTest.from_file(str(HARNESS_DIR / harness_file), default_timeout=10)
    at.run()
    assert not at.exception, f"{harness_file} raised: {at.exception}"


@pytest.mark.parametrize("harness_file", PRIMARY_PAGES)
def test_primary_page_renders_footer(harness_file):
    # Demo status now lives in the sidebar (see test_sidebar_status_renders),
    # not per-page — with_chrome only guarantees the footer.
    at = AppTest.from_file(str(HARNESS_DIR / harness_file), default_timeout=10)
    at.run()
    all_html = " ".join(m.value for m in at.markdown)
    assert "does not provide investment advice" in all_html
    assert "EevaResearch AI v" in all_html


def test_ticker_detail_page_receives_demo_symbol_via_query_params():
    at = AppTest.from_file(str(HARNESS_DIR / "ticker_detail_page.py"), default_timeout=10)
    at.query_params["symbol"] = "DEMO"
    at.run()
    assert not at.exception
    all_markdown = " ".join(m.value for m in at.markdown)
    assert "Nova Aperture Systems" in all_markdown


def test_ticker_detail_page_unknown_symbol_shows_empty_state_not_exception():
    at = AppTest.from_file(str(HARNESS_DIR / "ticker_detail_page.py"), default_timeout=10)
    at.query_params["symbol"] = "NOTREAL"
    at.run()
    assert not at.exception
    infos = " ".join(i.value for i in at.info)
    assert "No ticker found" in infos


def test_ticker_detail_shows_demo_evidence_with_no_fabricated_source():
    # Overview no longer renders an evidence feed (round-2 IA change) — the
    # evidence component/data is preserved and still used on Ticker Detail.
    at = AppTest.from_file(str(HARNESS_DIR / "ticker_detail_page.py"), default_timeout=10)
    at.query_params["symbol"] = "DEMO"
    at.run()
    assert not at.exception
    all_markdown = " ".join(m.value for m in at.markdown)
    assert "EevaResearch Demo Data" in all_markdown
    assert "no external source" in all_markdown


def test_sidebar_brand_header_and_status_render():
    at = AppTest.from_file(str(HARNESS_DIR / "sidebar_brand_header.py"), default_timeout=10)
    at.run()
    assert not at.exception
    all_html = " ".join(m.value for m in at.sidebar.markdown)
    assert "EEVA" in all_html
    assert "Research" in all_html
    assert "DEMO MODE" in all_html
    assert "No live data connected" in all_html


def test_themes_page_all_five_themes_present():
    at = AppTest.from_file(str(HARNESS_DIR / "themes_page.py"), default_timeout=10)
    at.run()
    assert not at.exception
    tab_labels = [t.label for t in at.tabs]
    assert tab_labels == ["AI Buildout", "Humanoids", "Space", "Memory", "Photonics"]
