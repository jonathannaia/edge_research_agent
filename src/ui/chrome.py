"""Global chrome: the custom top navigation header (logo, wordmark, tabs,
status) and the footer. Round 3 replaces the sidebar-based nav entirely —
`st.navigation(..., position="hidden")` suppresses Streamlit's own nav
widget, and `render_top_nav` here is the fully custom replacement, built
from real `st.page_link` controls. Each page's `nav_key` (which tab to
highlight as active) is baked into its `with_chrome(fn, nav_key)` closure
when app.py builds the `pages` dict — no separate session-state tracking
needed for that.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Callable

import streamlit as st

from src.config.settings import APP_NAME, APP_VERSION
from src.ui.theme import inject_global_css

METHODOLOGY_STATEMENT = (
    "EevaResearch separates source-backed facts, market interpretation, model "
    "inference, and uncertainty. It is for informational research only and "
    "does not provide investment advice."
)

# (session-state key, display label) for every visible primary page, in
# nav order. Defined once here — app.py imports this to build its `pages`
# dict so the two never drift apart.
NAV_ITEMS: list[tuple[str, str]] = [
    ("home", "Home"),
    ("overview", "Overview"),
    ("themes", "Themes"),
    ("research_chat", "Research Chat"),
    ("capital_rotation", "Capital Rotation"),
    ("signal_board", "Signal Board"),
    ("watchlists", "Watchlists"),
    ("methodology", "Methodology"),
]

_LOGO_PATH = Path(__file__).resolve().parents[2] / "assets" / "eeva-logo.png"

# Fallback mark (three bars + a dot) used only if the real logo file is
# ever missing — kept so the header never renders broken.
_BRAND_MARK_SVG = """
<svg viewBox="0 0 24 24" fill="none">
    <rect x="3" y="4" width="18" height="2.2" rx="1.1" fill="currentColor"/>
    <rect x="3" y="11" width="13" height="2.2" rx="1.1" fill="currentColor"/>
    <rect x="3" y="18" width="18" height="2.2" rx="1.1" fill="currentColor"/>
    <circle cx="20" cy="12.1" r="1.6" fill="currentColor"/>
</svg>
"""


@st.cache_data(show_spinner=False)
def _logo_data_uri() -> str | None:
    if not _LOGO_PATH.exists():
        return None
    encoded = base64.b64encode(_LOGO_PATH.read_bytes()).decode()
    return f"data:image/png;base64,{encoded}"


def brand_mark_html(size_px: int | None = None) -> str:
    """The real Eeva logo as an <img>, or the abstract SVG fallback if the
    asset is ever missing. Used for the header mark and both hero
    watermarks so there's exactly one source of truth for the mark."""
    uri = _logo_data_uri()
    style = f' style="width:{size_px}px;height:{size_px}px;"' if size_px else ""
    if uri:
        return f'<img src="{uri}" alt="" {style}/>'
    return _BRAND_MARK_SVG


def render_top_nav(current_key: str) -> None:
    pages = st.session_state.get("_pages", {})
    home_page = pages.get("home")

    st.markdown('<div class="er-topnav">', unsafe_allow_html=True)
    left, center, right = st.columns([1.7, 7.5, 1.1], vertical_alignment="center")

    with left:
        st.markdown(
            f"""
            <div class="er-topnav-brand">
                <a href="/" class="er-logo-link" title="Go to Home" aria-label="Go to Home">
                    <span class="er-logo-mark">{brand_mark_html()}</span>
                </a>
                <div class="er-brand-word">
                    <span class="er-brand-primary">EEVARESEARCH</span>
                    <span class="er-brand-secondary">Market Intelligence</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with center:
        # Desktop: a full horizontal tab row. Mobile (<=900px, see
        # theme.py): CSS swaps this out for the popover menu below —
        # both are always rendered, only one is visible at a time, so
        # there's no fragile JS/viewport-detection involved.
        with st.container(key="nav-desktop-row"):
            # Weighted by label length rather than an equal 8-way split —
            # "Capital Rotation" needs meaningfully more room than "Home"
            # within the same total width.
            weights = [len(label) + 5 for _, label in NAV_ITEMS]
            tab_cols = st.columns(weights, gap="small")
            for col, (key, label) in zip(tab_cols, NAV_ITEMS):
                page = pages.get(key)
                with col:
                    tab_key = f"navtab-{key}"
                    if key == current_key:
                        st.markdown(
                            f'<style>.st-key-{tab_key} {{ background: rgba(245,245,245,0.06) !important; '
                            f'box-shadow: inset 0 -2px 0 var(--er-white), 0 0 10px rgba(199,214,227,0.14) !important; '
                            f'border-radius: 6px; }} .st-key-{tab_key} a p {{ color: var(--er-white) !important; '
                            f'font-weight: 600 !important; }}</style>',
                            unsafe_allow_html=True,
                        )
                    with st.container(key=tab_key):
                        if page is not None:
                            st.page_link(page, label=label)

        with st.container(key="nav-mobile-menu"):
            with st.popover("Menu", width="stretch"):
                if home_page is not None:
                    st.page_link(home_page, label="Home")
                for key, label in NAV_ITEMS:
                    if key == "home":
                        continue
                    page = pages.get(key)
                    if page is not None:
                        st.page_link(page, label=label)

    with right:
        st.markdown(
            """
            <div class="er-topnav-status">
                <span class="er-status-line"><span class="er-dot"></span>DEMO MODE</span>
                <span class="er-status-sub">No live data</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


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


def with_chrome(page_fn: Callable[[], None], nav_key: str) -> Callable[[], None]:
    def _wrapped() -> None:
        inject_global_css()
        render_top_nav(nav_key)
        # A plain st.markdown('<div>') does NOT wrap subsequent st.* calls
        # (each renders as a DOM sibling, not a child of a preceding
        # unclosed tag) — confirmed the hard way earlier in this project.
        # st.container(key=...) is the real mechanism: it gives its
        # contents a stable `st-key-page-content` class theme.py can
        # target for the entrance animation.
        with st.container(key="page-content"):
            page_fn()
        render_footer()

    _wrapped.__name__ = getattr(page_fn, "__name__", "page")
    return _wrapped
