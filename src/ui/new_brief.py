from __future__ import annotations

import streamlit as st

from src.config.settings import Settings
from src.database.db import get_connection
from src.guardrails.citation_validator import CitationError
from src.services import research_service, ticker_service
from src.ui.components import render_brief_sections, render_mock_badge
from src.utils.export import brief_to_html, brief_to_markdown


def render(settings: Settings) -> None:
    st.caption(
        "Generate a dated, cited research brief for a ticker: fundamentals, filing highlights, "
        "management commentary, insider activity, a bull/bear read, and a full scorecard — every "
        "material claim cited to a source. Saves automatically and updates that ticker's watchlist "
        "entry (score, evidence status) when done."
    )
    with get_connection(settings) as conn:
        existing = [t["ticker"] for t in ticker_service.list_tickers(conn)]

    st.info(
        f"Data mode: **{settings.data_mode}**. Bounded to at most {settings.max_sources_per_brief} sources and "
        f"{settings.max_excerpts_per_source} excerpts per source (cost-control limits, editable via .env). "
        f"Freshness thresholds: fresh ≤{settings.freshness_fresh_days}d, aging ≤{settings.freshness_aging_days}d, "
        f"stale ≤{settings.freshness_stale_days}d."
    )

    with st.form("new_brief_form"):
        mode = st.radio("Ticker", ["Pick existing", "Add new"], horizontal=True)
        if mode == "Pick existing" and existing:
            ticker = st.selectbox("Select ticker", existing)
        else:
            ticker = st.text_input("New ticker symbol").upper().strip()
        question = st.text_area(
            "Research question (what are you trying to find out?)",
            placeholder="e.g. Is there evidence of a demand inflection in the datacom segment this quarter?",
        )
        submitted = st.form_submit_button("Generate Research Brief")

    if not submitted:
        return

    if not ticker:
        st.error("A ticker is required.")
        return

    with get_connection(settings) as conn:
        if not ticker_service.get_ticker(conn, ticker):
            ticker_service.upsert_ticker(
                conn, ticker, company_name=ticker, sector="Unclassified", subtheme="Unclassified",
                market_cap_category="Unclassified", is_mock=True,
            )
        try:
            result = research_service.generate_research_brief(conn, settings, ticker, question)
        except CitationError as exc:
            st.error(f"Brief could not be saved — it failed citation validation: {exc}")
            return

    st.success(f"Brief v{result['version']} generated and saved for {ticker}.")
    render_mock_badge(True)
    render_brief_sections(result["sections"])

    md = brief_to_markdown(ticker, result["version"], "just now", question, result["sections"])
    html = brief_to_html(ticker, result["version"], "just now", question, result["sections"])
    d1, d2 = st.columns(2)
    d1.download_button("Download as Markdown", md, file_name=f"{ticker}_brief_v{result['version']}.md")
    d2.download_button("Download as HTML", html, file_name=f"{ticker}_brief_v{result['version']}.html")
