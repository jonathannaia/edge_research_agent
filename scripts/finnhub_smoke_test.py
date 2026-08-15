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

    print(f"\n--- Result: {'OK (raw data printed above — inspect before trusting field names)' if ok else 'FAILED'} ---")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
