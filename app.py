"""EevaResearch AI — foundation-phase entry point.

Run with: streamlit run app.py

Registers Home + the seven other visible primary pages, plus the hidden
ticker-detail template, via st.navigation(position="hidden") — Streamlit's
own nav widget is fully suppressed; src/ui/chrome.render_top_nav is the
custom replacement (see chrome.py's module docstring for why "hidden" was
chosen over the native "top" position). Page objects are stored in
st.session_state so any page can build a cross-page st.page_link.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.ui.chrome import NAV_ITEMS, with_chrome
from src.ui.pages import (
    capital_rotation,
    home,
    methodology,
    overview,
    research_chat,
    signal_board,
    themes,
    ticker_detail,
    watchlists,
)

_LOGO_PATH = Path(__file__).resolve().parent / "assets" / "eeva-logo.png"

st.set_page_config(
    page_title="EevaResearch AI",
    page_icon=str(_LOGO_PATH) if _LOGO_PATH.exists() else None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

_RENDER_FNS = {
    "home": home.render,
    "overview": overview.render,
    "themes": themes.render,
    "research_chat": research_chat.render,
    "capital_rotation": capital_rotation.render,
    "signal_board": signal_board.render,
    "watchlists": watchlists.render,
    "methodology": methodology.render,
}

_URL_PATHS = {
    "overview": "overview",
    "themes": "themes",
    "research_chat": "research-chat",
    "capital_rotation": "capital-rotation",
    "signal_board": "signal-board",
    "watchlists": "watchlists",
    "methodology": "methodology",
}

pages = {}
for key, label in NAV_ITEMS:
    is_home = key == "home"
    pages[key] = st.Page(
        with_chrome(_RENDER_FNS[key], key),
        title=label,
        # default=True always maps a page to the root path regardless of
        # url_path, per st.Page's own docs — Home is the new landing page.
        default=is_home,
        url_path=_URL_PATHS.get(key),
    )
pages["ticker_detail"] = st.Page(
    with_chrome(ticker_detail.render, "ticker_detail"), title="Ticker Detail", url_path="ticker", visibility="hidden"
)

# Each page's nav_key is already baked into its with_chrome(...) closure
# above, so render_top_nav always gets the right active key without
# needing to track "current page" separately here.
st.session_state["_pages"] = pages

selected = st.navigation(list(pages.values()), position="hidden")
selected.run()
