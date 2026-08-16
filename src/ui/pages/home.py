"""Home — first-visit-only landing page (brief §8). No sidebar (see
app.py: show_sidebar=False); single 900px column with a minimal top bar
instead. No dashboard content, no financial claims, no live metrics.

Copy direction per the brief: plain and specific, no aspirational or
ceremonial language. The "What the tool does" marketing copy that used to
live here moved to About when the doc pages split — nothing was deleted.
"""
from __future__ import annotations

import streamlit as st

from src.data_access.container import get_repositories
from src.models.models import ClaimType
from src.ui.components.cards import theme_icon_html
from src.ui.components.evidence_chips import evidence_chip
from src.ui.components.section import section_header
from src.ui.ui import brand_mark_html, get_page

_STEPS = [
    "Start with the Dashboard for today's market read",
    "Open a theme to see its value chain, signals, and catalysts",
    "Check Signals for what's changed recently",
    "Ask Research a question and get an evidence-labeled answer",
    "Save a name to a watchlist with what would invalidate it",
    "Read Methodology for the framework behind every label",
]

_CHIP_DEFINITIONS = [
    (ClaimType.FACT, "Stated in a source document, and attributed to it."),
    (ClaimType.INTERPRETATION, "A market read built on facts shown alongside it."),
    (ClaimType.INFERENCE, "Follows logically from the evidence but isn't confirmed anywhere."),
    (ClaimType.UNCERTAINTY, "A named open question, recorded rather than smoothed over."),
]

# Exact content per brief §8.
_LIMITS = [
    "It does not give financial advice.",
    "The conversational agent can be wrong.",
    "It does not replace the primary source.",
    "The data may be delayed or incomplete.",
]


def render() -> None:
    ctx = get_repositories()
    themes = ctx.theme_repository.get_all_themes()

    st.markdown('<div class="er-home-column">', unsafe_allow_html=True)

    st.markdown(
        f'<div class="er-home-topbar"><span class="er-rail-logo">{brand_mark_html()}</span>'
        '<span style="font-weight:700; font-size:0.9rem;">EevaResearch</span></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="er-hero-wrap" style="padding:0 0 1rem 0;">', unsafe_allow_html=True)
    st.markdown('<div class="er-eyebrow">EevaResearch · Market Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="er-hero-title">Start with what was filed.</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="er-hero-sub">EevaResearch tracks the companies, supply chains, catalysts, and capital '
        "rotation behind five technology themes, and labels every claim by how well it's backed — Fact, "
        "Interpretation, Inference, or Uncertainty.</div>",
        unsafe_allow_html=True,
    )

    cta_cols = st.columns([1, 1, 2])
    with cta_cols[0]:
        page = get_page("dashboard")
        if page is not None:
            with st.container(key="cta-primary-home-dashboard"):
                st.page_link(page, label="Open Dashboard", width="stretch")
    with cta_cols[1]:
        st.markdown(
            '<div style="padding-top:0.5rem;"><a href="#what-this-tool-wont-do" '
            'style="color:var(--text-3); text-decoration:none; font-size:0.85rem;">What this tool won\'t do</a></div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    section_header("How to use it")
    step_cols_row1 = st.columns(3)
    for col, (i, step) in zip(step_cols_row1, enumerate(_STEPS[:3], start=1)):
        with col:
            st.markdown(f'<div class="er-metric-label">Step {i}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="er-card-title" style="font-size:0.9rem;">{step}</div>', unsafe_allow_html=True)
    step_cols_row2 = st.columns(3)
    for col, (i, step) in zip(step_cols_row2, enumerate(_STEPS[3:], start=4)):
        with col:
            st.markdown(f'<div class="er-metric-label">Step {i}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="er-card-title" style="font-size:0.9rem;">{step}</div>', unsafe_allow_html=True)

    st.divider()
    section_header("Every claim carries a label")
    chip_cols = st.columns(4)
    for col, (claim_type, description) in zip(chip_cols, _CHIP_DEFINITIONS):
        with col:
            evidence_chip(claim_type)
            st.markdown(f'<div class="er-muted" style="margin-top:0.4rem;">{description}</div>', unsafe_allow_html=True)

    st.divider()
    section_header("Five themes")
    themes_page = get_page("themes")
    theme_cols = st.columns(min(len(themes), 5) or 1)
    for col, theme in zip(theme_cols, themes):
        with col:
            with st.container(border=True, key=f"card-home-theme-{theme.slug}"):
                st.markdown(theme_icon_html(theme.slug), unsafe_allow_html=True)
                st.markdown(f'<div class="er-card-title" style="font-size:0.95rem;">{theme.name}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="er-muted" style="font-size:0.8rem;">{theme.description}</div>', unsafe_allow_html=True)
                if themes_page is not None:
                    with st.container(key=f"cta-tertiary-home-theme-{theme.slug}"):
                        st.page_link(themes_page, label="Explore →")

    st.divider()
    st.markdown('<div id="what-this-tool-wont-do"></div>', unsafe_allow_html=True)
    section_header("What this tool does not do")
    limit_cols = st.columns(4)
    for col, limit in zip(limit_cols, _LIMITS):
        with col:
            st.markdown(f'<div class="er-muted">{limit}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="er-muted" style="margin-top:1rem;">If that\'s the arrangement you want, the Dashboard '
        "is where the work starts.</div>",
        unsafe_allow_html=True,
    )
    page = get_page("dashboard")
    if page is not None:
        with st.container(key="cta-primary-home-closer"):
            st.page_link(page, label="Open Dashboard", width="stretch")

    st.markdown("</div>", unsafe_allow_html=True)
