"""Edge Research Agent — Streamlit entry point.

Run with: streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from src.config.settings import get_settings
from src.database.db import get_connection, init_db
from src.database.seed import seed_demo_data
from src.services import ticker_service
from src.ui import (
    alerts as ui_alerts,
    app_settings as ui_app_settings,
    compare_snapshots as ui_compare,
    dashboard as ui_dashboard,
    data_provider_settings as ui_data_providers,
    guardrails_page as ui_guardrails,
    new_brief as ui_new_brief,
    scoring_settings as ui_scoring_settings,
    sources as ui_sources,
    ticker_detail as ui_ticker_detail,
    watchlist as ui_watchlist,
)
from src.ui.components import render_top_disclaimer

st.set_page_config(page_title="Edge Research Agent", page_icon=None, layout="wide")


@st.cache_resource
def _bootstrap() -> None:
    settings = get_settings()
    init_db(settings)
    with get_connection(settings) as conn:
        has_tickers = len(ticker_service.list_tickers(conn)) > 0
    if not has_tickers:
        seed_demo_data()


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
}

with st.sidebar:
    st.title("Edge Research Agent")
    st.caption(f"v{settings.app_version} · Data mode: **{settings.data_mode}**")
    page_name = st.radio("Navigate", list(PAGES.keys()), label_visibility="collapsed", key="nav_page")
    st.divider()
    render_top_disclaimer()

st.title(page_name)
PAGES[page_name].render(settings)
