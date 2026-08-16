"""The app's CSS design system — "institutional intelligence with restrained
future-tech." Everything here is additive CSS on top of .streamlit/config.toml
(which sets the base palette/fonts for Streamlit's own native widgets); this
file adds what the theme system doesn't expose: the sidebar-as-branded-shell
treatment, the type scale, button/link styling for st.page_link and st.button
(targeted via real DOM testids and st-key-* classes confirmed against the
running app, not guessed), card variants, direction-color utilities, and the
hero ambient background.

Deliberately does NOT touch Streamlit's native toolbar/deploy/menu chrome
(stHeader/stToolbar/stAppDeployButton/stMainMenu) — left completely alone
per explicit instruction to avoid brittle CSS against elements Streamlit
itself may change across versions.
"""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
:root {
    --er-bg: #070B14;
    --er-surface: #0D1424;
    --er-surface-hover: #121D31;
    --er-text: #F8FAFC;
    --er-text-muted: #94A3B8;
    --er-border: rgba(148, 163, 184, 0.16);
    --er-border-strong: rgba(148, 163, 184, 0.32);
    --er-cyan: #38BDF8;
    --er-violet: #A78BFA;
    --er-positive: #34D399;
    --er-negative: #FB7185;
    --er-caution: #FBBF24;
    --er-font-display: "Space Grotesk", sans-serif;
    --er-font-body: "Inter", sans-serif;
    --er-font-mono: "JetBrains Mono", monospace;
}

/* ---------- layout ---------- */
.block-container {
    max-width: 980px;
    padding-top: 1rem;
    padding-bottom: 3rem;
}
h1, h2, h3 { font-family: var(--er-font-display); letter-spacing: -0.01em; }

/* ---------- type scale ---------- */
.er-eyebrow {
    font-family: var(--er-font-body);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--er-cyan);
    margin-bottom: 0.5rem;
}
.er-hero-title {
    font-family: var(--er-font-display);
    font-weight: 700;
    font-size: clamp(2.4rem, 4.5vw, 3.6rem);
    line-height: 1.05;
    letter-spacing: -0.02em;
    color: var(--er-text);
    margin: 0 0 0.75rem 0;
}
.er-hero-sub {
    font-family: var(--er-font-body);
    font-size: 1.05rem;
    line-height: 1.6;
    color: var(--er-text-muted);
    max-width: 640px;
    margin-bottom: 0.5rem;
}
.er-page-title {
    font-family: var(--er-font-display);
    font-weight: 700;
    font-size: clamp(1.75rem, 3vw, 2.1rem);
    color: var(--er-text);
    margin: 0 0 0.4rem 0;
}
.er-card-title {
    font-family: var(--er-font-body);
    font-weight: 600;
    font-size: 1.05rem;
    color: var(--er-text);
}
.er-muted {
    color: var(--er-text-muted);
    font-size: 0.85rem;
}
.er-mono {
    font-family: var(--er-font-mono);
    font-variant-numeric: tabular-nums;
}
.er-metric-value {
    font-family: var(--er-font-mono);
    font-weight: 500;
    font-size: 1.1rem;
}
.er-metric-label {
    font-family: var(--er-font-body);
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--er-text-muted);
}

/* ---------- status banner (sticky, compact pill) ---------- */
.er-status-row {
    /* Streamlit's own header is position:fixed at top:0, height 60px,
       z-index 999990 (confirmed via computed styles). `position: sticky`
       only affects behavior once scrolled — at rest this row sits at its
       natural in-flow position, which without the margin below overlaps
       the fixed header. margin-top clears that; top:60px is where it
       sticks once scrolled past. */
    position: sticky;
    top: 60px;
    z-index: 998;
    display: flex;
    justify-content: flex-end;
    padding: 0.5rem 0;
    margin-top: 2.5rem;
    background: var(--er-bg);
    margin-bottom: 0.5rem;
}
.er-status-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-family: var(--er-font-mono);
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.04em;
    color: var(--er-caution);
    background: rgba(251, 191, 36, 0.08);
    border: 1px solid rgba(251, 191, 36, 0.28);
    border-radius: 999px;
    padding: 0.3rem 0.75rem;
}
.er-status-pill .er-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--er-caution);
    display: inline-block;
}
.er-status-meta {
    font-family: var(--er-font-mono);
    font-size: 0.7rem;
    color: var(--er-text-muted);
    margin-left: 0.6rem;
}

