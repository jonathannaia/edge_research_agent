"""Overview — the market command center. Opens with a hero over an ambient
background, the compact Market Pulse strip, then the editorial Market
Brief, then structured theme/leaders/catalysts/rotation/signal/evidence
sections. Every number on this page comes from data/seed/ via AppContext,
not hardcoded here.
"""
from __future__ import annotations

import streamlit as st

from src.data_access.container import get_repositories
from src.logic.theme_metrics import rank_by_performance, strongest_signals
from src.ui.chrome import get_page
from src.ui.components.cards import catalyst_timeline_row, evidence_row, signal_card, theme_card
from src.ui.components.charts import rotation_bar_chart
from src.ui.components.market_brief import render_market_brief
from src.ui.components.market_pulse import render_market_pulse
from src.ui.components.section import section_header
from src.ui.components.tables import leaderboard_table


def render() -> None:
    ctx = get_repositories()
    themes = ctx.theme_repository.get_all_themes()
    theme_by_slug = {t.slug: t for t in themes}
    metrics = {m.theme_slug: m for m in ctx.market_data_provider.get_rotation_metrics()}
    theme_names = ", ".join(t.name for t in themes)

    st.markdown('<div class="er-hero-wrap"><div class="er-hero-bg"></div><div class="er-hero-content">', unsafe_allow_html=True)
    st.markdown('<div class="er-eyebrow">MARKET INTELLIGENCE · DEMO ENVIRONMENT</div>', unsafe_allow_html=True)
    st.markdown('<div class="er-hero-title">EevaResearch</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="er-hero-sub">Follow the infrastructure, bottlenecks, and capital flows behind the AI buildout.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="er-muted" style="margin-bottom:1.25rem;">Tracking {theme_names}.</div>', unsafe_allow_html=True)

    cta_cols = st.columns([1, 1, 1])
    with cta_cols[0]:
        page = get_page("themes")
        if page is not None:
            with st.container(key="cta-primary-hero-themes"):
                st.page_link(page, label="Explore themes →", width="stretch")
    with cta_cols[1]:
        page = get_page("research_chat")
        if page is not None:
            with st.container(key="cta-secondary-hero-chat"):
                st.page_link(page, label="Ask research chat →", width="stretch")
    with cta_cols[2]:
        page = get_page("capital_rotation")
        if page is not None:
            with st.container(key="cta-tertiary-hero-rotation"):
                st.page_link(page, label="View capital rotation →")
    st.markdown("</div></div>", unsafe_allow_html=True)

    render_market_pulse(ctx)

    st.divider()
    render_market_brief(ctx)

    st.divider()
    section_header("Theme performance", "Demo data — placeholder relative-performance and breadth figures.")
    for i in range(0, len(themes), 2):
        cols = st.columns(2)
        for col, theme in zip(cols, themes[i : i + 2]):
            with col:
                theme_card(theme, metrics.get(theme.slug), page=get_page("themes"))

    st.divider()
    section_header("Leaders and laggards", "Ranked by demo relative-performance figure, highest first.")
    ranked = rank_by_performance(list(metrics.values()))
    leaderboard_table(ranked, theme_by_slug)

    st.divider()
    section_header("Upcoming catalysts", "Demo placeholder catalyst calendar across all five themes.")
    upcoming = ctx.catalyst_repository.get_upcoming_catalysts(limit=6)
    if not upcoming:
        st.info("No catalysts loaded.")
    else:
        for c in upcoming:
            catalyst_timeline_row(c)

    st.divider()
    section_header("Capital Rotation preview", "Relative performance by theme — demo data.")
    st.altair_chart(rotation_bar_chart(ranked, theme_by_slug), width="stretch")
    if ranked and ranked[0].theme_slug in theme_by_slug:
        st.markdown(
            f'<div class="er-muted">Rotation read: <strong>{theme_by_slug[ranked[0].theme_slug].name}</strong> leads this '
            f'demo snapshot; <strong>{theme_by_slug[ranked[-1].theme_slug].name}</strong> is weakest. '
            "See Capital Rotation for the full breakdown.</div>",
            unsafe_allow_html=True,
        )
    page = get_page("capital_rotation")
    if page is not None:
        with st.container(key="cta-tertiary-overview-rotation"):
            st.page_link(page, label="View full Capital Rotation page →")

    st.divider()
    section_header("Signal Board preview", "Strongest current demo signals.")
    for s in strongest_signals(ctx.signal_repository.get_all_signals(), limit=2):
        signal_card(s, theme_page=get_page("themes"))
    page = get_page("signal_board")
    if page is not None:
        with st.container(key="cta-tertiary-overview-signals"):
            st.page_link(page, label="View full Signal Board →")

    st.divider()
    section_header("Recently updated research", "Latest demo evidence across all themes.")
    for ev in ctx.evidence_repository.get_recent_evidence(limit=3):
        evidence_row(ev)
