"""Global chrome: the sidebar brand header + status block, and the
footer. `with_chrome` applies the footer around every page body when
app.py registers its st.Page objects; `render_brand_header` and
`render_sidebar_status` are both called once by app.py inside
`with st.sidebar:`, above st.navigation's own auto-rendered nav links.

Round 2: the demo-status indicator moved from a sticky main-content pill
to a compact block pinned to the bottom of the sidebar (via
`.er-sidebar-status`'s absolute positioning in theme.py) — one status
location, not duplicated across the page body.
"""
from __future__ import annotations

from typing import Callable

import streamlit as st

from src.config.settings import APP_NAME, APP_VERSION
from src.ui.theme import inject_global_css

METHODOLOGY_STATEMENT = (
    "EevaResearch separates source-backed facts, market interpretation, model "
    "inference, and uncertainty. It is for informational research only and "
    "does not provide investment advice."
)

# Abstract, minimal, monochrome "E" / signal mark — three bars of
# decreasing width (an E without its spine) plus a small dot suggesting a
# signal ping. Pure inline SVG, no image asset, no emoji.
_BRAND_MARK_SVG = """
<svg viewBox="0 0 24 24" fill="none">
    <rect x="3" y="4" width="18" height="2.2" rx="1.1" fill="currentColor"/>
    <rect x="3" y="11" width="13" height="2.2" rx="1.1" fill="currentColor"/>
    <rect x="3" y="18" width="18" height="2.2" rx="1.1" fill="currentColor"/>
    <circle cx="20" cy="12.1" r="1.6" fill="currentColor"/>
</svg>
"""


def brand_mark_svg() -> str:
    """Exposed so the hero watermark (overview.py) can reuse the exact
    same mark, oversized and near-transparent."""
    return _BRAND_MARK_SVG


def render_brand_header() -> None:
    """The EEVA / RESEARCH wordmark, the abstract mark, and the
    'AI BUILDOUT MARKET INTELLIGENCE' subtitle line, rendered at the top
    of the sidebar."""
    st.markdown(
        f"""
        <div class="er-brand">
            <div class="er-brand-mark">{_BRAND_MARK_SVG}</div>
            <div class="er-brand-word">
                <span class="er-brand-primary">EEVA</span>
                <span class="er-brand-secondary">Research</span>
            </div>
        </div>
        <div class="er-brand-subtitle">AI Buildout Market Intelligence</div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_status() -> None:
    st.markdown(
        """
        <div class="er-sidebar-status">
            <div class="er-status-line"><span class="er-dot"></span>DEMO MODE</div>
            <div class="er-status-sub">No live data connected</div>
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


def get_page(name: str):
    """Looks up a registered st.Page by the key app.py used when building
    its `pages` dict (see app.py). Returns None if not found."""
    return st.session_state.get("_pages", {}).get(name)


def with_chrome(page_fn: Callable[[], None]) -> Callable[[], None]:
    def _wrapped() -> None:
        inject_global_css()
        page_fn()
        render_footer()

    _wrapped.__name__ = getattr(page_fn, "__name__", "page")
    return _wrapped
