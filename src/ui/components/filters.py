"""Reusable ticker filter bar. Options are derived from whatever data is
actually loaded rather than hardcoded, so this works unchanged once a real
ticker universe replaces the single DEMO row — right now, with one ticker,
most filters will have at most one option and won't visibly narrow
anything, which is expected and not a bug.
"""
from __future__ import annotations

import streamlit as st

from src.models.models import Catalyst, Subtheme, Ticker


def ticker_filter_bar(
    tickers: list[Ticker], subthemes: list[Subtheme], catalysts: list[Catalyst] | None = None, key_prefix: str = "default"
) -> list[Ticker]:
    catalysts = catalysts or []
    with st.expander("Filters (market cap, liquidity, subcategory, exposure, technical strength, catalyst type, risk level)", expanded=False):
        row1 = st.columns(4)
        subtheme_by_name = {s.name: s.slug for s in subthemes}
        selected_subthemes = row1[0].multiselect("Subcategory", list(subtheme_by_name.keys()), key=f"{key_prefix}-subcategory")
        selected_exposure = row1[1].multiselect("Exposure", sorted({t.exposure.value for t in tickers}), key=f"{key_prefix}-exposure")
        selected_market_cap = row1[2].multiselect("Market cap", sorted({t.market_cap_bucket for t in tickers}), key=f"{key_prefix}-market-cap")
        selected_risk = row1[3].multiselect("Risk level", sorted({t.risk_level for t in tickers}), key=f"{key_prefix}-risk")

        row2 = st.columns(3)
        selected_liquidity = row2[0].multiselect("Liquidity", sorted({t.liquidity_bucket for t in tickers}), key=f"{key_prefix}-liquidity")
        selected_tech = row2[1].multiselect("Technical strength", sorted({t.technical_strength for t in tickers}), key=f"{key_prefix}-tech")
        catalyst_types = sorted({c.catalyst_type for c in catalysts})
        selected_catalyst_types = row2[2].multiselect("Catalyst type", catalyst_types, key=f"{key_prefix}-catalyst-type")

    filtered = tickers
    if selected_subthemes:
        slugs = {subtheme_by_name[n] for n in selected_subthemes}
        filtered = [t for t in filtered if t.subtheme_slug in slugs]
    if selected_exposure:
        filtered = [t for t in filtered if t.exposure.value in selected_exposure]
    if selected_market_cap:
        filtered = [t for t in filtered if t.market_cap_bucket in selected_market_cap]
    if selected_risk:
        filtered = [t for t in filtered if t.risk_level in selected_risk]
    if selected_liquidity:
        filtered = [t for t in filtered if t.liquidity_bucket in selected_liquidity]
    if selected_tech:
        filtered = [t for t in filtered if t.technical_strength in selected_tech]
    if selected_catalyst_types:
        symbols_with_catalyst = {c.ticker_symbol for c in catalysts if c.catalyst_type in selected_catalyst_types and c.ticker_symbol}
        filtered = [t for t in filtered if t.symbol in symbols_with_catalyst]
    return filtered
