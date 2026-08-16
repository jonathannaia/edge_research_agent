"""Shared UI shell: the persistent left sidebar, global CSS loader, and
footer — replaces chrome.py's top-nav-based design (round 3) with the
sidebar-based IA from design/eevaresearch-brief.md §4. `st.navigation`
still drives routing/`st.Page` objects; only the nav *widget* itself moved
from a custom top header to `st.sidebar` + real `st.page_link`s.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Callable

import streamlit as st

from src.config.settings import APP_NAME, APP_VERSION

METHODOLOGY_STATEMENT = (
    "EevaResearch separates source-backed facts, market interpretation, model "
    "inference, and uncertainty. It is for informational research only and "
    "does not provide investment advice."
)

# Primary sidebar nav, in order — see brief §4's route table. Home and
# Company are deliberately excluded (Home is first-visit-only with no
# sidebar at all; Company is reached only by clicking a ticker).
PRIMARY_NAV: list[tuple[str, str]] = [
    ("dashboard", "Dashboard"),
    ("themes", "Themes"),
    ("signals", "Signals"),
    ("research", "Research"),
]

# Static doc pages, linked from the sidebar footer rather than the primary
# nav group.
FOOTER_NAV: list[tuple[str, str]] = [
    ("methodology", "Methodology"),
    ("disclaimer", "Disclaimer"),
    ("about", "About"),
]

# Session-state keys for unread/last-seen tracking (brief §10) — defined
# here rather than in logic/unread.py since that module stays Streamlit-free.
LAST_SEEN_KEY = "signals_last_seen_at"
READ_IDS_KEY = "read_signal_ids"

# Kept for any code that still enumerates "every visible page" (e.g. a
# future command-palette index) — primary + footer, in nav order.
NAV_ITEMS: list[tuple[str, str]] = PRIMARY_NAV + FOOTER_NAV

_LOGO_PATH = Path(__file__).resolve().parents[2] / "assets" / "eeva-logo.png"
_CSS_PATH = Path(__file__).resolve().parents[2] / "assets" / "styles.css"

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


def _css_text() -> str:
    # Deliberately uncached (unlike the logo data-URI) — it's a cheap local
    # read, and caching it meant CSS edits needed a process restart to
    # take effect during development.
    if not _CSS_PATH.exists():
        return ""
    return _CSS_PATH.read_text()


def load_css() -> None:
    css = _css_text()
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def brand_mark_html(size_px: int | None = None) -> str:
    uri = _logo_data_uri()
    style = f' style="width:{size_px}px;height:{size_px}px;"' if size_px else ""
    if uri:
        return f'<img src="{uri}" alt="" {style}/>'
    return _BRAND_MARK_SVG


def render_sidebar(current_key: str) -> None:
    from src.data_access.container import get_repositories
    from src.logic.unread import unread_count

    pages = st.session_state.get("_pages", {})
    home_page = pages.get("home")

    unread = 0
    if "signals" in pages:
        ctx = get_repositories()
        unread = unread_count(
            ctx.signal_repository.get_all_signals(),
            st.session_state.get(LAST_SEEN_KEY),
            st.session_state.get(READ_IDS_KEY, set()),
        )

    with st.sidebar:
        st.markdown('<div class="er-rail-brand">', unsafe_allow_html=True)
        brand_cols = st.columns([1, 5], vertical_alignment="center")
        with brand_cols[0]:
            st.markdown(f'<span class="er-rail-logo">{brand_mark_html()}</span>', unsafe_allow_html=True)
        with brand_cols[1]:
            if home_page is not None:
                st.page_link(home_page, label="EevaResearch")
            else:
                st.markdown('<span class="er-rail-word">EevaResearch</span>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        from src.ui.components.command_palette import render_palette_trigger

        render_palette_trigger()

        st.markdown('<div class="er-rail-group-label">Research</div>', unsafe_allow_html=True)
        for key, label in PRIMARY_NAV:
            page = pages.get(key)
            if page is None:
                continue
            active_cls = "er-rail-navactive" if key == current_key else ""
            display_label = f"{label}  ·  {unread} unread" if key == "signals" and unread else label
            with st.container(key=f"navitem-{key}"):
                if active_cls:
                    st.markdown(
                        f'<style>.st-key-navitem-{key} {{}}</style>'
                        f'<div class="{active_cls}">', unsafe_allow_html=True,
                    )
                st.page_link(page, label=display_label)
                if active_cls:
                    st.markdown("</div>", unsafe_allow_html=True)

        # Watchlists are sidebar entries filtering Signals, not a
        # standalone page (brief §4) — each link sets ?watchlist=<name> on
        # the Signals route, which signals.py resolves against the same
        # session-state watchlists used everywhere else, with counts shown
        # here per the brief's "listing the user's actual lists with counts."
        st.markdown('<div class="er-rail-group-label">Watchlists</div>', unsafe_allow_html=True)
        from src.ui.pages.watchlists import WATCHLIST_NAMES, seed_watchlists

        signals_page = pages.get("signals")
        if "watchlists" not in st.session_state:
            st.session_state["watchlists"] = seed_watchlists()
        lists = st.session_state["watchlists"]
        for name in WATCHLIST_NAMES:
            count = len(lists.get(name, []))
            if signals_page is not None:
                st.page_link(signals_page, label=f"{name} ({count})", query_params={"watchlist": name})
            else:
                st.markdown(f'<div class="er-muted" style="padding:0.2rem 0.5rem;">{name} ({count})</div>', unsafe_allow_html=True)

        # Recent research — last 5-8 threads by question text (brief §4).
        # "Thread" here is just the asked question string (research.py has
        # no richer thread object); session-only, like watchlists.
        research_page = pages.get("research")
        asked = st.session_state.get("chat_messages", [])
        if asked and research_page is not None:
            recent = list(dict.fromkeys(reversed(asked)))[:8]
            st.markdown('<div class="er-rail-group-label">Recent research</div>', unsafe_allow_html=True)
            for q in recent:
                label = q if len(q) <= 40 else q[:37] + "…"
                st.page_link(research_page, label=label)

        st.markdown('<div class="er-rail-group-label">Doc pages</div>', unsafe_allow_html=True)
        st.markdown('<div class="er-rail-footlinks">', unsafe_allow_html=True)
        for key, label in FOOTER_NAV:
            page = pages.get(key)
            if page is not None:
                st.page_link(page, label=label)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            '<div class="er-rail-status"><span class="dot"></span>Demo mode — no live data</div>',
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
    # "Disclaimer" link on every page footer (brief §17 — one of the four
    # disclaimer placements, deliberately not a dismiss-once banner).
    disclaimer_page = get_page("disclaimer")
    if disclaimer_page is not None:
        with st.container(key="cta-tertiary-footer-disclaimer"):
            st.page_link(disclaimer_page, label="Disclaimer")


def get_page(name: str):
    return st.session_state.get("_pages", {}).get(name)


def with_chrome(page_fn: Callable[[], None], nav_key: str, show_sidebar: bool = True) -> Callable[[], None]:
    def _wrapped() -> None:
        load_css()
        if show_sidebar:
            render_sidebar(nav_key)

        from src.ui.components.save_dialog import render_pending_save_dialog

        render_pending_save_dialog()

        with st.container(key="page-content"):
            page_fn()
        render_footer()

    _wrapped.__name__ = getattr(page_fn, "__name__", "page")
    return _wrapped
