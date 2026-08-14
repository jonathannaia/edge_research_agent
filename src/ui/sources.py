from __future__ import annotations

from datetime import date

import streamlit as st

from src.config.settings import Settings
from src.database.db import get_connection
from src.services import source_service
from src.utils.formatting import freshness_badge


def render(settings: Settings) -> None:
    with get_connection(settings) as conn:
        sources = source_service.list_all_sources(conn)
        if not sources:
            st.info("No sources ingested yet. Generate a research brief to populate this page.")
            return

        tickers = sorted({s["ticker"] for s in sources})
        types = sorted({s["source_type"] for s in sources})

        c1, c2, c3 = st.columns(3)
        with c1:
            ticker_filter = st.multiselect("Ticker", tickers)
        with c2:
            type_filter = st.multiselect("Source type", types)
        with c3:
            freshness_filter = st.multiselect("Freshness", ["fresh", "aging", "stale", "very_stale"])

        rows = []
        for s in sources:
            age = (date.today() - date.fromisoformat(s["source_date"])).days
            status = settings.freshness_status(age)
            if ticker_filter and s["ticker"] not in ticker_filter:
                continue
            if type_filter and s["source_type"] not in type_filter:
                continue
            if freshness_filter and status not in freshness_filter:
                continue
            rows.append((s, status, age))

        st.write(f"{len(rows)} of {len(sources)} sources shown.")
        for s, status, age in rows:
            with st.expander(f"#{s['id']} · {s['ticker']} · {s['source_type']} · {s['title']} · {freshness_badge(status)}"):
                st.write(f"**Source date:** {s['source_date']} ({age} days ago)")
                st.write(f"**Retrieved:** {s['retrieval_date']}")
                st.write(f"**Authority rank:** {s['authority_rank']} (1 = highest authority)")
                st.write(f"**Identifier / URL:** {s['url_or_identifier']}")
                excerpts = source_service.list_excerpts_for_source(conn, s["id"])
                if excerpts:
                    st.markdown("**Excerpts:**")
                    for e in excerpts:
                        st.write(f"- _{e['tag']}_: {e['excerpt_text']}")