/* ---------- footer ---------- */
.er-footer {
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--er-border);
    color: var(--er-text-muted);
    font-size: 0.78rem;
    line-height: 1.6;
}
.er-footer .er-footer-version {
    font-family: var(--er-font-mono);
    margin-top: 0.6rem;
}

/* ---------- rows (catalyst timeline etc.) ---------- */
.er-row {
    padding: 0.55rem 0;
    border-bottom: 1px solid var(--er-border);
}
.er-row:last-child { border-bottom: none; }

/* ---------- direction rail + dots ---------- */
.er-rail-improving, .er-rail-emerging, .er-rail-weakening, .er-rail-mixed {
    border-left: 3px solid var(--er-text-muted);
    padding-left: 0.9rem;
}
.er-rail-improving { border-left-color: var(--er-positive); }
.er-rail-weakening { border-left-color: var(--er-negative); }
.er-rail-mixed { border-left-color: var(--er-caution); }
.er-rail-emerging { border-left-color: var(--er-violet); }

.er-dir-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    margin-right: 0.4rem;
    vertical-align: middle;
}
.er-dir-dot.er-dir-improving { background: var(--er-positive); }
.er-dir-dot.er-dir-weakening { background: var(--er-negative); }
.er-dir-dot.er-dir-mixed { background: var(--er-caution); }
.er-dir-dot.er-dir-emerging { background: var(--er-violet); }

/* ---------- sidebar brand shell ---------- */
[data-testid="stSidebar"] {
    background: var(--er-surface);
    border-right: 1px solid var(--er-border);
}
/* st.navigation's nav block is always inserted before any custom
   `with st.sidebar:` content in the DOM, regardless of call order in the
   script (a fixed Streamlit layout, confirmed empirically) — reordered
   visually via flex order so the brand header reads above the nav. */
[data-testid="stSidebarContent"] {
    display: flex;
    flex-direction: column;
}
[data-testid="stSidebarHeader"] { order: 0; }
[data-testid="stSidebarUserContent"] { order: 1; }
[data-testid="stSidebarNav"] { order: 2; }
.er-brand {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.25rem 0 1rem 0;
}
.er-brand-mark {
    width: 26px;
    height: 26px;
    flex-shrink: 0;
    position: relative;
}
.er-brand-mark span {
    position: absolute;
    border-radius: 50%;
    border: 1.5px solid var(--er-cyan);
}
.er-brand-mark span:nth-child(1) { inset: 0; opacity: 0.9; }
.er-brand-mark span:nth-child(2) { inset: 7px; border-color: var(--er-violet); opacity: 0.85; }
.er-brand-mark span:nth-child(3) {
    inset: 11px; background: var(--er-cyan); border: none;
}
.er-brand-word {
    font-family: var(--er-font-display);
    line-height: 1.1;
}
.er-brand-word .er-brand-primary {
    font-weight: 700;
    font-size: 1.05rem;
    color: var(--er-text);
    letter-spacing: 0.01em;
}
.er-brand-word .er-brand-secondary {
    display: block;
    font-family: var(--er-font-body);
    font-weight: 500;
    font-size: 0.62rem;
    letter-spacing: 0.16em;
    color: var(--er-text-muted);
    text-transform: uppercase;
}

/* ---------- sidebar nav active state ---------- */
[data-testid="stSidebarNavLink"] {
    border-radius: 6px !important;
    transition: background-color 0.15s ease, color 0.15s ease;
}
[data-testid="stSidebarNavLink"]:hover {
    background-color: var(--er-surface-hover) !important;
}
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background-color: rgba(56, 189, 248, 0.10) !important;
    box-shadow: inset 2px 0 0 var(--er-cyan);
}
[data-testid="stSidebarNavLink"][aria-current="page"] p {
    color: var(--er-cyan) !important;
    font-weight: 600 !important;
}

.er-sidebar-status {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--er-border);
}

/* ---------- CTA buttons ----------
   Targeted via a `key="cta-primary-...".format(...)` naming convention on
   the wrapping st.container/widget — Streamlit puts a `st-key-{key}` class
   on that element (confirmed against the running app), and these rules
   match any key starting with the given prefix via a substring attribute
   selector, so every CTA using the convention is styled without needing
   a distinct rule per instance. A plain <div> from st.markdown does NOT
   wrap subsequent st.* calls (they render as siblings, not children) —
   that approach was tried and confirmed not to work; the key-prefix
   selector below is the one that does. */
