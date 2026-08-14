from __future__ import annotations

import json

import streamlit as st

from src.config.settings import Settings
from src.database.db import get_connection
from src.services import snapshot_service, ticker_service


def render(settings: Settings) -> None:
    with get_connection(settings) as conn:
        tickers = [t["ticker"] for t in ticker_service.list_tickers(conn)]
        if not tickers:
            st.info("No tickers yet.")
            return

        ticker = st.selectbox("Ticker", tickers)
        snapshots = conn.execute(
            "SELECT rs.id, rs.brief_id, rs.created_at, rb.version, rb.bottom_line "
            "FROM research_snapshots rs JOIN research_briefs rb ON rb.id = rs.brief_id "
            "WHERE rs.ticker = ? ORDER BY rb.version ASC",
            (ticker,),
        ).fetchall()

        if len(snapshots) < 2:
            st.info("Need at least two saved research briefs for this ticker to compare snapshots.")
            return

        options = {f"v{s['version']} — {s['bottom_line']} ({s['created_at'][:16]})": s for s in snapshots}
        col1, col2 = st.columns(2)
        with col1:
            older_label = st.selectbox("Earlier snapshot", list(options.keys()), index=len(options) - 2)
        with col2:
            newer_label = st.selectbox("Later snapshot", list(options.keys()), index=len(options) - 1)

        older = options[older_label]
        newer = options[newer_label]

        older_row = conn.execute("SELECT snapshot_json FROM research_snapshots WHERE id = ?", (older["id"],)).fetchone()
        newer_row = conn.execute("SELECT snapshot_json FROM research_snapshots WHERE id = ?", (newer["id"],)).fetchone()

        diff = snapshot_service.compare_snapshots(json.loads(older_row["snapshot_json"]), json.loads(newer_row["snapshot_json"]))

    st.subheader(f"What changed: {older_label} → {newer_label}")
    cols = st.columns(4)
    labels = [
        ("confirming", "Confirming evidence"), ("disconfirming", "Disconfirming evidence"),
        ("neutral", "Neutral updates"), ("new_unknowns", "New unknowns"),
    ]
    for col, (key, label) in zip(cols, labels):
        with col:
            st.markdown(f"**{label}**")
            items = diff.get(key, [])
            if not items:
                st.caption("None")
            for item in items:
                st.write(f"- {item}")

    with st.expander("Raw snapshot facts"):
        c1, c2 = st.columns(2)
        c1.json(json.loads(older_row["snapshot_json"]))
        c2.json(json.loads(newer_row["snapshot_json"]))
