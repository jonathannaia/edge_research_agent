"""Watchlists — four demo lists. Add/remove works within a session
(st.session_state only) so the UI feels functional; nothing here persists
across a reload. Watchlists are deliberately not behind the repository
interfaces used elsewhere — they're user-generated session state, not
sourced market data.
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from src.config.settings import get_settings
from src.data_access import loaders
from src.data_access.container import get_repositories
from src.logic.formatting import fmt_date
from src.models.models import WatchlistEntry
from src.ui.components.empty_state import empty_state

SESSION_KEY = "watchlists"
WATCHLIST_NAMES = ["Core Themes", "High-Conviction Research", "Earnings/Catalysts", "Emerging Names"]


def _seed_watchlists() -> dict[str, list[WatchlistEntry]]:
    raw = loaders.load(get_settings(), "watchlists.json", default={})
    return {
        name: [
            WatchlistEntry(list_name=name, ticker_symbol=e["ticker_symbol"], added_at=e["added_at"], note=e.get("note", ""))
            for e in raw.get(name, [])
        ]
        for name in WATCHLIST_NAMES
    }


def render() -> None:
    ctx = get_repositories()
    if SESSION_KEY not in st.session_state:
        st.session_state[SESSION_KEY] = _seed_watchlists()
    lists: dict[str, list[WatchlistEntry]] = st.session_state[SESSION_KEY]

    st.markdown("# Watchlists")
    st.write(
        "Demo watchlists, seeded from mock data. Adding or removing a ticker updates this session "
        "only — reloading the page resets to the seeded lists. Built so real, persisted watchlists "
        "can be added later without a UI rewrite."
    )

    all_symbols = [t.symbol for t in ctx.ticker_repository.get_all_tickers()]

    tabs = st.tabs(WATCHLIST_NAMES)
    for tab, name in zip(tabs, WATCHLIST_NAMES):
        with tab:
            entries = lists[name]
            if not entries:
                empty_state("This watchlist is empty.")
            else:
                rows = [{"Ticker": e.ticker_symbol, "Added": fmt_date(e.added_at), "Note": e.note} for e in entries]
                st.dataframe(rows, hide_index=True, width="stretch")

            available_to_add = [s for s in all_symbols if s not in {e.ticker_symbol for e in entries}]
            add_cols = st.columns([3, 1])
            with add_cols[0]:
                to_add = st.selectbox("Add ticker", ["—"] + available_to_add, key=f"add-select-{name}")
            with add_cols[1]:
                st.markdown("&nbsp;")
                if st.button("Add", key=f"add-btn-{name}", width="stretch") and to_add != "—":
                    entries.append(
                        WatchlistEntry(
                            list_name=name, ticker_symbol=to_add,
                            added_at=datetime.now(timezone.utc).isoformat(),
                            note="Added this session — not persisted.",
                        )
                    )

            if entries:
                remove_cols = st.columns([3, 1])
                with remove_cols[0]:
                    to_remove = st.selectbox("Remove ticker", ["—"] + [e.ticker_symbol for e in entries], key=f"remove-select-{name}")
                with remove_cols[1]:
                    st.markdown("&nbsp;")
                    if st.button("Remove", key=f"remove-btn-{name}", width="stretch") and to_remove != "—":
                        lists[name] = [e for e in entries if e.ticker_symbol != to_remove]
