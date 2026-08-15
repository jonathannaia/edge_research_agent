"""Global chrome rendered on every page: the demo-data status banner and
the footer. A single wrapper (with_chrome) applies both around every page
function when app.py registers its st.Page objects, so no individual page
file has to remember to call these — and a new page added later can't
forget them either.
"""
from __future__ import annotations

from typing import Callable

import streamlit as st

from src.config.settings import APP_NAME, APP_VERSION, demo_last_updated_label
from src.ui.theme import inject_global_css

METHODOLOGY_STATEMENT = (
    "EevaResearch separates source-backed facts, market interpretation, model "
    "inference, and uncertainty. It is for informational research only and "
    "does not provide investment advice."
)


def render_status_banner() -> None:
    st.markdown(
        f"""
        <div class="er-status-banner">
            <span>Demo data — no live market data connected</span>
            <span class="er-muted">Last updated: {demo_last_updated_label()}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        f"""
        <div class="er-footer">
            <div>{APP_NAME} is evidence-first: every claim is labeled Fact, Interpretation,
            Inference, or Uncertainty, and material claims link to their source.</div>
            <div style="margin-top:0.4rem;">Data freshness: demo/mock data only — no live feed connected in this phase.</div>
            <div style="margin-top:0.4rem;">{METHODOLOGY_STATEMENT}</div>
            <div style="margin-top:0.6rem;">{APP_NAME} v{APP_VERSION} · Foundation phase (demo data)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def with_chrome(page_fn: Callable[[], None]) -> Callable[[], None]:
    def _wrapped() -> None:
        inject_global_css()
        render_status_banner()
        page_fn()
        render_footer()

    _wrapped.__name__ = getattr(page_fn, "__name__", "page")
    return _wrapped
