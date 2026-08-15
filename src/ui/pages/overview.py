"""Overview — the market command center. Opens with the editorial Market
Brief, then structured theme/leaders/catalysts/rotation/signal/evidence
previews. Every number on this page comes from data/seed/ via AppContext,
not hardcoded here.
"""
from __future__ import annotations

import streamlit as st

from src.data_access.container import get_repositories
from src.logic.theme_metrics import rank_by_performance, strongest_signals
from src.ui.components.cards import catalyst_row, evidence_row, signal_card, theme_card
from src.ui.components.market_brief import render_market_brief
from src.ui.components.section import section_header


def _get_page(name: str):
    return st.session_state.get("_pages", {}).get(name)


def render() -> None:
    ctx = get_repositories()
    themes = ctx.theme_repository.get_all_themes()
    theme_by_slug = {t.slug: t for t in themes}
    metrics = {m.theme_slug: m for m in ctx.market_data_provider.get_rotation_metrics()}

    st.markdown("# EevaResearch AI")
    st.markdown(
        "Evidence-first thematic research across AI Buildout, Humanoids, Space, Memory, "
        "and Photonics — every material claim traces to evidence, and every read is labeled "
        "Fact, Interpretation, Inference, or Uncertainty."
    )
    cta_cols = st.columns(3)
    with cta_cols[0]:
        page = _get_page("themes")
        if page is not None:
            st.page_link(page, label="Explore Themes", width="stretch")
    with cta_cols[1]:
        page = _get_page("research_chat")
        if page is not None:
            st.page_link(page, label="Open Research Chat", width="stretch")
    with cta_cols[2]:
        page = _get_page("capital_rotation")
        if page is not None:
            st.page_link(page, label="View Capital Rotation", width="stretch")

    st.divider()
    render_market_brief(ctx)

    st.divider()
    section_header("Theme performance", "Demo data — placeholder relative-performance and breadth figures.")
    for i in range(0, len(themes), 2):
        cols = st.columns(2)
        for col, theme in zip(cols, themes[i : i + 2]):
            with col:
                theme_card(theme, metrics.get(theme.slug), page=_get_page("themes"))

    st.divider()
    section_header("Leaders and laggards", "Ranked by demo relative-performance figure, highest first.")
    ranked = rank_by_performance(list(metrics.values()))
    rows = [
        {"Theme": theme_by_slug[m.theme_slug].name, "Relative performance": f"{m.relative_performance_pct:+.1f}%", "Breadth": f"{m.breadth_pct:.0f}%"}
        for m in ranked
        if m.theme_slug in theme_by_slug
    ]
    st.dataframe(rows, hide_index=True, width="stretch")

    st.divider()
    section_header("Upcoming catalysts", "Demo placeholder catalyst calendar across all five themes.")
    upcoming = ctx.catalyst_repository.get_upcoming_catalysts(limit=6)
    if not upcoming:
        st.info("No catalysts loaded.")
    else:
        for c in upcoming:
            catalyst_row(c)

    st.divider()
    section_header("Capital Rotation preview", "Relative performance by theme — demo data.")
    chart_data = {theme_by_slug[m.theme_slug].name: m.relative_performance_pct for m in ranked if m.theme_slug in theme_by_slug}
    st.bar_chart(chart_data)
    page = _get_page("capital_rotation")
    if page is not None:
        st.page_link(page, label="View full Capital Rotation page →")

    st.divider()
    section_header("Signal Board preview", "Strongest current demo signals.")
    for s in strongest_signals(ctx.signal_repository.get_all_signals(), limit=2):
        signal_card(s)
    page = _get_page("signal_board")
    if page is not None:
        st.page_link(page, label="View full Signal Board →")

    st.divider()
    section_header("Recently updated research", "Latest demo evidence across all themes.")
    for ev in ctx.evidence_repository.get_recent_evidence(limit=3):
        evidence_row(ev)
