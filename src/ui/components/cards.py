"""Card-style components, built on Streamlit's native bordered container
(st.container(border=True, key="card-...")) rather than custom HTML — keeps
borders/spacing consistent with the theme and gives every card the shared
hover-lift rule in theme.py (which targets the `st-key-card-*` prefix).
Direction rails use a small per-instance <style> block injected right
before the container, since the rail color varies per signal and Streamlit
containers don't accept an arbitrary CSS class directly — only a `key`,
which becomes a `st-key-{key}` class (confirmed against the running app).
"""
from __future__ import annotations

import streamlit as st

from src.logic.evidence import source_label
from src.logic.formatting import fmt_date, fmt_pct
from src.models.models import CapitalRotationMetric, Catalyst, EvidenceItem, Signal, Theme
from src.ui.components.badges import demo_badge, direction_dot_html, freshness_badge
from src.ui.components.evidence_chips import evidence_chip
from src.ui.components.excerpts import render_excerpt

_THEME_ICONS: dict[str, str] = {
    "ai-buildout": (
        '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.4">'
        '<rect x="3" y="3" width="14" height="4" rx="1"/><rect x="3" y="8" width="14" height="4" rx="1"/>'
        '<rect x="3" y="13" width="14" height="4" rx="1"/>'
        '<circle cx="6" cy="5" r="0.6" fill="currentColor" stroke="none"/>'
        '<circle cx="6" cy="10" r="0.6" fill="currentColor" stroke="none"/>'
        '<circle cx="6" cy="15" r="0.6" fill="currentColor" stroke="none"/></svg>'
    ),
    "humanoids": (
        '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.4">'
        '<circle cx="10" cy="4.5" r="2.3"/><line x1="10" y1="6.8" x2="10" y2="12"/>'
        '<line x1="10" y1="9" x2="5" y2="13.5"/><line x1="10" y1="9" x2="15" y2="13.5"/>'
        '<line x1="10" y1="12" x2="6.5" y2="17.5"/><line x1="10" y1="12" x2="13.5" y2="17.5"/>'
        '<circle cx="10" cy="9" r="0.7" fill="currentColor" stroke="none"/></svg>'
    ),
    "space": (
        '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.4">'
        '<ellipse cx="10" cy="10" rx="8" ry="3.2" transform="rotate(-20 10 10)"/>'
        '<circle cx="10" cy="10" r="1.5" fill="currentColor" stroke="none"/>'
        '<circle cx="16" cy="6.6" r="1" fill="currentColor" stroke="none"/></svg>'
    ),
    "memory": (
        '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.4">'
        '<rect x="5" y="5" width="10" height="10" rx="1"/>'
        '<line x1="7" y1="2" x2="7" y2="5"/><line x1="10" y1="2" x2="10" y2="5"/><line x1="13" y1="2" x2="13" y2="5"/>'
        '<line x1="7" y1="15" x2="7" y2="18"/><line x1="10" y1="15" x2="10" y2="18"/><line x1="13" y1="15" x2="13" y2="18"/>'
        '<line x1="2" y1="7" x2="5" y2="7"/><line x1="2" y1="10" x2="5" y2="10"/><line x1="2" y1="13" x2="5" y2="13"/>'
        '<line x1="15" y1="7" x2="18" y2="7"/><line x1="15" y1="10" x2="18" y2="10"/><line x1="15" y1="13" x2="18" y2="13"/></svg>'
    ),
    "photonics": (
        '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.4">'
        '<path d="M2 10 Q5 4 8 10 T14 10 T20 10" stroke-linecap="round"/>'
        '<circle cx="2" cy="10" r="1" fill="currentColor" stroke="none"/></svg>'
    ),
}

def theme_icon_html(theme_slug: str) -> str:
    icon = _THEME_ICONS.get(theme_slug, "")
    return f'<div class="er-theme-icon">{icon}</div>'


def metric_pair_html(label1: str, value1: str, label2: str, value2: str) -> str:
    return (
        '<div style="display:flex; gap:1.5rem; margin: 0.4rem 0 0.8rem 0;">'
        f'<div><div class="er-metric-label">{label1}</div><div class="er-metric-value">{value1}</div></div>'
        f'<div><div class="er-metric-label">{label2}</div><div class="er-metric-value">{value2}</div></div>'
        "</div>"
    )


def metric_tile(label: str, value: str, help_text: str | None = None) -> None:
    st.metric(label, value, help=help_text)


def theme_card(theme: Theme, metric: CapitalRotationMetric | None, page=None) -> None:
    with st.container(border=True, key=f"card-theme-{theme.slug}"):
        icon = _THEME_ICONS.get(theme.slug, "")
        st.markdown(f'<div class="er-theme-icon">{icon}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="er-card-title">{theme.name}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="er-muted">{theme.description}</div>', unsafe_allow_html=True)
        if metric:
            dot = direction_dot_html(_infer_direction(metric.relative_performance_pct))
            st.markdown(
                f"""
                <div style="display:flex; gap:1.5rem; margin-top:0.6rem;">
                    <div><div class="er-metric-label">Rel. perf.</div>
                    <div class="er-metric-value">{fmt_pct(metric.relative_performance_pct)}</div></div>
                    <div><div class="er-metric-label">Breadth</div>
                    <div class="er-metric-value">{metric.breadth_pct:.0f}%</div></div>
                </div>
                <div class="er-muted" style="margin-top:0.4rem;">{dot}</div>
                """,
                unsafe_allow_html=True,
            )
        if page is not None:
            with st.container(key=f"cta-tertiary-theme-{theme.slug}"):
                st.page_link(page, label=f"Explore {theme.name} →")


