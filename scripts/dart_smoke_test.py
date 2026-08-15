#!/usr/bin/env python3
"""Manual verification for the live DART (Korea) provider — not part of the
regular test suite (those are all mocked). Run via the "DART smoke test"
GitHub Actions workflow (workflow_dispatch) to confirm live_dart.py's
endpoints, parameters, and account-name matching actually work against a
real API response, using EDGE_DART_API_KEY from repo secrets. Nothing
printed here is sensitive — filing metadata and financial figures are
public company disclosures; the API key itself is never printed.

Run with: python -m scripts.dart_smoke_test
"""
from __future__ import annotations

import sys

from src.config.settings import Settings
from src.providers.live_dart import (
    DartUnavailableError,
    LiveDartFilingsProvider,
    LiveDartFundamentalsProvider,
)

# Samsung Electronics — a large, certainly-listed company, good for a
# connectivity/correctness smoke test.
TEST_TICKER = "005930"


def main() -> int:
    settings = Settings()
    if not settings.dart_api_key:
        print("EDGE_DART_API_KEY is not set.")
        return 1

    ok = True

    print(f"--- Filings for {TEST_TICKER} ---")
    try:
        filings = LiveDartFilingsProvider(settings).get_recent_filings(TEST_TICKER, limit=5)
        print(f"{len(filings)} filing(s) returned")
        for f in filings:
            print(f"  {f.filing_date}  {f.filing_type}  {f.url_or_identifier}")
        if not filings:
            ok = False
            print("WARNING: zero filings returned for a major company — check the response shape.")
    except DartUnavailableError as exc:
        ok = False
        print(f"FAILED: {exc}")

    print(f"\n--- Fundamentals for {TEST_TICKER} ---")
    try:
        snap = LiveDartFundamentalsProvider(settings).get_fundamentals(TEST_TICKER)
        print(f"period: {snap.period_label} (end {snap.period_end_date})")
        print(f"revenue: {snap.revenue:,.0f}  yoy_growth: {snap.revenue_yoy_growth:.1%}")
        print(f"gross_margin: {snap.gross_margin:.1%}  operating_margin: {snap.operating_margin:.1%}")
        print(f"cash: {snap.cash_and_equivalents:,.0f}  total_debt: {snap.total_debt:,.0f}")
        print(f"source: {snap.source_url_or_identifier}")
        if snap.revenue <= 0:
            ok = False
            print("WARNING: revenue is zero/negative for a major company — check account name matching.")
    except DartUnavailableError as exc:
        ok = False
        print(f"FAILED: {exc}")

    print(f"\n--- Result: {'OK' if ok else 'FAILED'} ---")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
