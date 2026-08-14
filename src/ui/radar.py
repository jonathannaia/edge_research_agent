"""Radar — the autonomous, guardrail-constrained news scanner.

Deliberately separate from the manual Watchlist/Research workflow: this page
only *displays* what the scheduled GitHub Actions job has already found and
saved to data/radar_findings.json (see src/radar/). Nothing on this page
triggers a scan or costs money to view — the LLM calls all happen offline,
on a schedule, in CI.
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from src.config.settings import Settings
from src.radar import store
from src.radar.models import Niche

RADAR_DISCLAIMER = (
    "**Radar runs autonomously** — findings below are surfaced and summarized by an AI model on a "
    "schedule, with **no human review before they appear here**. Every item links back to its original "
    "source; read the source before acting on anything. Like the rest of EevaResearch AI, Radar never "
    "says buy/sell/hold and never gives a price target — findings are cited factual summaries only, "
    "not investment advice."
)


def _hours_ago(iso_ts: str) -> str:
    try:
        ts = datetime.fromisoformat(iso_ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - ts
    except (ValueError, TypeError):
        return iso_ts
    hours = delta.total_seconds() / 3600
    if hours < 1:
        return "less than an hour ago"
    if hours < 48:
        return f"{int(hours)}h ago"
    return f"{int(hours / 24)}d ago"


def render(settings: Settings) -> None:
    st.caption(
        "Fully autonomous, strictly scoped to four niches: AI Buildout, Humanoids, Space, and "
        "Macro/Rates/Policy. Separate from your manual Watchlist and Research Briefs — nothing here "
        "affects those, and nothing there affects this. Every finding must be published within the "
        "last 24 hours (`EDGE_RADAR_MAX_AGE_HOURS`) — anything older, or with no parseable publish "
        "date, is dropped before it ever reaches the AI model."
    )
    st.warning(RADAR_DISCLAIMER)

    findings = store.load_findings()
    run_history = store.load_run_history()

    if not findings:
        st.info(
            "No Radar findings yet. The scheduled scan (`.github/workflows/radar_scan.yml`, every 2 "
            "hours) hasn't run or hasn't found anything in-scope yet. See App Settings or the README "
            "for how to turn it on — it needs an `ANTHROPIC_API_KEY` GitHub Actions secret."
        )
        if run_history:
            with st.expander(f"Scan run history ({len(run_history)} runs, most recent first)"):
                _render_run_history(run_history)
        return

    last_run = run_history[0] if run_history else None
    if last_run:
        st.caption(
            f"Last scan: {_hours_ago(last_run.finished_at)} · "
            f"{last_run.items_saved} new finding(s) saved · status: {last_run.status}"
        )

    niches = [n.value for n in Niche]
    all_tickers = sorted({t.ticker for f in findings for t in f.tickers})

    c1, c2 = st.columns(2)
    with c1:
        niche_filter = st.multiselect("Niche", niches)
    with c2:
        ticker_filter = st.multiselect("Ticker", all_tickers)

    rows = findings
    if niche_filter:
        rows = [f for f in rows if f.niche in niche_filter]
    if ticker_filter:
        rows = [f for f in rows if any(t.ticker in ticker_filter for t in f.tickers)]

    st.write(f"{len(rows)} of {len(findings)} findings shown.")

    for f in rows:
        ticker_str = ", ".join(f"{t.ticker} ({t.jurisdiction})" for t in f.tickers) if f.tickers else "No ticker identified"
        with st.container(border=True):
            st.markdown(f"**{f.headline}**")
            st.caption(f"{f.niche} · {f.source_name} · {_hours_ago(f.retrieved_at)}")
            st.write(f.summary)
            st.write(f"**Tickers:** {ticker_str}")
            st.write(f"[Read source]({f.source_url})")
            if f.relevance_reason:
                st.caption(f"Why flagged: {f.relevance_reason}")

    if run_history:
        st.divider()
        with st.expander(f"Scan run history ({len(run_history)} runs, most recent first)"):
            _render_run_history(run_history)


def _render_run_history(run_history) -> None:
    st.dataframe(
        [
            {
                "Finished": r.finished_at,
                "Status": r.status,
                "Feeds": r.feeds_checked,
                "Items seen": r.items_seen,
                "Within 24h": r.items_after_freshness_filter,
                "Sent to LLM": r.items_sent_to_llm,
                "Saved": r.items_saved,
                "Guardrail-rejected": r.items_rejected_by_guardrail,
                "Errors": len(r.errors),
            }
            for r in run_history[:30]
        ],
        width="stretch", hide_index=True,
    )
