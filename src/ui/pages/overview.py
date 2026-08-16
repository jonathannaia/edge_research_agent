"""Overview — a short executive landing page (round 2 IA), not a page
holding every feature. Keeps only: hero, Market Pulse, Today's Read,
top-3 signals, next-few catalysts, and quick-action links. Full theme
detail lives on Themes; the full rotation chart/leaders/breadth/catalyst
timeline live on Capital Rotation; the full signal feed lives on Signal
Board. The evidence feed is intentionally not shown here — it's still
used on Ticker Detail and untouched in the data layer, just not
previewed on this page in this pass.
"""
from __future__ import annotations

import streamlit as st

from src.data_access.container import get_repositories
from src.logic.theme_metrics import strongest_signals
from src.ui.chrome import brand_mark_svg, get_page
from src.ui.components.cards import catalyst_timeline_row, compact_signal_row
from src.ui.components.market_brief import render_todays_read
from src.ui.components.market_pulse import render_market_pulse
from src.ui.components.section import section_header


def render() -> None:
    ctx = get_repositories()
    theme_names = ", ".join(t.name for t in ctx.theme_repository.get_all_themes())

    st.markdown(
        f'<div class="er-hero-wrap"><div class="er-hero-watermark">{brand_mark_svg()}</div>'
        '<svg class="er-hero-signal-svg" viewBox="0 0 800 260" preserveAspectRatio="none">'
        '<path class="er-signal-path" d="M-50,190 C150,150 250,230 450,170 S650,90 850,130"/>'
        '<path class="er-signal-path er-signal-path-2" d="M-50,70 C200,120 350,30 550,90 S750,150 850,100"/>'
        '<circle class="er-signal-node" cx="120" cy="170" r="2.5"/>'
        '<circle class="er-signal-node er-signal-node-2" cx="420" cy="90" r="2"/>'
        '<circle class="er-signal-node er-signal-node-3" cx="620" cy="120" r="2.5"/>'
        '</svg><div class="er-hero-content">',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="er-eyebrow">EevaResearch · Market Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="er-hero-title">EevaResearch</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="er-hero-sub">Track the infrastructure, bottlenecks, and capital flows behind the AI buildout.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="er-muted" style="margin-bottom:1.25rem;">Tracking {theme_names}.</div>', unsafe_allow_html=True)

    cta_cols = st.columns([1, 1, 1])
    with cta_cols[0]:
        page = get_page("themes")
        if page is not None:
            with st.container(key="cta-primary-hero-themes"):
                st.page_link(page, label="Explore themes", width="stretch")
    with cta_cols[1]:
        page = get_page("research_chat")
        if page is not None:
            with st.container(key="cta-secondary-hero-chat"):
                st.page_link(page, label="Ask research chat", width="stretch")
    with cta_cols[2]:
        page = get_page("capital_rotation")
        if page is not None:
            with st.container(key="cta-tertiary-hero-rotation"):
                st.page_link(page, label="View capital rotation →")
    st.markdown("</div></div>", unsafe_allow_html=True)

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
