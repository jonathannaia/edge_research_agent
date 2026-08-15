from __future__ import annotations

import streamlit as st


def section_header(title: str, subtitle: str | None = None) -> None:
    st.subheader(title)
    if subtitle:
        st.markdown(f'<div class="er-muted">{subtitle}</div>', unsafe_allow_html=True)
