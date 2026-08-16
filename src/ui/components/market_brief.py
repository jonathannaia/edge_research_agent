"""The editorial opening experience on Overview — a compact bento-style
summary synthesized from the same demo repositories every other page reads
from. Redesigned from the original five stacked full-paragraph cards into
four short panels (title + 1-2 lines + deep link) per the UI redesign brief.

Every synthesized read here is an Interpretation, never a Fact — these are
readings across multiple demo data points, not a single sourced statement.
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from src.data_access.container import AppContext
from src.logic.formatting import fmt_date, fmt_pct
from src.logic.theme_metrics import leaders_and_laggards, strongest_signals
from src.models.models import ClaimType
from src.ui.chrome import get_page
from src.ui.components.badges import claim_type_badge, demo_badge


def _panel_header(title: str, claim_type: ClaimType = ClaimType.INTERPRETATION) -> None:
    top = st.columns([4, 1])
    top[0].markdown(f'<div class="er-card-title">{title}</div>', unsafe_allow_html=True)
    with top[1]:
        claim_type_badge(claim_type)


def render_market_brief(ctx: AppContext) -> None:
    themes = {t.slug: t for t in ctx.theme_repository.get_all_themes()}
    metrics = ctx.market_data_provider.get_rotation_metrics()
    signals = ctx.signal_repository.get_all_signals()
    upcoming = ctx.catalyst_repository.get_upcoming_catalysts(limit=3)
    leaders, laggards = leaders_and_laggards(metrics, top_n=2)
    top_signals = strongest_signals(signals, limit=2)

    header_cols = st.columns([3, 1])
    with header_cols[0]:
        st.markdown('<div class="er-page-title" style="font-size:1.4rem;">Market Brief</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="er-muted er-mono">As of {datetime.now(timezone.utc).strftime("%b %-d, %Y, %H:%M UTC")}</div>',
            unsafe_allow_html=True,
        )
    with header_cols[1]:
        demo_badge("Demo / mock-data mode")

    row1 = st.columns([2, 1])
    with row1[0]:
        with st.container(border=True, key="card-brief-rotation"):
            _panel_header("Capital rotation read")
            if leaders and laggards:
                lead_names = ", ".join(themes[m.theme_slug].name for m in leaders if m.theme_slug in themes)
                lag_names = ", ".join(themes[m.theme_slug].name for m in laggards if m.theme_slug in themes)
                st.write(f"**{lead_names}** lead this demo snapshot; **{lag_names}** show the weakest reads.")
                st.markdown(
                    f'<div class="er-muted">A sustained gap is one input into where research attention may be '
                    f"concentrating — on its own it isn't conclusive.</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Not enough theme data yet.")
            page = get_page("capital_rotation")
            if page is not None:
                with st.container(key="cta-tertiary-brief-rotation"):
                    st.page_link(page, label="Open Capital Rotation →")

    with row1[1]:
        with st.container(border=True, key="card-brief-attention"):
            _panel_header("Research attention")
            if top_signals:
                for s in top_signals:
                    st.markdown(f"**{s.title}**")
                    st.markdown(
                        f'<div class="er-muted">{s.direction.value}, {s.strength.value.lower()}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No signals yet.")
            page = get_page("signal_board")
            if page is not None:
                with st.container(key="cta-tertiary-brief-attention"):
                    st.page_link(page, label="Open Signal Board →")

    row2 = st.columns([1, 1])
    with row2[0]:
        with st.container(border=True, key="card-brief-catalysts"):
            _panel_header("Approaching catalysts")
            if upcoming:
                for c in upcoming:
                    st.markdown(
                        f'<div class="er-row"><span class="er-mono">{fmt_date(c.date)}</span> — {c.title}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No catalysts scheduled.")
            page = get_page("themes")
            if page is not None:
                with st.container(key="cta-tertiary-brief-catalysts"):
                    st.page_link(page, label="View full calendar in Themes →")

    with row2[1]:
        with st.container(border=True, key="card-brief-invalidate"):
            _panel_header("What would change this read", ClaimType.UNCERTAINTY)
            st.markdown(
                '<div class="er-muted">This is a fixed demo snapshot — nothing updates it in this phase. '
                "Phase 2 evidence ingestion would state the specific new data that changes the read above.</div>",
                unsafe_allow_html=True,
            )
            page = get_page("methodology")
            if page is not None:
                with st.container(key="cta-tertiary-brief-invalidate"):
                    st.page_link(page, label="Read Methodology →")
