"""Dashboard — the concise market workspace, distinct from Home (which
introduces the product) and the default route on repeat visits (brief §4:
Dashboard absorbs Overview). Brief §9 spec: a theme-health breadth strip
(the one place the animated fill bar is used), a "New signals" card with
unread-dot/last-seen-divider tracking (brief §10), a watchlist table, and a
compact capital-rotation panel (leaders/laggards as static diverging bars —
the full Capital Rotation page's chart/leaderboard/catalyst-timeline moves
into Themes' Rotation tab in a later checkpoint, not duplicated here).
"""
from __future__ import annotations

import streamlit as st

from src.data_access.container import get_repositories
from src.logic.formatting import fmt_datetime, fmt_pct
from src.logic.theme_metrics import leaders_and_laggards, rank_by_performance
from src.logic.unread import is_unread, unread_count
from src.logic.watchlist_risk import is_moving_against_thesis
from src.models.models import Direction
from src.ui.components.badges import direction_dot_html
from src.ui.components.cards import catalyst_timeline_row, signal_card
from src.ui.components.empty_state import empty_state
from src.ui.components.freshness import freshness_chip, panel_header
from src.ui.pages.watchlists import WATCHLIST_NAMES, seed_watchlists
from src.ui.ui import LAST_SEEN_KEY, READ_IDS_KEY, brand_mark_html, get_page


def _infer_direction(relative_performance_pct: float) -> Direction:
    if relative_performance_pct > 2:
        return Direction.IMPROVING
    if relative_performance_pct < -2:
        return Direction.WEAKENING
    return Direction.MIXED


def _render_breadth_strip(ctx) -> None:
    panel_header("Theme health", key="fresh-breadth")
    themes = ctx.theme_repository.get_all_themes()
    metrics = {m.theme_slug: m for m in ctx.market_data_provider.get_rotation_metrics()}
    cols = st.columns(min(len(themes), 5) or 1)
    for i, (col, theme) in enumerate(zip(cols, themes)):
        metric = metrics.get(theme.slug)
        with col:
            with st.container(border=True, key=f"card-breadth-{theme.slug}"):
                st.markdown(f'<div class="er-metric-label">{theme.name}</div>', unsafe_allow_html=True)
                if metric is None:
                    st.markdown('<div class="er-muted">No data.</div>', unsafe_allow_html=True)
                    continue
                st.markdown(f'<div class="er-metric-value">{fmt_pct(metric.relative_performance_pct)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="er-muted">{metric.breadth_pct:.0f}% breadth</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="bar" style="margin-top:0.5rem;">'
                    f'<i style="--w:{metric.breadth_pct:.0f}%; animation-delay:{i * 40}ms;"></i></div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div style="margin-top:0.4rem;">{direction_dot_html(_infer_direction(metric.relative_performance_pct))}</div>',
                    unsafe_allow_html=True,
                )


def _render_new_signals(ctx) -> None:
    signals = sorted(ctx.signal_repository.get_all_signals(), key=lambda s: s.last_updated, reverse=True)
    prev_last_seen = st.session_state.get(LAST_SEEN_KEY)
    read_ids = st.session_state.setdefault(READ_IDS_KEY, set())
    n_unread = unread_count(signals, prev_last_seen, read_ids)

    panel_header(f"New signals — {n_unread} unread" if n_unread else "New signals", key="fresh-newsignals")
    if not signals:
        st.caption("No signals loaded.")
        return

    unread = [s for s in signals if is_unread(s, prev_last_seen, read_ids)]
    read = [s for s in signals if not is_unread(s, prev_last_seen, read_ids)]

    if not unread:
        empty_state(
            "No new signals since Thursday",
            "The feed checks EDGAR, TDnet, DART, CNINFO, and HKEX every 15 minutes.",
            action_label="View all signals",
            action_page=get_page("signals"),
            key="dashboard-no-new-signals",
        )
    for s in unread:
        signal_card(s, evidence_repository=ctx.evidence_repository, unread=True)

    if prev_last_seen:
        st.markdown(f'<div class="er-divider">You were last here {fmt_datetime(prev_last_seen)}</div>', unsafe_allow_html=True)

    for s in read[:5]:
        st.markdown(
            f'<div class="er-row"><span class="er-card-title" style="font-size:0.88rem;">{s.title}</span> '
            f'<span class="er-muted">— {direction_dot_html(s.direction)}</span></div>',
            unsafe_allow_html=True,
        )

    signals_page = get_page("signals")
    if signals_page is not None:
        with st.container(key="cta-tertiary-dashboard-signals"):
            st.page_link(signals_page, label="View all signals →")


