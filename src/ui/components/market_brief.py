"""The editorial opening experience on Overview — a short, narrative brief
synthesized from the same demo repositories every other page reads from
(not separately hardcoded prose), so it stays consistent with the rest of
the app and exercises the full data_access -> logic -> UI path end to end.

Every synthesized read here is an Interpretation or Inference, never a
Fact — these are readings across multiple demo data points, not a single
sourced statement, so they're labeled accordingly.
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from src.data_access.container import AppContext
from src.logic.formatting import fmt_date, fmt_pct
from src.logic.theme_metrics import leaders_and_laggards, strongest_signals
from src.models.models import ClaimType
from src.ui.components.badges import claim_type_badge, demo_badge


def _get_page(name: str):
    return st.session_state.get("_pages", {}).get(name)


def render_market_brief(ctx: AppContext) -> None:
    themes = {t.slug: t for t in ctx.theme_repository.get_all_themes()}
    metrics = ctx.market_data_provider.get_rotation_metrics()
    signals = ctx.signal_repository.get_all_signals()
    upcoming = ctx.catalyst_repository.get_upcoming_catalysts(limit=3)
    leaders, laggards = leaders_and_laggards(metrics, top_n=2)
    top_signals = strongest_signals(signals, limit=2)

    header_cols = st.columns([3, 1])
    with header_cols[0]:
        st.markdown("### Market Brief")
        st.markdown(f'<div class="er-muted">As of {datetime.now(timezone.utc).strftime("%b %-d, %Y, %H:%M UTC")}</div>', unsafe_allow_html=True)
    with header_cols[1]:
        demo_badge("Demo / mock-data mode")

    blocks: list[tuple[str, str]] = []

    if leaders:
        leader_names = ", ".join(themes[m.theme_slug].name for m in leaders if m.theme_slug in themes)
        blocks.append((
            "Where capital is rotating",
            f"Across the five tracked themes, {leader_names} show the strongest relative performance "
            f"reads this period ({', '.join(fmt_pct(m.relative_performance_pct) for m in leaders)}). "
            "This is a synthesized read across demo metrics, not a single sourced fact.",
        ))
    if laggards:
        laggard_names = ", ".join(themes[m.theme_slug].name for m in laggards if m.theme_slug in themes)
        blocks.append((
            "Which themes are weakening",
            f"{laggard_names} show the weakest relative performance reads this period "
            f"({', '.join(fmt_pct(m.relative_performance_pct) for m in laggards)}).",
        ))
    if top_signals:
        sig_titles = "; ".join(f"{s.title} ({s.direction.value.lower()}, {s.strength.value.lower()})" for s in top_signals)
        blocks.append((
            "What deserves research attention",
            f"The strongest current signals: {sig_titles}. See Signal Board for full validation/invalidation criteria.",
        ))
    if upcoming:
        cat_list = "; ".join(f"{c.title} ({fmt_date(c.date)})" for c in upcoming)
        blocks.append((
            "Catalysts approaching",
            f"Nearest tracked catalysts: {cat_list}.",
        ))
    blocks.append((
        "What changed today / this week",
        "Phase 1 has no live data connection, so nothing in this brief reflects real intraday or "
        "weekly change — every figure above is static demo data included to exercise this layout.",
    ))

    for title, body in blocks[:5]:
        with st.container(border=True):
            top = st.columns([4, 1])
            top[0].markdown(f"**{title}**")
            with top[1]:
                claim_type_badge(ClaimType.INTERPRETATION)
            st.write(body)

    with st.container(border=True):
        st.markdown("**What would change this read**")
        st.write(
            "This brief is a fixed demo snapshot, not a live model — nothing will change it in this "
            "phase. Once real evidence ingestion exists (Phase 2), this section will state the specific "
            "new data (a filing, a rating action, a catalyst outcome) that would update the read above."
        )

    st.markdown("&nbsp;", unsafe_allow_html=True)
    link_cols = st.columns(4)
    link_targets = [
        ("Capital Rotation", "capital_rotation"),
        ("Signal Board", "signal_board"),
        ("Themes", "themes"),
        ("Research Chat", "research_chat"),
    ]
    for col, (label, key) in zip(link_cols, link_targets):
        page = _get_page(key)
        with col:
            if page is not None:
                st.page_link(page, label=f"{label} →", width="stretch")
