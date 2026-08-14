"""EevaResearch AI — Streamlit entry point.

Run with: streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from src.config.settings import get_settings
from src.database.db import init_db
from src.ui import (
    alerts as ui_alerts,
    app_settings as ui_app_settings,
    compare_snapshots as ui_compare,
    dashboard as ui_dashboard,
    data_provider_settings as ui_data_providers,
    guardrails_page as ui_guardrails,
    new_brief as ui_new_brief,
    radar as ui_radar,
    radar_trends as ui_radar_trends,
    scoring_settings as ui_scoring_settings,
    sources as ui_sources,
    ticker_detail as ui_ticker_detail,
    watchlist as ui_watchlist,
)
from src.ui.components import inject_button_glow, render_top_disclaimer

st.set_page_config(page_title="EevaResearch AI", page_icon=None, layout="wide")
inject_button_glow()


@st.cache_resource
def _bootstrap() -> None:
    init_db(get_settings())


_bootstrap()
settings = get_settings()

PAGES = {
    "Dashboard": ui_dashboard,
    "Watchlist": ui_watchlist,
    "Ticker Detail": ui_ticker_detail,
    "New Research Brief": ui_new_brief,
    "Compare Snapshots": ui_compare,
    "Alerts / Review Queue": ui_alerts,
    "Sources": ui_sources,
    "Scoring Settings": ui_scoring_settings,
    "Data Provider Settings": ui_data_providers,
    "Research Rules / Guardrails": ui_guardrails,
    "App Settings": ui_app_settings,
    "Radar": ui_radar,
    "Radar Trends": ui_radar_trends,
}

# Two independent categories, per the user's split: everything you drive
# yourself (Watchlist/Research/etc.) vs. Radar, which runs unattended on a
# schedule. Keeping them as separate sidebar sections makes that boundary
# visible instead of burying Radar in one long page list.
SECTIONS = {
    "Manual Research": [
        "Dashboard", "Watchlist", "Ticker Detail", "New Research Brief", "Compare Snapshots",
        "Alerts / Review Queue", "Sources", "Scoring Settings", "Data Provider Settings",
        "Research Rules / Guardrails", "App Settings",
    ],
    "Radar (Autonomous)": ["Radar", "Radar Trends"],
}
PAGE_SECTION = {page: section for section, pages in SECTIONS.items() for page in pages}

if "_requested_page" in st.session_state:
    st.session_state["nav_page"] = st.session_state.pop("_requested_page")

current_page = st.session_state.get("nav_page", "Dashboard")
current_section = PAGE_SECTION.get(current_page, next(iter(SECTIONS)))

with st.sidebar:
    st.title("EevaResearch AI")
    st.caption(f"v{settings.app_version} · Data mode: **{settings.data_mode}**")
    section_name = st.radio("Section", list(SECTIONS.keys()), index=list(SECTIONS.keys()).index(current_section), key="nav_section")
    section_pages = SECTIONS[section_name]
    if st.session_state.get("nav_page") not in section_pages:
        st.session_state["nav_page"] = section_pages[0]
    page_name = st.radio("Page", section_pages, label_visibility="collapsed", key="nav_page")
    st.divider()
    render_top_disclaimer()

st.title(page_name)
PAGES[page_name].render(settings)