def _infer_direction(relative_performance_pct: float):
    from src.models.models import Direction

    if relative_performance_pct > 2:
        return Direction.IMPROVING
    if relative_performance_pct < -2:
        return Direction.WEAKENING
    return Direction.MIXED


def signal_card(signal: Signal, theme_page=None, evidence_repository=None, unread: bool = False) -> None:
    key = f"card-signal-{signal.id}"
    with st.container(border=True, key=key):
        top = st.columns([3, 1])
        with top[0]:
            dot = '<span class="er-unread-dot"></span>' if unread else ""
            st.markdown(f'<div class="er-card-title">{dot}{signal.title}</div>', unsafe_allow_html=True)
            tag_line = signal.theme_slug + (f" / {signal.subtheme_slug}" if signal.subtheme_slug else "")
            st.markdown(f'<div class="er-muted">{tag_line}</div>', unsafe_allow_html=True)
        with top[1]:
            demo_badge()

        st.markdown(
            f"""
            <div style="display:flex; gap:1.5rem; margin: 0.5rem 0;">
                <div><div class="er-metric-label">Direction</div><div class="er-muted">{direction_dot_html(signal.direction)}</div></div>
                <div><div class="er-metric-label">Strength</div><div class="er-mono">{signal.strength.value}</div></div>
                <div><div class="er-metric-label">Horizon</div><div class="er-mono">{signal.horizon.value}</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="max-height:4.2em; overflow:hidden;">{signal.interpretation}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="er-muted" style="margin-top:0.4rem;">{signal.evidence_count} demo evidence item(s) '
            f'· updated {fmt_date(signal.last_updated)}</div>',
            unsafe_allow_html=True,
        )
        if signal.related_tickers:
            # Every ticker mention links to its Company page (acceptance
            # checklist: "every ticker in the app links to one").
            links = ", ".join(
                f'<a href="company?symbol={t}" style="color:var(--text-2); text-decoration:underline;">{t}</a>'
                for t in signal.related_tickers
            )
            st.markdown(f'<div class="er-muted">Related: {links}</div>', unsafe_allow_html=True)

        action_cols = st.columns([1, 1, 2])
        with action_cols[0]:
            with st.container(key=f"cta-secondary-{signal.id}"):
                if st.button("View details", key=f"open-drawer-{signal.id}", width="stretch"):
                    from src.ui.components.signal_drawer import open_signal_drawer

                    open_signal_drawer(signal, evidence_repository=evidence_repository)
        if theme_page is not None:
            with action_cols[1]:
                with st.container(key=f"cta-tertiary-{signal.id}"):
                    st.page_link(theme_page, label="Open theme →")


def compact_signal_row(signal: Signal) -> None:
    """A slimmer signal presentation for Overview's top-3 — direction,
    strength, horizon, and a one-line interpretation only. No expander, no
    evidence-count/related-tickers/CTA — that detail lives on the full
    signal_card, which is Signal Board's job now, not Overview's."""
    key = f"card-compact-signal-{signal.id}"
    with st.container(border=True, key=key):
        st.markdown(f'<div class="er-card-title" style="font-size:0.95rem;">{signal.title}</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="er-muted" style="margin: 0.2rem 0;">
                {direction_dot_html(signal.direction)} · <span class="er-mono">{signal.strength.value}</span>
                · <span class="er-mono">{signal.horizon.value}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="er-muted" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{signal.interpretation}</div>',
            unsafe_allow_html=True,
        )


def catalyst_timeline_row(catalyst: Catalyst) -> None:
    st.markdown(
        f"""
        <div class="er-row" style="display:flex; align-items:baseline; gap:0.9rem;">
            <span class="er-mono" style="background:var(--er-surface-hover); border:1px solid var(--er-border);
                  border-radius:4px; padding:0.15rem 0.5rem; font-size:0.75rem; white-space:nowrap;">
                {fmt_date(catalyst.date)}
            </span>
            <span>{catalyst.title}</span>
            <span class="er-muted" style="margin-left:auto; white-space:nowrap;">{catalyst.catalyst_type}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Backwards-compatible alias — catalyst_row was the pre-redesign name.
catalyst_row = catalyst_timeline_row


def evidence_row(evidence: EvidenceItem) -> None:
    with st.container(border=True, key=f"card-evidence-{evidence.id}"):
        top = st.columns([3, 1, 1])
        top[0].markdown(f'<div class="er-card-title">{evidence.title}</div>', unsafe_allow_html=True)
        with top[1]:
            evidence_chip(evidence.claim_type, has_source=bool(evidence.source_name))
        with top[2]:
            freshness_badge(evidence)
        render_excerpt(evidence)
        st.markdown(
            f'<div class="er-muted" style="margin-top:0.3rem;">{source_label(evidence)}</div>',
            unsafe_allow_html=True,
        )
