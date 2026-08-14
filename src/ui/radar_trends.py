"""Radar Trends — aggregated view over Radar's findings history.

Separate from the reverse-chronological feed on the Radar page: this page
only aggregates what's already been saved, it never fetches anything new
or makes an LLM call, and the same 24h freshness gate and guardrails
already applied when each finding was saved still apply to what's counted
here.
"""
from __future__ import annotations

import streamlit as st

from src.config.settings import Settings
from src.radar import analytics, store


def render(settings: Settings) -> None:
    st.caption(
        "Aggregated view over Radar's stored findings — which niches and tickers have been "
        "trending, not just a flat list. Nothing on this page triggers a scan."
    )

    findings = store.load_findings()
    if not findings:
        st.info("No Radar findings yet — nothing to chart. See the Radar page for setup steps.")
        return

    days = st.radio("Window", [7, 14, 30], index=0, horizontal=True, format_func=lambda d: f"Last {d} days")
    windowed = analytics.findings_within(findings, days)

    st.subheader("Findings per day")
    if windowed:
        st.bar_chart(analytics.mentions_per_day(windowed, days))
    else:
        st.caption("No findings in this window.")

    st.subheader("Findings per niche")
    niche_counts = analytics.mentions_per_niche(windowed)
    if niche_counts:
        st.bar_chart(niche_counts)
    else:
        st.caption("No findings in this window.")

    st.subheader("Most-mentioned tickers")
    top = analytics.top_tickers(windowed)
    if top:
        st.dataframe(
            [
                {
                    "Ticker": r["ticker"], "Company": r["company_name"], "Jurisdiction": r["jurisdiction"],
                    "Mentions": r["count"], "Last mention": r["last_mention"],
                }
                for r in top
            ],
            width="stretch", hide_index=True,
        )
    else:
        st.caption("No tickers tagged in this window.")

    st.caption(f"{len(windowed)} of {len(findings)} total stored findings fall within the selected window.")
