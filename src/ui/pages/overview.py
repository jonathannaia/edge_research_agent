"""Overview — the concise market workspace, distinct from Home (which
introduces the product). Keeps only: a compact header, Market Pulse,
Today's Read, top-3 signals, next-few catalysts, and quick-action links.
Full theme detail lives on Themes; the full rotation chart/leaders/
breadth/catalyst timeline live on Capital Rotation; the full signal feed
lives on Signal Board. The evidence feed is intentionally not shown here
— it's still used on Ticker Detail and untouched in the data layer, just
not previewed on this page in this pass.

Deliberately no signal-path hero animation here (that's Home's branded
entry-point treatment) — just a small, optional, faint watermark, kept
this page reading as a workspace rather than a second landing page.
"""
from __future__ import annotations

import streamlit as st

from src.data_access.container import get_repositories
from src.logic.theme_metrics import strongest_signals
from src.ui.chrome import brand_mark_html, get_page
from src.ui.components.cards import catalyst_timeline_row, compact_signal_row
from src.ui.components.market_brief import render_todays_read
from src.ui.components.market_pulse import render_market_pulse
from src.ui.components.section import section_header


def render() -> None:
    ctx = get_repositories()

    st.markdown(
        f'<div class="er-hero-wrap" style="padding:1rem 0 0.5rem 0;">'
        f'<div class="er-hero-watermark" style="width:140px;height:140px;opacity:0.035;">{brand_mark_html()}</div>'
        '<div class="er-hero-content">',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="er-page-title">Market Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="er-muted">Today\'s market read across all five themes.</div>', unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

    st.divider()
    render_market_pulse(ctx)

    st.divider()
    render_todays_read(ctx)

    st.divider()
    section_header("Top signals")
    for s in strongest_signals(ctx.signal_repository.get_all_signals(), limit=3):
        compact_signal_row(s)

    st.divider()
    section_header("Next catalysts")
    upcoming = ctx.catalyst_repository.get_upcoming_catalysts(limit=3)
    if not upcoming:
        st.caption("No catalysts scheduled.")
    else:
        for c in upcoming:
            catalyst_timeline_row(c)

    st.divider()
    quick_links = [
        ("Themes", "themes"),
        ("Research Chat", "research_chat"),
        ("Capital Rotation", "capital_rotation"),
        ("Signal Board", "signal_board"),
    ]
    link_cols = st.columns(len(quick_links))
    for col, (label, key) in zip(link_cols, quick_links):
        page = get_page(key)
        with col:
            if page is not None:
                with st.container(key=f"cta-tertiary-quicklink-{key}"):
                    st.page_link(page, label=f"{label} →")
