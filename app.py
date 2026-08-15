"""EevaResearch AI — foundation-phase entry point.

Run with: streamlit run app.py

Registers all pages (seven visible primary pages + one hidden ticker-detail
template) via st.navigation, stores the Page objects in st.session_state so
components like the Market Brief and Themes page can build st.page_link
references to each other, and wraps every page with the shared chrome
(status banner + footer) via src/ui/chrome.with_chrome.
"""
from __future__ import annotations

import streamlit as st

from src.ui.chrome import with_chrome
from src.ui.pages import (
    capital_rotation,
    methodology,
    overview,
    research_chat,
    signal_board,
    themes,
    ticker_detail,
    watchlists,
)

st.set_page_config(page_title="EevaResearch AI", layout="wide")

pages = {
    # url_path is intentionally omitted: default=True always maps this page
    # to the root path ("") regardless of url_path, per st.Page's own docs.
    "overview": st.Page(with_chrome(overview.render), title="Overview", default=True),
    "themes": st.Page(with_chrome(themes.render), title="Themes", url_path="themes"),
    "research_chat": st.Page(with_chrome(research_chat.render), title="Research Chat", url_path="research-chat"),
    "capital_rotation": st.Page(with_chrome(capital_rotation.render), title="Capital Rotation", url_path="capital-rotation"),
    "signal_board": st.Page(with_chrome(signal_board.render), title="Signal Board", url_path="signal-board"),
    "watchlists": st.Page(with_chrome(watchlists.render), title="Watchlists", url_path="watchlists"),
    "methodology": st.Page(with_chrome(methodology.render), title="Methodology", url_path="methodology"),
    "ticker_detail": st.Page(
        with_chrome(ticker_detail.render), title="Ticker Detail", url_path="ticker", visibility="hidden"
    ),
}

# Set before st.navigation runs the selected page's body, so any page can
# build a cross-page st.page_link from this same dict (see e.g.
# src/ui/components/market_brief.py's _get_page helper).
st.session_state["_pages"] = pages

selected = st.navigation(list(pages.values()))
selected.run()
