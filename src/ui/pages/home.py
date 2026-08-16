"""Home — the welcome/introduction page. Separate from Overview (the
market workspace): Home explains what EevaResearch is and how to use it
for a first-time visitor; it deliberately does not carry any dashboard
content. No financial claims, no live metrics — every number that could
appear here is intentionally absent.
"""
from __future__ import annotations

import streamlit as st

from src.data_access.container import get_repositories
from src.ui.chrome import brand_mark_html, get_page
from src.ui.components.cards import theme_icon_html
from src.ui.components.section import section_header

_FEATURES = [
    ("Track themes", "Follow the five thematic supply chains and their market structure."),
    ("Read capital rotation", "See where leadership, breadth, and attention are shifting."),
    ("Ask research questions", "Use Research Chat to explore companies, themes, catalysts, and market reads."),
]

_STEPS = [
    "Start with the market read",
    "Explore a theme or signal",
    "Ask a research question",
]


def render() -> None:
    ctx = get_repositories()
    themes = ctx.theme_repository.get_all_themes()

    st.markdown(
        f'<div class="er-hero-wrap"><div class="er-hero-watermark">{brand_mark_html()}</div>'
        '<svg class="er-hero-signal-svg" viewBox="0 0 800 260" preserveAspectRatio="none">'
        '<path class="er-signal-path" d="M-50,190 C150,150 250,230 450,170 S650,90 850,130"/>'
        '<path class="er-signal-path er-signal-path-2" d="M-50,70 C200,120 350,30 550,90 S750,150 850,100"/>'
        '<circle class="er-signal-node" cx="120" cy="170" r="2.5"/>'
        '<circle class="er-signal-node er-signal-node-2" cx="420" cy="90" r="2"/>'
        '<circle class="er-signal-node er-signal-node-3" cx="620" cy="120" r="2.5"/>'
        '</svg><div class="er-hero-content">',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="er-eyebrow">EevaResearch · Market Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="er-hero-title">Find the signals behind the AI buildout.</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="er-hero-sub">EevaResearch helps you track the infrastructure, bottlenecks, catalysts, '
        'and capital rotation shaping AI Buildout, Humanoids, Space, Memory, and Photonics.</div>',
        unsafe_allow_html=True,
    )

    cta_cols = st.columns([1, 1, 1])
    with cta_cols[0]:
        page = get_page("overview")
        if page is not None:
            with st.container(key="cta-primary-home-overview"):
                st.page_link(page, label="Enter market overview", width="stretch")
    with cta_cols[1]:
        page = get_page("themes")
        if page is not None:
            with st.container(key="cta-secondary-home-themes"):
                st.page_link(page, label="Explore themes", width="stretch")
    with cta_cols[2]:
        page = get_page("methodology")
        if page is not None:
            with st.container(key="cta-tertiary-home-methodology"):
                st.page_link(page, label="How EevaResearch works →")
    st.markdown("</div></div>", unsafe_allow_html=True)

    st.divider()
    section_header("What the tool does")
    feature_cols = st.columns(3)
    for col, (title, desc) in zip(feature_cols, _FEATURES):
        with col:
            with st.container(border=True, key=f"card-feature-{title.replace(' ', '-').lower()}"):
                st.markdown(f'<div class="er-card-title">{title}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="er-muted">{desc}</div>', unsafe_allow_html=True)

    st.divider()
    section_header("Five research themes")
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
    section_header("How to use it")
    step_cols = st.columns(3)
    for col, (i, step) in zip(step_cols, enumerate(_STEPS, start=1)):
        with col:
            st.markdown(f'<div class="er-metric-label">Step {i}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="er-card-title" style="font-size:0.95rem;">{step}</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown(
        '<div class="er-muted">EevaResearch separates source-backed facts, market interpretation, model '
        'inference, and uncertainty. Demo mode is active — no live market data is connected.</div>',
        unsafe_allow_html=True,
    )
