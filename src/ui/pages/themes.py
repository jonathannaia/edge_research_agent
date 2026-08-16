"""Themes — one shared detail renderer reused across all five fixed
themes via tabs, rather than five near-duplicate page files. Each theme's
data (subthemes, tickers, signals, catalysts, rotation metric) comes from
AppContext, so a real ticker universe drops in later without touching this
file.
"""
from __future__ import annotations

import streamlit as st

from src.data_access.container import AppContext, get_repositories
from src.models.models import Theme
from src.ui.chrome import get_page
from src.ui.components.cards import catalyst_timeline_row, metric_pair_html, signal_card, theme_icon_html
from src.ui.components.empty_state import empty_state
from src.ui.components.filters import ticker_filter_bar
from src.ui.components.section import section_header
from src.ui.components.tables import ticker_table


def _render_theme_detail(theme: Theme, ctx: AppContext) -> None:
    st.markdown(theme_icon_html(theme.slug), unsafe_allow_html=True)
    st.markdown(f'<div class="er-page-title" style="font-size:1.6rem;">{theme.name}</div>', unsafe_allow_html=True)
    st.write(theme.description)

    metric = ctx.market_data_provider.get_rotation_metric_for_theme(theme.slug)
    if metric:
        st.markdown(
            metric_pair_html("Rel. perf.", f"{metric.relative_performance_pct:+.1f}%", "Breadth", f"{metric.breadth_pct:.0f}%"),
            unsafe_allow_html=True,
        )

    section_header("Value-chain subcategories")
    sub_cols = st.columns(min(len(theme.subthemes), 3) or 1)
    for i, sub in enumerate(theme.subthemes):
        with sub_cols[i % len(sub_cols)]:
            with st.container(border=True, key=f"card-subtheme-{sub.slug}"):
                st.markdown(f'<div class="er-card-title" style="font-size:0.95rem;">{sub.name}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="er-muted">{sub.description}</div>', unsafe_allow_html=True)

    section_header("Tickers", "Filters are designed for the full curated ticker universe (Phase 3) — with one demo ticker, most won't narrow anything yet.")
    tickers = ctx.ticker_repository.get_tickers_for_theme(theme.slug)
    catalysts = ctx.catalyst_repository.get_catalysts_for_theme(theme.slug)
    filtered = ticker_filter_bar(tickers, theme.subthemes, catalysts, key_prefix=theme.slug)
    ticker_table(filtered)
    demo_ticker = next((t for t in filtered if t.is_demo), None)
    if demo_ticker is not None:
        ticker_page = get_page("ticker_detail")
        if ticker_page is not None:
            with st.container(key=f"cta-tertiary-demo-ticker-{theme.slug}"):
                st.page_link(ticker_page, label=f"View {demo_ticker.symbol} demo ticker page →", query_params={"symbol": demo_ticker.symbol})

    section_header("Related signals")
    theme_signals = ctx.signal_repository.get_signals_for_theme(theme.slug)
    if not theme_signals:
        empty_state("No signals for this theme yet.")
    else:
        for s in theme_signals:
            signal_card(s)

    section_header("Catalysts")
    if not catalysts:
        empty_state("No catalysts scheduled for this theme yet.")
    else:
        for c in catalysts:
            catalyst_timeline_row(c)


def render() -> None:
    ctx = get_repositories()
    themes = ctx.theme_repository.get_all_themes()

    st.markdown('<div class="er-page-title">Themes</div>', unsafe_allow_html=True)
    st.write("Organized research across the five themes EevaResearch tracks — value chains, signals, catalysts, and (eventually) a curated ticker universe.")

    if not themes:
        empty_state("No themes loaded.")
        return

    tabs = st.tabs([t.name for t in themes])
    for tab, theme in zip(tabs, themes):
        with tab:
            _render_theme_detail(theme, ctx)
