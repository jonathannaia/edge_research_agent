from __future__ import annotations

import streamlit as st

from src.config.settings import Settings
from src.database.db import get_connection
from src.scoring.defaults import DEFAULT_COMPONENTS, DEFAULT_WEIGHTS
from src.services import settings_service


def render(settings: Settings) -> None:
    st.write(
        "Weights determine how much each component contributes to the total conviction score. "
        "They are normalized to sum to 1.0 automatically, however you set the sliders below. "
        "**The score is a research aid, not investment advice or a prediction.**"
    )

    with get_connection(settings) as conn:
        current_weights = settings_service.get_score_weights(conn)

        new_weights = {}
        for c in DEFAULT_COMPONENTS:
            key = c["key"]
            new_weights[key] = st.slider(
                c["label"], min_value=0.0, max_value=0.30, step=0.01,
                value=float(current_weights.get(key, c["weight"])), help=c["description"],
            )

        total_raw = sum(new_weights.values()) or 1.0
        st.caption(f"Raw weight sum: {total_raw:.2f} → normalized to 1.00 when saved/used.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save weights", type="primary"):
                settings_service.set_score_weights(conn, new_weights)
                st.success("Weights saved. New research briefs will use these weights.")
        with col2:
            if st.button("Reset to defaults"):
                settings_service.set_score_weights(conn, DEFAULT_WEIGHTS.copy())
                st.success("Reset to defaults.")
                st.rerun()

    st.divider()
    st.subheader("Score cap & warning rules")
    st.write(
        "- If **Evidence quality & freshness** scores ≤2/5, the total conviction score is capped at 2.5/5 "
        "and confidence is forced to Low, regardless of other components.\n"
        "- If **Cash flow / balance sheet** or **Risk level / thesis fragility** score ≤2/5, a prominent "
        "risk warning is generated and shown in the brief and on the watchlist."
    )
