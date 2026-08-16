"""The app's CSS design system — round 2: a near-black, white-typography,
editorial visual direction (X-profile inspired), replacing the earlier
cyan/violet system. Everything here is additive CSS on top of
.streamlit/config.toml; this file adds what the theme system doesn't
expose (the sidebar brand shell, absolute-positioned sidebar status, the
type scale, button/link styling via st-key-* targeting, card variants,
the hero signal-path motion, and the abstract Eeva mark).

Deliberately does NOT touch Streamlit's native toolbar/deploy/menu chrome
(stHeader/stToolbar/stAppDeployButton/stMainMenu).
"""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
:root {
    --er-bg: #050505;
    --er-surface: #0B0B0B;
    --er-surface-hover: #161616;
    --er-text: #F5F5F5;
    --er-text-muted: #71767B;
    --er-border: #2F3336;
    --er-border-strong: #4A4E52;
    --er-white: #FFFFFF;
    --er-accent: #C7D6E3;
    --er-positive: #5B9E7D;
    --er-negative: #C77B84;
    --er-caution: #C4A661;
    --er-font-display: "Space Grotesk", sans-serif;
    --er-font-body: "Inter", sans-serif;
    --er-font-mono: "JetBrains Mono", monospace;
}

/* ---------- layout ---------- */
.block-container {
    max-width: 1320px;
    padding-top: 1.5rem;
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
    color: var(--er-text-muted);
    margin-bottom: 0.5rem;
}
.er-hero-title {
    font-family: var(--er-font-display);
    font-weight: 700;
    font-size: clamp(2.4rem, 4.5vw, 3.6rem);
    line-height: 1.05;
    letter-spacing: -0.02em;
    color: var(--er-white);
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
    color: var(--er-white);
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
    color: var(--er-text);
}
.er-metric-label {
    font-family: var(--er-font-body);
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--er-text-muted);
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

/* ---------- direction rail + dots (muted market-state colors only) ---------- */
.er-rail-improving, .er-rail-emerging, .er-rail-weakening, .er-rail-mixed {
    border-left: 3px solid var(--er-text-muted);
    padding-left: 0.9rem;
}
.er-rail-improving { border-left-color: var(--er-positive); }
.er-rail-weakening { border-left-color: var(--er-negative); }
.er-rail-mixed { border-left-color: var(--er-caution); }
.er-rail-emerging { border-left-color: var(--er-accent); }

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
.er-dir-dot.er-dir-emerging { background: var(--er-accent); }

/* ---------- top navigation header ----------
   Round 3: replaces the sidebar entirely. st.navigation(position="hidden")
   suppresses Streamlit's own nav widget; everything below is fully custom,
   built from real st.page_link controls (see chrome.py render_top_nav). */
.er-topnav {
    display: flex;
    align-items: center;
    padding-bottom: 1rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid var(--er-border);
}
.er-topnav-brand {
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.er-logo-link {
    display: inline-flex;
    line-height: 0;
    border-radius: 4px;
    transition: filter 0.15s ease, transform 0.15s ease;
}
.er-logo-link:hover {
    filter: brightness(1.25) drop-shadow(0 0 6px rgba(199, 214, 227, 0.35));
    transform: scale(1.04);
}
.er-logo-link:focus-visible {
    outline: 2px solid var(--er-accent);
    outline-offset: 3px;
}
.er-logo-mark {
    display: inline-flex;
    width: 30px;
    height: 30px;
}
.er-logo-mark img, .er-logo-mark svg {
    width: 100%;
    height: 100%;
    object-fit: contain;
    color: var(--er-white);
}
.er-brand-word {
    font-family: var(--er-font-display);
    line-height: 1.1;
}
.er-brand-word .er-brand-primary {
    font-weight: 700;
    font-size: 1rem;
    color: var(--er-white);
    letter-spacing: 0.02em;
}
.er-brand-word .er-brand-secondary {
    display: block;
    font-family: var(--er-font-body);
    font-weight: 500;
    font-size: 0.6rem;
    letter-spacing: 0.14em;
    color: var(--er-text-muted);
    text-transform: uppercase;
}

/* Desktop tab row visible by default; mobile popover menu hidden by
   default. Swapped at the breakpoint below — both always render, CSS
   alone decides which is visible, so there's no viewport-detection JS. */
[class*="st-key-nav-desktop-row"] { display: block; }
[class*="st-key-nav-mobile-menu"] { display: none; }

[class*="st-key-navtab-"] {
    border-radius: 6px;
    text-align: center;
    transition: background-color 0.15s ease;
}
[class*="st-key-navtab-"] [data-testid="stPageLink"] a {
    justify-content: center;
    color: var(--er-text-muted) !important;
    border-radius: 6px;
    padding: 0.3rem 0.3rem !important;
    transition: color 0.15s ease, background-color 0.15s ease;
}
[class*="st-key-navtab-"] [data-testid="stPageLink"] a p {
    font-size: 0.74rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
[class*="st-key-navtab-"] [data-testid="stPageLink"] a:hover {
    color: var(--er-white) !important;
    background-color: var(--er-surface-hover);
}
[class*="st-key-navtab-"] [data-testid="stPageLink"] a:focus-visible {
    outline: 2px solid var(--er-accent) !important;
    outline-offset: 2px;
}

.er-topnav-status {
    text-align: right;
}
.er-topnav-status .er-status-line {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 0.4rem;
    font-family: var(--er-font-mono);
    font-size: 0.7rem;
    font-weight: 500;
    color: var(--er-caution);
}
.er-topnav-status .er-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--er-caution);
    display: inline-block;
}
.er-topnav-status .er-status-sub {
    font-family: var(--er-font-body);
    font-size: 0.65rem;
    color: var(--er-text-muted);
}

