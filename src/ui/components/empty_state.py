from __future__ import annotations

import streamlit as st


def empty_state(message: str, detail: str | None = None) -> None:
    st.info(message)
    if detail:
        st.markdown(f'<div class="er-muted">{detail}</div>', unsafe_allow_html=True)
