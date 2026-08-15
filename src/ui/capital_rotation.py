"""Capital Rotation — theme-level price momentum comparison for your
tracked watchlist (data/tracked_tickers.json), built from the same live
snapshot data src/radar/snapshots.py already refreshes on Radar's
schedule. Nothing on this page triggers a fetch.

Scope, stated plainly rather than left implicit:
- This is a PRICE-MOMENTUM PROXY for rotation, not literal capital/fund-
  flow tracking — there's no free source for actual money-flow data.
- Cross-theme "connections" are evidence-linked only: a finding is shown
  here only when a single cited Radar finding already, factually, names
  tickers from two different themes. This page never asserts that two
  SEPARATE articles are causally related — that would be an inference
  this app's guardrails don't allow (see README "Radar" section).
"""
from __future__ import annotations

import statistics

import streamlit as st

from src.config.settings import Settings
from src.radar import analytics, snapshots, store
from src.ui.components import hours_ago
from src.utils.formatting import fmt_pct


def render(settings: Settings) -> None:
    st.caption(
        "Price-momentum comparison across your tracked themes — a proxy built from live price data, "
        "not actual capital/fund-flow tracking (no free source for that exists). Refreshed on Radar's "
        "schedule (~every 2h), not on page load."
    )

    ticker_themes = snapshots.load_ticker_themes()
    all_snapshots = snapshots.load_snapshots()

    if not ticker_themes:
        st.info(
            "No themes defined yet. Edit `data/tracked_tickers.json`'s `themes` object to add tickers "
            "grouped by theme — see the README \"Radar\" section."
        )
        return
    if not all_snapshots:
        st.info("No snapshot data yet — Radar hasn't run since these tickers were added, or none have live data yet.")
        return

    # --- Theme momentum table ---
    st.subheader("Theme momentum")
    theme_tickers: dict[str, list[str]] = {}
    for ticker, theme in ticker_themes.items():
        theme_tickers.setdefault(theme, []).append(ticker)

    rows = []
    for theme, tickers in sorted(theme_tickers.items()):
        returns_1d, returns_1y = [], []
        for t in tickers:
            snap = all_snapshots.get(t)
            if not snap:
                continue
            if snap.get("pct_change_1d") is not None:
                returns_1d.append(snap["pct_change_1d"] / 100)
            price = snap.get("price")
            if price and price.get("pct_change_1y") is not None:
                returns_1y.append(price["pct_change_1y"])
        n_with_data = len({t for t in tickers if all_snapshots.get(t) and all_snapshots[t].get("price")})
        rows.append(
            {
                "Theme": theme,
                "Tickers": len(tickers),
                "With live data": n_with_data,
                "Median 1-day move": fmt_pct(statistics.median(returns_1d)) if returns_1d else "—",
                "Median 1-year return": fmt_pct(statistics.median(returns_1y)) if returns_1y else "—",
            }
        )
    st.dataframe(rows, width="stretch", hide_index=True)
    st.caption(
        "Median, not average — a single distorted stock (e.g. a recent spinoff or IPO, where a low "
        "base price a year ago produces a mathematically extreme but real % return) shouldn't set the "
        "whole theme's number. Confirmed against live Finnhub data directly, not assumed: SanDisk's "
        "(SNDK) 2024 spinoff from Western Digital is a real example of this in the current data."
    )
    if not any(t for t in theme_tickers.get("Humanoid Robotics", [])):
        st.caption(
            "\"Humanoid Robotics\" has no tracked tickers — that theme is still covered via Radar's "
            "existing Humanoids niche findings, just not in this price comparison."
        )

    # --- Notable & watch-trigger moves this cycle ---
    notable = [(t, s) for t, s in all_snapshots.items() if s.get("unusual_move") and t in ticker_themes]
    triggers = [(t, s) for t, s in all_snapshots.items() if s.get("watch_trigger_move") and t in ticker_themes]

    if triggers:
        st.subheader("Watch triggers")
        st.warning(
            "Single-day price move ≥7% — the price-based watch-trigger threshold from your spec. "
            "Export-control rule changes (BIS Entity List, EAR amendments) are covered separately, "
            "as regular Radar findings under Macro / Rates / Policy — not as a price trigger here. "
            "Credit rating changes, guidance cuts, and IPO pricing still aren't wired up — no free "
            "live source found for the first two, and no live source configured for the third."
        )
        st.dataframe(
            [
                {"Ticker": t, "Theme": ticker_themes[t], "1-day move": fmt_pct(s["pct_change_1d"] / 100),
                 "Retrieved": hours_ago(s.get("retrieved_at", ""))}
                for t, s in sorted(triggers, key=lambda x: abs(x[1]["pct_change_1d"]), reverse=True)
            ],
            width="stretch", hide_index=True,
        )

    if notable:
        st.subheader("Notable moves (≥3%)")
        st.dataframe(
            [
                {"Ticker": t, "Theme": ticker_themes[t], "1-day move": fmt_pct(s["pct_change_1d"] / 100)}
                for t, s in sorted(notable, key=lambda x: abs(x[1]["pct_change_1d"]), reverse=True)
                if not s.get("watch_trigger_move")
            ],
            width="stretch", hide_index=True,
        )

    # --- Analyst sentiment ---
    with_ratings = [(t, s["analyst_recommendations"]) for t, s in all_snapshots.items() if s.get("analyst_recommendations") and t in ticker_themes]
    if with_ratings:
        st.subheader("Analyst recommendation trends")
        st.caption(
            "Aggregate analyst buy/hold/sell counts (Finnhub, free tier). Individual price targets "
            "aren't available on the free tier and aren't shown."
        )
        st.dataframe(
            [
                {
                    "Ticker": t, "Theme": ticker_themes[t], "Period": r.get("period", ""),
                    "Strong Buy": r.get("strongBuy", 0), "Buy": r.get("buy", 0), "Hold": r.get("hold", 0),
                    "Sell": r.get("sell", 0), "Strong Sell": r.get("strongSell", 0),
                }
                for t, r in sorted(with_ratings)
            ],
            width="stretch", hide_index=True,
        )

    # --- Evidence-linked cross-theme findings ---
    st.subheader("Cross-theme findings")
    st.caption(
        "Radar findings that already, factually, name tickers from two or more different themes in "
        "the same cited article. This is the only \"cross-theme connection\" made here — no inference "
        "about separate articles being related."
    )
    findings = store.load_findings()
    cross_theme = analytics.find_cross_theme_findings(findings, ticker_themes)
    if not cross_theme:
        st.caption("None found yet in Radar's findings history.")
    for item in cross_theme[:20]:
        f = item["finding"]
        with st.container(border=True):
            st.markdown(f"**{f.headline}**")
            st.caption(f"Themes: {', '.join(item['themes'])} · {f.source_name} · {hours_ago(f.retrieved_at)}")
            st.write(f.summary)
            st.write(f"[Read source]({f.source_url})")