def _render_watchlist_table(ctx) -> None:
    panel_header("Watchlists", key="fresh-watchlists")
    if "watchlists" not in st.session_state:
        st.session_state["watchlists"] = seed_watchlists()
    lists = st.session_state["watchlists"]
    entries = [(name, e) for name in WATCHLIST_NAMES for e in lists.get(name, [])]
    if not entries:
        st.caption("No watchlist entries yet.")
        return

    signals = ctx.signal_repository.get_all_signals()
    for list_name, e in entries:
        against = is_moving_against_thesis(e.ticker_symbol, signals)
        row_html = (
            f'<div class="er-row" style="display:flex; justify-content:space-between; align-items:baseline;">'
            f'<span><a href="company?symbol={e.ticker_symbol}" class="er-mono" '
            f'style="color:var(--text); text-decoration:underline;">{e.ticker_symbol}</a> '
            f'<span class="er-muted">· {list_name}</span></span>'
            f'<span class="er-mono er-muted">Last — · 5-day —</span></div>'
        )
        st.markdown(row_html, unsafe_allow_html=True)
        if against and e.invalidates_if:
            st.markdown(
                f'<div class="er-muted" style="background:rgba(255,255,255,.025); border-radius:var(--r-sm); '
                f'padding:0.5rem 0.7rem; margin:-0.2rem 0 0.5rem 0; font-size:0.82rem;">'
                f'<strong style="color:var(--text);">Moving against thesis</strong> — you wrote: "{e.invalidates_if}"</div>',
                unsafe_allow_html=True,
            )


def _render_rotation_panel(ctx) -> None:
    panel_header("Capital rotation", key="fresh-rotation")
    themes = {t.slug: t for t in ctx.theme_repository.get_all_themes()}
    metrics = ctx.market_data_provider.get_rotation_metrics()
    ranked = rank_by_performance(metrics)
    if not ranked:
        st.caption("No rotation data loaded.")
        return
    max_abs = max(abs(m.relative_performance_pct) for m in ranked) or 1
    for m in ranked:
        if m.theme_slug not in themes:
            continue
        pct = m.relative_performance_pct
        half_width = min(abs(pct) / max_abs * 50, 50)
        side_style = f"left:50%; width:{half_width:.1f}%;" if pct >= 0 else f"right:50%; width:{half_width:.1f}%;"
        st.markdown(
            f"""
            <div class="er-divbar-row">
                <div class="er-divbar-label">{themes[m.theme_slug].name}</div>
                <div class="er-divbar-track">
                    <div class="er-divbar-zero"></div>
                    <div class="er-divbar-fill" style="{side_style}"></div>
                </div>
                <div class="er-divbar-value">{fmt_pct(pct)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    leaders, laggards = leaders_and_laggards(metrics, top_n=1)
    if leaders and laggards and leaders[0].theme_slug in themes and laggards[0].theme_slug in themes:
        st.markdown(
            f'<div class="er-muted" style="margin-top:0.5rem;">Leading: <strong>{themes[leaders[0].theme_slug].name}</strong> '
            f'· Lagging: <strong>{themes[laggards[0].theme_slug].name}</strong></div>',
            unsafe_allow_html=True,
        )
    themes_page = get_page("themes")
    if themes_page is not None:
        with st.container(key="cta-tertiary-dashboard-rotation"):
            st.page_link(themes_page, label="See rotation by theme →")


def render() -> None:
    ctx = get_repositories()

    st.markdown(
        f'<div class="er-hero-wrap" style="padding:1rem 0 0.5rem 0;">'
        f'<div class="er-hero-watermark" style="width:140px;height:140px;opacity:0.03;">{brand_mark_html()}</div>'
        '<div class="er-hero-content">',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="er-page-title">Dashboard</div>', unsafe_allow_html=True)
    freshness_chip("demo", key="fresh-dashboard-head")
    st.markdown("</div></div>", unsafe_allow_html=True)

    st.divider()
    _render_breadth_strip(ctx)

    st.divider()
    _render_new_signals(ctx)

    st.divider()
    _render_watchlist_table(ctx)

    st.divider()
    _render_rotation_panel(ctx)

    st.divider()
    panel_header("Next catalysts", key="fresh-catalysts")
    upcoming = ctx.catalyst_repository.get_upcoming_catalysts(limit=3)
    if not upcoming:
        st.caption("No catalysts scheduled.")
    else:
        for c in upcoming:
            catalyst_timeline_row(c)