[class*="st-key-cta-primary-"] [data-testid="stPageLink"] a,
[class*="st-key-cta-primary-"] [data-testid="stBaseButton-secondary"] {
    background: var(--er-cyan) !important;
    color: #04121C !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    transition: box-shadow 0.15s ease, transform 0.15s ease;
}
[class*="st-key-cta-primary-"] [data-testid="stPageLink"] a:hover,
[class*="st-key-cta-primary-"] [data-testid="stBaseButton-secondary"]:hover {
    box-shadow: 0 0 0 1px var(--er-cyan), 0 0 18px rgba(56, 189, 248, 0.35);
    transform: translateY(-1px);
}
[class*="st-key-cta-primary-"] [data-testid="stPageLink"] a span,
[class*="st-key-cta-primary-"] [data-testid="stPageLink"] a p { color: #04121C !important; }

[class*="st-key-cta-secondary-"] [data-testid="stPageLink"] a,
[class*="st-key-cta-secondary-"] [data-testid="stBaseButton-secondary"] {
    background: transparent !important;
    border: 1px solid var(--er-border-strong) !important;
    border-radius: 6px !important;
    color: var(--er-text) !important;
    transition: border-color 0.15s ease, background-color 0.15s ease;
}
[class*="st-key-cta-secondary-"] [data-testid="stPageLink"] a:hover,
[class*="st-key-cta-secondary-"] [data-testid="stBaseButton-secondary"]:hover {
    border-color: var(--er-cyan) !important;
    background: var(--er-surface-hover) !important;
}

[class*="st-key-cta-tertiary-"] [data-testid="stPageLink"] a {
    background: transparent !important;
    border: none !important;
    color: var(--er-text-muted) !important;
    padding-left: 0 !important;
}
[class*="st-key-cta-tertiary-"] [data-testid="stPageLink"] a:hover {
    color: var(--er-cyan) !important;
}

/* focus-visible for keyboard users, everywhere */
[data-testid="stPageLink"] a:focus-visible,
[data-testid="stBaseButton-secondary"]:focus-visible,
[data-testid="stSidebarNavLink"]:focus-visible {
    outline: 2px solid var(--er-cyan) !important;
    outline-offset: 2px;
}

/* ---------- card hover lift ----------
   Applies to every bordered st.container(border=True, key="card-...")
   in the app — a shared "card-" key prefix convention (see cards.py,
   market_brief.py) lets one static rule cover all of them via a substring
   class-attribute selector, since Streamlit puts the border directly on
   the same element that carries the st-key-* class (confirmed against
   the running app — there is no separate "border wrapper" element in
   this Streamlit version). */
[class*="st-key-card-"] {
    transition: border-color 0.15s ease, transform 0.15s ease;
}
[class*="st-key-card-"]:hover {
    border-color: var(--er-border-strong) !important;
    transform: translateY(-2px);
}

/* ---------- theme icon motifs ---------- */
.er-theme-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    margin-bottom: 0.5rem;
    color: var(--er-cyan);
}
.er-theme-icon svg { width: 100%; height: 100%; }

/* ---------- hero ambient background ---------- */
.er-hero-wrap {
    position: relative;
    padding: 2.5rem 0 2rem 0;
    overflow: hidden;
}
.er-hero-bg {
    position: absolute;
    inset: -20% -10% -10% -10%;
    z-index: 0;
    pointer-events: none;
    background:
        radial-gradient(480px circle at 15% 20%, rgba(56, 189, 248, 0.16), transparent 60%),
        radial-gradient(420px circle at 85% 10%, rgba(167, 139, 250, 0.14), transparent 60%),
        radial-gradient(circle, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
    background-size: auto, auto, 26px 26px;
}
@media (prefers-reduced-motion: no-preference) {
    .er-hero-bg { animation: er-hero-drift 50s ease-in-out infinite alternate; }
}
@keyframes er-hero-drift {
    from { background-position: 0 0, 0 0, 0 0; }
    to { background-position: 20px 10px, -15px -10px, 0 0; }
}
.er-hero-content { position: relative; z-index: 1; }
</style>
"""


def inject_global_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