/* Eight labels (including "Capital Rotation", "Research Chat") need real
   room — below this, the compact popover menu takes over rather than
   cramming/wrapping tabs. This covers typical laptop widths too, not
   just phones; that's deliberate, matching "if all eight links cannot
   fit horizontally, use a stable compact menu." */
@media (max-width: 1400px) {
    [class*="st-key-nav-desktop-row"] { display: none; }
    [class*="st-key-nav-mobile-menu"] { display: block; }
    .er-topnav { flex-wrap: wrap; row-gap: 0.75rem; }
}

/* ---------- page-content entrance animation ----------
   Applies on every render of st.container(key="page-content") — including
   non-navigation reruns (a filter change, a chat submission), since
   Streamlit has no client-side-only "page just switched" signal to hook.
   Deliberately accepted per spec ("a consistent per-page entrance
   animation that runs safely on each render"). */
@media (prefers-reduced-motion: no-preference) {
    [class*="st-key-page-content"] {
        animation: er-page-enter 200ms ease-out;
    }
}
@keyframes er-page-enter {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}

/* ---------- CTA buttons ----------
   Targeted via a `key="cta-{tier}-...".format(...)` naming convention on
   the wrapping st.container/widget — Streamlit puts a `st-key-{key}`
   class on that element, and these rules match any key starting with the
   given prefix via a substring attribute selector. A plain <div> from
   st.markdown does NOT wrap subsequent st.* calls (siblings, not
   children) — confirmed not to work; the key-prefix selector is the one
   that does. */
[class*="st-key-cta-primary-"] [data-testid="stPageLink"] a,
[class*="st-key-cta-primary-"] [data-testid="stBaseButton-secondary"] {
    background: var(--er-white) !important;
    color: #050505 !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    transition: box-shadow 0.15s ease, transform 0.15s ease;
}
[class*="st-key-cta-primary-"] [data-testid="stPageLink"] a:hover,
[class*="st-key-cta-primary-"] [data-testid="stBaseButton-secondary"]:hover {
    box-shadow: 0 0 0 1px var(--er-white), 0 0 16px rgba(199, 214, 227, 0.25);
    transform: translateY(-1px);
}
[class*="st-key-cta-primary-"] [data-testid="stPageLink"] a span,
[class*="st-key-cta-primary-"] [data-testid="stPageLink"] a p { color: #050505 !important; }

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
    border-color: var(--er-white) !important;
    background: var(--er-surface-hover) !important;
}

[class*="st-key-cta-tertiary-"] [data-testid="stPageLink"] a {
    background: transparent !important;
    border: none !important;
    color: var(--er-text-muted) !important;
    padding-left: 0 !important;
    transition: color 0.15s ease;
}
[class*="st-key-cta-tertiary-"] [data-testid="stPageLink"] a:hover {
    color: var(--er-white) !important;
    text-decoration: underline;
}

/* focus-visible for keyboard users, everywhere */
[data-testid="stPageLink"] a:focus-visible,
[data-testid="stBaseButton-secondary"]:focus-visible,
[data-testid="stSidebarNavLink"]:focus-visible {
    outline: 2px solid var(--er-accent) !important;
    outline-offset: 2px;
}

/* ---------- card hover lift ----------
   Applies to every bordered st.container(border=True, key="card-...") —
   the border lives directly on the same element carrying the st-key-*
   class in this Streamlit version (confirmed against the running app;
   there is no separate "border wrapper" element). */
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
    color: var(--er-text);
}
.er-theme-icon svg { width: 100%; height: 100%; }

/* ---------- hero: signal-path motion + Eeva watermark ---------- */
.er-hero-wrap {
    position: relative;
    padding: 2.5rem 0 2rem 0;
    overflow: hidden;
}
.er-hero-signal-svg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    z-index: 0;
    pointer-events: none;
}
.er-signal-path {
    fill: none;
    stroke: rgba(245, 245, 245, 0.08);
    stroke-width: 1;
    stroke-dasharray: 6 10;
}
.er-signal-path-2 { stroke: rgba(199, 214, 227, 0.07); }
.er-signal-node { fill: rgba(245, 245, 245, 0.5); }
@media (prefers-reduced-motion: no-preference) {
    .er-signal-path { animation: er-flow 16s linear infinite; }
    .er-signal-path-2 { animation: er-flow 22s linear infinite reverse; }
    .er-signal-node { animation: er-drift 42s ease-in-out infinite; }
    .er-signal-node-2 { animation: er-drift 56s ease-in-out infinite reverse; animation-delay: -12s; }
    .er-signal-node-3 { animation: er-drift 48s ease-in-out infinite; animation-delay: -24s; }
    .er-hero-watermark { animation: er-breathe 12s ease-in-out infinite; }
}
@keyframes er-flow { to { stroke-dashoffset: -160; } }
@keyframes er-drift {
    0%, 100% { transform: translate(0, 0); opacity: 0.35; }
    50% { transform: translate(16px, -9px); opacity: 0.7; }
}
@keyframes er-breathe {
    0%, 100% { opacity: 0.03; }
    50% { opacity: 0.055; }
}
.er-hero-watermark {
    position: absolute;
    top: 50%;
    right: -4%;
    transform: translateY(-50%);
    width: 340px;
    height: 340px;
    color: var(--er-white);
    opacity: 0.04;
    z-index: 0;
    pointer-events: none;
}
.er-hero-watermark svg, .er-hero-watermark img { width: 100%; height: 100%; object-fit: contain; }
.er-hero-content { position: relative; z-index: 1; }
</style>
"""


def inject_global_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
