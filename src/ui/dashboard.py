from __future__ import annotations

from datetime import date

import streamlit as st

from src.config.settings import Settings
from src.database.db import get_connection
from src.services import alert_service, audit_service, watchlist_service
from src.ui.components import evidence_badge, navigate_to, tier_badge


def _render_getting_started() -> None:
    st.write(
        "This is a personal research organizer for tracking potential business inflections in "
        "companies you're watching. Here's the workflow, start to finish:"
    )
    st.markdown(
        "1. **Add a ticker to your watchlist** — set its tier (Active Research / Watch Closely / "
        "Avoid), a short inflection thesis, and what would confirm or invalidate it.\n"
        "2. **Generate a research brief** — pick the ticker and a research question; the app pulls "
        "evidence, cites every claim to a source, and scores it. Nothing here is investment advice "
        "or a buy/sell call — only cited evidence and an evidence-based bull/bear/mixed read.\n"
        "3. **Review on Ticker Detail** — see the full thesis record, every brief version, and a "
        "change log of what shifted between reviews and why.\n"
        "4. **Set up alerts** — the Alerts page flags upcoming catalysts, new filings, and score "
        "moves. It only runs when you click the button; nothing happens in the background."
    )
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Add your first ticker", type="primary"):
            navigate_to("Watchlist")
    with col2:
        st.caption(
            "Prefer to see it populated first? App Settings has a one-click 'Load demo tickers' "
            "button with three example companies and mock data."
        )


def render(settings: Settings) -> None:
    with get_connection(settings) as conn:
        watchlist = watchlist_service.list_watchlist(conn)

        if not watchlist:
            _render_getting_started()
            return

        open_alerts = alert_service.list_alerts(conn, status="open")
        recent_events = audit_service.list_recent_events(conn, limit=8)

    tier_counts = {"Active Research": 0, "Watch Closely": 0, "Avoid / Broken Thesis": 0}
    upcoming_catalysts = []
    for w in watchlist:
        tier_counts[w["tier"]] = tier_counts.get(w["tier"], 0) + 1
        if w["next_catalyst_date"]:
            try:
                days_out = (date.fromisoformat(w["next_catalyst_date"]) - date.today()).days
                if 0 <= days_out <= 30:
                    upcoming_catalysts.append((w["ticker"], w["next_catalyst"], w["next_catalyst_date"], days_out))
            except ValueError:
                pass

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Watchlist size", len(watchlist))
    c2.metric("Active Research", tier_counts.get("Active Research", 0))
    c3.metric("Watch Closely", tier_counts.get("Watch Closely", 0))
    c4.metric("Avoid / Broken", tier_counts.get("Avoid / Broken Thesis", 0))
    c5.metric("Open alerts", len(open_alerts))

    st.divider()

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Watchlist overview")
        st.dataframe(
            [
                {
                    "Ticker": w["ticker"], "Company": w["company_name"], "Tier": tier_badge(w["tier"]),
                    "Score": w["conviction_score"], "Evidence": evidence_badge(w["evidence_status"]),
                    "Next Catalyst": f"{w['next_catalyst'] or '—'} ({w['next_catalyst_date'] or '—'})",
                    "Risk Flags": w["risk_flags"] or "—",
                }
                for w in watchlist
            ],
            width='stretch', hide_index=True,
        )

    with col_right:
        st.subheader("Catalysts within 30 days")
        if not upcoming_catalysts:
            st.caption("None.")
        for ticker, desc, cdate, days_out in sorted(upcoming_catalysts, key=lambda x: x[3]):
            st.write(f"**{ticker}** — {desc} in {days_out}d ({cdate})")

        st.subheader("Recent activity")
        for e in recent_events:
            st.caption(f"`{e['created_at']}` [{e['ticker'] or '—'}] {e['event_type']}")
