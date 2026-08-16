"""Global chrome: the sidebar brand header, the sticky demo-status pill, and
the footer. `with_chrome` applies the status pill + footer around every page
body when app.py registers its st.Page objects; `render_brand_header` is
called once by app.py inside `with st.sidebar:`, above st.navigation's own
auto-rendered nav links.
"""
from __future__ import annotations

from typing import Callable

import streamlit as st

from src.config.settings import APP_NAME, APP_VERSION, demo_last_updated_label
from src.ui.theme import inject_global_css

def get_page(name: str):
    """Looks up a registered st.Page by the key app.py used when building
    its `pages` dict (see app.py). Returns None if not found — callers
    render no link rather than a broken one, which also makes this safe
    to call from an AppTest harness that doesn't set up app.py's full
    session state."""
    return st.session_state.get("_pages", {}).get(name)


METHODOLOGY_STATEMENT = (
    "EevaResearch separates source-backed facts, market interpretation, model "
    "inference, and uncertainty. It is for informational research only and "
    "does not provide investment advice."
)


def render_brand_header() -> None:
    """The EEVA / RESEARCH wordmark + a small CSS-drawn node/signal mark
    (three concentric shapes, no image asset, no emoji), rendered at the
    top of the sidebar."""
    st.markdown(
        """
        <div class="er-brand">
            <div class="er-brand-mark"><span></span><span></span><span></span></div>
            <div class="er-brand-word">
                <span class="er-brand-primary">EEVA</span>
                <span class="er-brand-secondary">Research</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_banner() -> None:
    st.markdown(
        f"""
        <div class="er-status-row">
            <span class="er-status-pill"><span class="er-dot"></span>DEMO MODE — NO LIVE DATA</span>
            <span class="er-status-meta">Last updated: {demo_last_updated_label()}</span>
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
            <div class="er-footer-version">{APP_NAME} v{APP_VERSION} · Foundation phase (demo data)</div>
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
