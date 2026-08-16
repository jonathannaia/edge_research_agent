"""Empty states (brief §14) — a title, one line of guidance, and a primary
action. Never an apology, never a bare `st.info` (that's a blue accent box,
which the zero-accent-colour rule rules out anyway)."""
from __future__ import annotations

import streamlit as st


def empty_state(
    title: str,
    detail: str | None = None,
    action_label: str | None = None,
    action_page=None,
    action_query_params: dict | None = None,
    on_click=None,
    key: str | None = None,
) -> None:
    with st.container(border=True, key=f"card-empty-{key}" if key else None):
        st.markdown(f'<div class="er-card-title">{title}</div>', unsafe_allow_html=True)
        if detail:
            st.markdown(f'<div class="er-muted" style="margin-top:0.2rem;">{detail}</div>', unsafe_allow_html=True)
        if action_label and action_page is not None:
            with st.container(key=f"cta-secondary-empty-{key or action_label}"):
                st.page_link(action_page, label=action_label, query_params=action_query_params or {})
        elif action_label and on_click is not None:
            with st.container(key=f"cta-secondary-empty-{key or action_label}"):
                st.button(action_label, key=f"empty-action-{key or action_label}", on_click=on_click)
