"""Ticker table wrapper — a thin layer over st.dataframe (which already
gives column sorting/resizing natively) plus an empty-state fallback, so
every theme page renders the ticker universe the same way whether it holds
one demo row or, eventually, hundreds of real ones.
"""
from __future__ import annotations

import streamlit as st

from src.models.models import Ticker
from src.ui.components.empty_state import empty_state


def ticker_table(tickers: list[Ticker]) -> None:
    if not tickers:
        empty_state(
            "Ticker universe not yet loaded for this theme.",
            "See Methodology for the Phase 3 curated ticker-universe plan.",
        )
        return

    rows = [
        {
            "Symbol": t.symbol,
            "Company": t.company_name,
            "Exposure": t.exposure.value,
            "Market cap": t.market_cap_bucket,
            "Liquidity": t.liquidity_bucket,
            "Technical strength": t.technical_strength,
            "Risk level": t.risk_level,
            "Demo": "Yes" if t.is_demo else "No",
        }
        for t in tickers
    ]
    st.dataframe(rows, hide_index=True, width="stretch")
