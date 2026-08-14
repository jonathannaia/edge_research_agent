from __future__ import annotations

from collections import defaultdict
from datetime import date

import streamlit as st

from src.config.settings import Settings
from src.database.db import get_connection
from src.models.models import JURISDICTION_REGULATOR
from src.services import source_service, ticker_service
from src.utils.formatting import freshness_badge

REGULATORY_TYPES = {"Regulatory Filing", "Insider/Ownership Filing"}


def render(settings: Settings) -> None:
    with get_connection(settings) as conn:
        sources = source_service.list_all_sources(conn)
        if not sources:
            st.info("No sources ingested yet. Generate a research brief to populate this page.")
            return

        ticker_rows = {t["ticker"]: t for t in ticker_service.list_tickers(conn)}

        st.subheader("Coverage by jurisdiction")
        st.caption(
            "Which regulator each ticker's filings come from, and how many regulatory filings "
            "(10-K/10-Q/8-K equivalents, insider disclosures) have been pulled for it so far."
        )
        by_jurisdiction: dict[str, dict] = defaultdict(lambda: {"tickers": set(), "filings": 0})
        for s in sources:
            t = ticker_rows.get(s["ticker"])
            jurisdiction = t["jurisdiction"] if t else "Unknown"
            by_jurisdiction[jurisdiction]["tickers"].add(s["ticker"])
            if s["source_type"] in REGULATORY_TYPES:
                by_jurisdiction[jurisdiction]["filings"] += 1

        st.dataframe(
            [
                {
                    "Jurisdiction": j,
                    "Regulator": JURISDICTION_REGULATOR.get(j, "Unknown"),
                    "Tickers covered": ", ".join(sorted(v["tickers"])),
                    "Regulatory filings pulled": v["filings"],
                }
                for j, v in sorted(by_jurisdiction.items())
            ],
            width="stretch", hide_index=True,
        )
        st.caption(
            "All filings above are mock data in V1 regardless of jurisdiction — see Data Provider "
            "Settings for what it takes to wire up a live regulator for each market."
        )

        st.subheader("Coverage by source type")
        st.caption("Everything else feeding a research brief: earnings materials, ownership data, market data, and news.")
        by_type: dict[str, dict] = defaultdict(lambda: {"count": 0, "tickers": set()})
        for s in sources:
            by_type[s["source_type"]]["count"] += 1
            by_type[s["source_type"]]["tickers"].add(s["ticker"])

        st.dataframe(
            [
                {
                    "Source type": t,
                    "Count": v["count"],
                    "Tickers covered": ", ".join(sorted(v["tickers"])),
                }
                for t, v in sorted(by_type.items(), key=lambda kv: -kv[1]["count"])
            ],
            width="stretch", hide_index=True,
        )

        st.divider()
        with st.expander(f"All {len(sources)} individual sources (detailed, filterable, for audit)"):
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
