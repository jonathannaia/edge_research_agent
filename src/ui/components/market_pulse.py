"""The compact five-theme strip shown directly under the Overview hero —
name, mono relative-performance, mono breadth, and a small direction dot
per theme, laid out horizontally so all five scan at a glance. Same demo
data as everywhere else (CapitalRotationMetric), no separate numbers."""
from __future__ import annotations

import streamlit as st

from src.data_access.container import AppContext
from src.logic.formatting import fmt_pct
from src.models.models import Direction
from src.ui.components.badges import direction_dot_html


def _infer_direction(pct: float) -> Direction:
    if pct > 2:
        return Direction.IMPROVING
    if pct < -2:
        return Direction.WEAKENING
    return Direction.MIXED


def render_market_pulse(ctx: AppContext) -> None:
    themes = {t.slug: t.name for t in ctx.theme_repository.get_all_themes()}
    metrics = {m.theme_slug: m for m in ctx.market_data_provider.get_rotation_metrics()}

    cols = st.columns(len(themes) or 1)
    for col, (slug, name) in zip(cols, themes.items()):
        metric = metrics.get(slug)
        with col:
            with st.container(border=True, key=f"card-pulse-{slug}"):
                st.markdown(f'<div class="er-metric-label">{name}</div>', unsafe_allow_html=True)
                if metric:
                    st.markdown(
                        f'<div class="er-metric-value">{fmt_pct(metric.relative_performance_pct)}</div>'
                        f'<div class="er-muted er-mono">{metric.breadth_pct:.0f}% breadth</div>'
                        f'<div class="er-muted" style="margin-top:0.3rem;">{direction_dot_html(_infer_direction(metric.relative_performance_pct))}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown('<div class="er-muted">No data</div>', unsafe_allow_html=True)
