from __future__ import annotations

import json

import streamlit as st

from src.config.settings import Settings
from src.database.db import get_connection
from src.services import settings_service

TABLES_TO_EXPORT = [
    "tickers", "watchlist_records", "theses", "sources", "source_excerpts",
    "research_briefs", "research_snapshots", "scorecards", "score_components",
    "catalysts", "alerts", "notes", "audit_logs",
]


def render(settings: Settings) -> None:
    st.subheader("Freshness thresholds")
    st.write("Used to flag how stale evidence is throughout the app. Changes apply to newly generated briefs and alert checks.")

    defaults = {
        "fresh": settings.freshness_fresh_days,
        "aging": settings.freshness_aging_days,
        "stale": settings.freshness_stale_days,
    }
    with get_connection(settings) as conn:
        thresholds = settings_service.get_freshness_thresholds(conn, defaults)

        col1, col2, col3 = st.columns(3)
        with col1:
            fresh = st.number_input("Fresh ≤ (days)", min_value=1, value=int(thresholds["fresh"]))
        with col2:
            aging = st.number_input("Aging ≤ (days)", min_value=1, value=int(thresholds["aging"]))
        with col3:
            stale = st.number_input("Stale ≤ (days, beyond = very stale)", min_value=1, value=int(thresholds["stale"]))

        if st.button("Save freshness thresholds"):
            if fresh < aging < stale:
                settings_service.set_freshness_thresholds(conn, {"fresh": fresh, "aging": aging, "stale": stale})
                st.success("Saved. Note: applies at read-time in this UI; restart the app to fully reload env-based defaults.")
            else:
                st.error("Thresholds must satisfy fresh < aging < stale.")

        st.divider()
        st.subheader("App info")
        st.write(f"**{settings.app_name}** v{settings.app_version}")
        st.write(f"Database path: `{settings.db_path}`")
        st.write(f"Data mode: `{settings.data_mode}`")

        st.divider()
        st.subheader("Export local data backup")
        st.caption("Exports every table as JSON — your full research history, for backup or migration. Stays local.")
        if st.button("Prepare backup export"):
            backup = {}
            for table in TABLES_TO_EXPORT:
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                backup[table] = [dict(r) for r in rows]
            payload = json.dumps(backup, indent=2, default=str)
            st.download_button("Download backup JSON", payload, file_name="edge_research_agent_backup.json")

    st.divider()
    st.subheader("Disclaimer")
    st.warning(
        "Edge Research Agent is a personal research organizer. It does not execute trades, move money, "
        "or provide personalized investment advice. All investment decisions are yours alone."
    )
