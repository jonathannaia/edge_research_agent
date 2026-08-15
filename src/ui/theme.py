"""A thin CSS layer on top of .streamlit/config.toml — kept deliberately
small. The theme file already sets the dark palette, accent color, and
fonts; this only adds layout/spacing rules Streamlit's theme system doesn't
expose (max content width, consistent vertical rhythm, muted-text utility
class) so the app reads as a research website rather than a wide dashboard.
"""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
.block-container {
    max-width: 900px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}
h1, h2, h3 { letter-spacing: -0.01em; }
.er-muted {
    color: #9A9A9A;
    font-size: 0.85rem;
}
.er-status-banner {
    border: 1px solid #2A2A2A;
    border-radius: 6px;
    padding: 0.5rem 0.9rem;
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
}
.er-footer {
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid #2A2A2A;
    color: #9A9A9A;
    font-size: 0.8rem;
    line-height: 1.5;
}
.er-row {
    padding: 0.5rem 0;
    border-bottom: 1px solid #1E1E1E;
}
.er-row:last-child { border-bottom: none; }
</style>
"""


def inject_global_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
