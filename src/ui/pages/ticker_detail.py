"""Ticker Detail — the reusable per-ticker research template. Reads
`symbol` from st.query_params (defaults to the DEMO ticker if absent). Not
in the primary seven-item navigation — reached via an explicit
st.page_link from Themes and the Market Brief, never a typed-only URL.

This phase validates the template's layout, not example data quality: the
fundamental/technical snapshot fields render as explicit placeholders, not
an invented price, earnings figure, contract, or valuation statistic.
"""
from __future__ import annotations

import streamlit as st

from src.data_access.container import get_repositories
from src.logic.formatting import fmt_date
from src.ui.components.badges import demo_badge
from src.ui.components.cards import catalyst_row, evidence_row
from src.ui.components.empty_state import empty_state
from src.ui.components.section import section_header

DEFAULT_SYMBOL = "DEMO"


def render() -> None:
    ctx = get_repositories()
    symbol = st.query_params.get("symbol", DEFAULT_SYMBOL)
    ticker = ctx.ticker_repository.get_ticker(symbol)

    if ticker is None:
        st.markdown("# Ticker Detail")
        empty_state(
            f"No ticker found for symbol '{symbol}'.",
            f"The only ticker loaded in this phase is the fictional {DEFAULT_SYMBOL} — see Themes to reach it.",
        )
        return

    theme = ctx.theme_repository.get_theme(ticker.theme_slug)
    subtheme = next((s for s in (theme.subthemes if theme else []) if s.slug == ticker.subtheme_slug), None)

    header_cols = st.columns([4, 1])
    with header_cols[0]:
        st.markdown(f"# {ticker.symbol} — {ticker.company_name}")
        tag_line = theme.name if theme else ticker.theme_slug
        if subtheme:
            tag_line += f" / {subtheme.name}"
        st.markdown(f'<div class="er-muted">{tag_line} · {ticker.exposure.value} exposure</div>', unsafe_allow_html=True)
    with header_cols[1]:
        demo_badge()

    st.markdown(f"**Thesis:** {ticker.thesis}")

    section_header("Market expectation")
    st.write(ticker.market_expectation or "Not populated.")

    section_header("What may be underappreciated")
    st.write(ticker.underappreciated or "Not populated.")

    section_header("Fundamental snapshot", "No live data connected — placeholder fields only, not real figures.")
    st.dataframe(
        [{"Metric": m, "Value": "—"} for m in ["Price", "Market cap", "P/E", "Revenue growth", "Gross margin"]],
        hide_index=True, width="stretch",
    )

    section_header("Technical / relative-strength snapshot", "No live data connected — placeholder fields only.")
    st.dataframe(
        [{"Metric": m, "Value": "—"} for m in ["RSI", "Relative strength vs. theme", "50-day trend", "200-day trend"]],
        hide_index=True, width="stretch",
    )

    section_header("Catalyst calendar")
    catalysts = ctx.catalyst_repository.get_catalysts_for_ticker(ticker.symbol)
    if not catalysts:
        empty_state("No catalysts scheduled for this ticker yet.")
    else:
        for c in catalysts:
            catalyst_row(c)

    section_header("Bull / base / bear")
    bull_col, base_col, bear_col = st.columns(3)
    for col, label, factors in [(bull_col, "Bull", ticker.bull_factors), (base_col, "Base", ticker.base_factors), (bear_col, "Bear", ticker.bear_factors)]:
        with col:
            st.markdown(f"**{label}**")
            if factors:
                for f in factors:
                    st.write(f"- {f}")
            else:
                st.caption("Not populated.")

    section_header("Key risks")
    if ticker.key_risks:
        for r in ticker.key_risks:
            st.write(f"- {r}")
    else:
        st.caption("Not populated.")

    section_header("Evidence timeline")
    evidence = ctx.evidence_repository.get_evidence_for_ticker(ticker.symbol)
    if not evidence:
        empty_state("No evidence recorded for this ticker yet.")
    else:
        for e in sorted(evidence, key=lambda e: e.retrieved_at, reverse=True):
            evidence_row(e)

    section_header("Related peers")
    peers = [t for t in ctx.ticker_repository.get_tickers_for_theme(ticker.theme_slug) if t.symbol != ticker.symbol]
    if not peers:
        empty_state(
            "No peer tickers loaded yet.",
            "The curated ticker universe (Phase 3) will populate this with other names in the same theme.",
        )
    else:
        st.write(", ".join(f"{p.symbol} — {p.company_name}" for p in peers))

    section_header("What would change the thesis")
    st.write(ticker.what_would_change_thesis or "Not populated.")

    section_header("Sources")
    if evidence:
        for e in evidence:
            st.markdown(f"- {e.source_name} (no external source — demo data), retrieved {fmt_date(e.retrieved_at)}")
    else:
        st.caption("No sources recorded for this ticker yet.")

    st.divider()
    st.markdown(f'<div class="er-muted">Freshness: demo data, not a live feed. Ticker record is_demo={ticker.is_demo}.</div>', unsafe_allow_html=True)
