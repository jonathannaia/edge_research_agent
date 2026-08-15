#!/usr/bin/env python3
"""Diagnostic-first verification for Finnhub — dumps the RAW real API
response before any parsing logic is trusted. Finnhub's own docs site is
JS-rendered and couldn't be read directly the way SEC EDGAR/DART's could,
so unlike those two integrations, this one starts by inspecting real data
rather than confirmed official documentation. Nothing printed here is
sensitive — quote/valuation data is public; the API key itself is never
printed.

Run via the "Finnhub smoke test" GitHub Actions workflow (workflow_dispatch)
using EDGE_FINNHUB_API_KEY from repo secrets.

Run with: python -m scripts.finnhub_smoke_test
"""
from __future__ import annotations

import json
import sys

from src.config.settings import Settings
from src.providers import finnhub_client
from src.providers.live_price import LivePriceProvider, PriceUnavailableError

TEST_TICKER = "AAPL"


def main() -> int:
    settings = Settings()
    if not settings.finnhub_api_key:
        print("EDGE_FINNHUB_API_KEY is not set.")
        return 1

    ok = True

    print(f"--- Raw /quote response for {TEST_TICKER} ---")
    try:
        quote = finnhub_client.get_quote(TEST_TICKER, settings.finnhub_api_key)
        print(json.dumps(quote, indent=2))
    except finnhub_client.FinnhubError as exc:
        ok = False
        print(f"FAILED: {exc}")

    print(f"\n--- Raw /stock/metric (metric=all) response for {TEST_TICKER} ---")
    try:
        metrics = finnhub_client.get_basic_financials(TEST_TICKER, settings.finnhub_api_key)
        # "series" can be large (historical time series) — print "metric"
        # (current point-in-time values, what we actually need) in full,
        # and just the top-level keys of everything else.
        print("Top-level keys:", list(metrics.keys()))
        print("metric dict keys:", sorted((metrics.get("metric") or {}).keys()))
        print(json.dumps(metrics.get("metric", {}), indent=2))
    except finnhub_client.FinnhubError as exc:
        ok = False
        print(f"FAILED: {exc}")

    print(f"\n--- Parsed PriceContext/ValuationContext for {TEST_TICKER} (via LivePriceProvider) ---")
    try:
        provider = LivePriceProvider(settings)
        price = provider.get_price_context(TEST_TICKER)
        valuation = provider.get_valuation_context(TEST_TICKER)
        print(f"last_price=${price.last_price:.2f}  52w_range=${price.fifty_two_week_low:.2f}-${price.fifty_two_week_high:.2f}")
        print(f"pct_change_3m={price.pct_change_3m:+.1%}  pct_change_1y={price.pct_change_1y:+.1%}")
        print(f"avg_volume_30d(proxy)={price.avg_volume_30d:,.0f} shares")
        print(f"market_cap=${valuation.market_cap:,.0f}")
        print(f"ev_to_revenue={valuation.ev_to_revenue}  ev_to_ebitda={valuation.ev_to_ebitda}  price_to_sales={valuation.price_to_sales}")
        # Sanity checks — these are meant to catch a unit-conversion bug (100x/1,000,000x
        # off), not to validate that the numbers are "correct" in some deeper sense.
        if not (0 < price.pct_change_1y < 3):
            ok = False
            print(f"WARNING: pct_change_1y={price.pct_change_1y} looks like a unit-conversion bug (expected roughly 0-3, i.e. 0-300%).")
        if not (1e11 < valuation.market_cap < 1e14):
            ok = False
            print(f"WARNING: market_cap={valuation.market_cap} looks like a unit-conversion bug for a mega-cap stock.")
    except PriceUnavailableError as exc:
        ok = False
        print(f"FAILED: {exc}")

    print(f"\n--- Result: {'OK' if ok else 'FAILED'} ---")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
