"""Card-style components, built on Streamlit's native bordered container
(st.container(border=True)) rather than custom HTML — keeps borders/spacing
consistent with the rest of the theme and avoids a second styling system.
Used sparingly per page, per the "not dashboard-like" design direction.
"""
from __future__ import annotations

import streamlit as st

from src.logic.evidence import source_label
from src.logic.formatting import fmt_date, fmt_pct
from src.models.models import CapitalRotationMetric, Catalyst, EvidenceItem, Signal, Theme
from src.ui.components.badges import claim_type_badge, demo_badge, direction_badge, freshness_badge, strength_badge


def metric_tile(label: str, value: str, help_text: str | None = None) -> None:
    st.metric(label, value, help=help_text)


def theme_card(theme: Theme, metric: CapitalRotationMetric | None, page=None) -> None:
    with st.container(border=True):
        st.markdown(f"**{theme.name}**")
        st.markdown(f'<div class="er-muted">{theme.description}</div>', unsafe_allow_html=True)
        if metric:
            cols = st.columns(2)
            cols[0].metric("Relative performance", fmt_pct(metric.relative_performance_pct), help="Demo data — placeholder benchmark comparison")
            cols[1].metric("Breadth", f"{metric.breadth_pct:.0f}%", help="Demo data — placeholder breadth measure")
        if page is not None:
            st.page_link(page, label=f"Explore {theme.name} →")


def signal_card(signal: Signal) -> None:
    with st.container(border=True):
        top = st.columns([3, 1])
        top[0].markdown(f"**{signal.title}**")
        with top[1]:
            demo_badge()
        badge_cols = st.columns(3)
        with badge_cols[0]:
            direction_badge(signal.direction)
        with badge_cols[1]:
            strength_badge(signal.strength)
        with badge_cols[2]:
            st.badge(signal.horizon.value, color="gray")
        st.markdown(f'<div class="er-muted">{signal.theme_slug}{" / " + signal.subtheme_slug if signal.subtheme_slug else ""} · {signal.evidence_count} evidence item(s) · updated {fmt_date(signal.last_updated)}</div>', unsafe_allow_html=True)
        st.markdown(f"**Interpretation:** {signal.interpretation}")
        st.markdown(f"**Contrary evidence:** {signal.contrary_evidence}")
        with st.expander("Validation / invalidation criteria"):
            st.markdown(f"**Would validate:** {signal.validation_criteria}")
            st.markdown(f"**Would invalidate:** {signal.invalidation_criteria}")
        if signal.related_tickers:
            st.markdown(f'<div class="er-muted">Related: {", ".join(signal.related_tickers)}</div>', unsafe_allow_html=True)


def catalyst_row(catalyst: Catalyst) -> None:
    st.markdown(
        f'<div class="er-row"><strong>{fmt_date(catalyst.date)}</strong> — {catalyst.title} '
        f'<span class="er-muted">({catalyst.catalyst_type})</span></div>',
        unsafe_allow_html=True,
    )


def evidence_row(evidence: EvidenceItem) -> None:
    with st.container(border=True):
        top = st.columns([3, 1, 1])
        top[0].markdown(f"**{evidence.title}**")
        with top[1]:
            claim_type_badge(evidence.claim_type)
        with top[2]:
            freshness_badge(evidence)
        st.write(evidence.excerpt)
        st.markdown(
            f'<div class="er-muted">{source_label(evidence)} · retrieved {fmt_date(evidence.retrieved_at)}</div>',
            unsafe_allow_html=True,
        )
