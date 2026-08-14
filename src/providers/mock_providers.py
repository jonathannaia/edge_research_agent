"""Mock data providers.

These implement every provider interface in base.py using local JSON fixtures
in sample_data/ for the three seed tickers (COHR, AAOI, AXTI). For any other
ticker the user adds, a deterministic synthetic snapshot is generated from a
hash of the ticker symbol so the app remains fully usable before any live API
is connected — every mock value is clearly labeled `is_mock=True` and every
generated title/identifier is prefixed "MOCK" so it can never be confused
with a real citation.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from src.providers.base import (
    EarningsCalendarEntry,
    EarningsCalendarProvider,
    FilingHighlight,
    FilingsProvider,
    FundamentalsProvider,
    FundamentalsSnapshot,
    InsiderProvider,
    InsiderTransaction,
    ManagementCommentary,
    NewsItem,
    NewsProvider,
    OwnershipProvider,
    OwnershipSummary,
    PriceContext,
    PriceProvider,
    TranscriptProvider,
    ValuationContext,
)

_SAMPLE_DATA_DIR = Path(__file__).resolve().parents[2] / "sample_data"

FIXTURE_FILES = {
    "COHR": "mock_cohr.json",
    "AAOI": "mock_aaoi.json",
    "AXTI": "mock_axti.json",
}


def _load_fixture(ticker: str) -> Optional[dict]:
    filename = FIXTURE_FILES.get(ticker.upper())
    if not filename:
        return None
    path = _SAMPLE_DATA_DIR / filename
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _ticker_seed(ticker: str) -> int:
    return int(hashlib.sha256(ticker.upper().encode()).hexdigest(), 16)


def _synthetic_fixture(ticker: str) -> dict:
    """Deterministically generate a plausible-but-fictional dataset for a
    ticker with no bundled fixture, so the app works for any watchlist entry
    in mock mode."""
    seed = _ticker_seed(ticker)
    rev_growth = ((seed % 41) - 15) / 100.0  # -0.15 .. 0.25
    gm = 0.20 + (seed % 30) / 100.0
    gm_prior = gm - (((seed >> 4) % 11) - 5) / 100.0
    today = date.today()
    filing_date = (today - timedelta(days=15 + (seed % 70))).isoformat()

    return {
        "is_mock": True,
        "mock_disclaimer": (
            f"No bundled fixture exists for {ticker.upper()}; this dataset was "
            "synthetically generated so the app remains usable in mock mode. "
            "It is not real financial data."
        ),
        "ticker": ticker.upper(),
        "fundamentals": {
            "period_label": "MOCK Most Recent Quarter",
            "period_end_date": filing_date,
            "revenue": float(50_000_000 + (seed % 900_000_000)),
            "revenue_yoy_growth": rev_growth,
            "gross_margin": gm,
            "gross_margin_prior_year": gm_prior,
            "operating_margin": gm - 0.20,
            "free_cash_flow": float((seed % 50_000_000) - 15_000_000),
            "cash_and_equivalents": float(10_000_000 + (seed % 200_000_000)),
            "total_debt": float(seed % 150_000_000),
            "shares_outstanding": float(10_000_000 + (seed % 100_000_000)),
            "shares_outstanding_yoy_change": ((seed >> 8) % 8) / 100.0,
            "source_title": f"MOCK synthetic filing for {ticker.upper()} (no bundled fixture)",
            "source_url_or_identifier": f"MOCK-SYNTHETIC-{ticker.upper()}",
            "source_date": filing_date,
            "source_type": "Regulatory Filing",
        },
        "filings": [
            {
                "filing_type": "10-Q",
                "title": f"MOCK synthetic quarterly filing for {ticker.upper()}",
                "url_or_identifier": f"MOCK-SYNTHETIC-10Q-{ticker.upper()}",
                "filing_date": filing_date,
                "highlights": [
                    [
                        "MOCK: Synthetic placeholder evidence — no bundled fixture for this "
                        "ticker. Add real evidence via the Sources page or wire a live provider.",
                        "neutral",
                    ]
                ],
            }
        ],
        "commentary": None,
        "insider_transactions": [],
        "ownership": {
            "institutional_ownership_pct": ((seed >> 12) % 80) / 100.0,
            "insider_ownership_pct": ((seed >> 20) % 15) / 100.0,
            "as_of_date": filing_date,
            "source_url_or_identifier": f"MOCK-SYNTHETIC-OWNERSHIP-{ticker.upper()}",
        },
        "price_context": {
            "last_price": round(5 + (seed % 20000) / 100.0, 2),
            "fifty_two_week_low": round(3 + (seed % 10000) / 100.0, 2),
            "fifty_two_week_high": round(10 + (seed % 30000) / 100.0, 2),
            "pct_change_3m": (((seed >> 6) % 60) - 30) / 100.0,
            "pct_change_1y": (((seed >> 10) % 100) - 40) / 100.0,
            "avg_volume_30d": float(100_000 + (seed % 4_000_000)),
            "trend_note": "MOCK: Synthetic price context only, not a signal on its own.",
            "as_of_date": today.isoformat(),
        },
        "valuation_context": {
            "market_cap": float(50_000_000 + (seed % 5_000_000_000)),
            "ev_to_revenue": round(1 + (seed % 800) / 100.0, 2),
            "ev_to_ebitda": None,
            "price_to_sales": round(1 + (seed % 600) / 100.0, 2),
            "peer_median_ev_to_revenue": 4.0,
            "as_of_date": today.isoformat(),
        },
        "earnings_calendar": {
            "next_earnings_date": (today + timedelta(days=30 + (seed % 60))).isoformat(),
            "is_confirmed": False,
        },
        "news": [],
    }


def _fixture(ticker: str) -> dict:
    return _load_fixture(ticker) or _synthetic_fixture(ticker)


class MockFundamentalsProvider(FundamentalsProvider):
    def get_fundamentals(self, ticker: str) -> FundamentalsSnapshot:
        f = _fixture(ticker)["fundamentals"]
        return FundamentalsSnapshot(ticker=ticker.upper(), **f)


class MockFilingsProvider(FilingsProvider):
    def get_recent_filings(self, ticker: str, limit: int = 5) -> list[FilingHighlight]:
        filings = _fixture(ticker).get("filings", [])[:limit]
        return [
            FilingHighlight(
                ticker=ticker.upper(),
                filing_type=f["filing_type"],
                title=f["title"],
                url_or_identifier=f["url_or_identifier"],
                filing_date=f["filing_date"],
                highlights=[tuple(h) for h in f["highlights"]],
            )
            for f in filings
        ]


class MockTranscriptProvider(TranscriptProvider):
    def get_latest_commentary(self, ticker: str) -> Optional[ManagementCommentary]:
        c = _fixture(ticker).get("commentary")
        if not c:
            return None
        return ManagementCommentary(
            ticker=ticker.upper(),
            event_label=c["event_label"],
            event_date=c["event_date"],
            url_or_identifier=c["url_or_identifier"],
            quotes=[tuple(q) for q in c["quotes"]],
        )


class MockInsiderProvider(InsiderProvider):
    def get_insider_transactions(self, ticker: str, limit: int = 5) -> list[InsiderTransaction]:
        txns = _fixture(ticker).get("insider_transactions", [])[:limit]
        return [InsiderTransaction(ticker=ticker.upper(), **t) for t in txns]


class MockOwnershipProvider(OwnershipProvider):
    def get_ownership_summary(self, ticker: str) -> Optional[OwnershipSummary]:
        o = _fixture(ticker).get("ownership")
        if not o:
            return None
        return OwnershipSummary(ticker=ticker.upper(), **o)


class MockPriceProvider(PriceProvider):
    def get_price_context(self, ticker: str) -> Optional[PriceContext]:
        p = _fixture(ticker).get("price_context")
        if not p:
            return None
        return PriceContext(ticker=ticker.upper(), **p)

    def get_valuation_context(self, ticker: str) -> Optional[ValuationContext]:
        v = _fixture(ticker).get("valuation_context")
        if not v:
            return None
        return ValuationContext(ticker=ticker.upper(), **v)


class MockEarningsCalendarProvider(EarningsCalendarProvider):
    def get_next_earnings(self, ticker: str) -> Optional[EarningsCalendarEntry]:
        e = _fixture(ticker).get("earnings_calendar")
        if not e:
            return None
        return EarningsCalendarEntry(ticker=ticker.upper(), **e)


class MockNewsProvider(NewsProvider):
    def get_recent_news(self, ticker: str, limit: int = 5) -> list[NewsItem]:
        items = _fixture(ticker).get("news", [])[:limit]
        return [NewsItem(ticker=ticker.upper(), **n) for n in items]


def get_watchlist_seed(ticker: str) -> Optional[dict]:
    """Only defined for bundled fixtures — used by the DB seed script."""
    fixture = _load_fixture(ticker)
    if not fixture:
        return None
    return {
        "company_name": fixture["company_name"],
        "sector": fixture["sector"],
        "subtheme": fixture["subtheme"],
        "market_cap_category": fixture["market_cap_category"],
        "jurisdiction": fixture.get("jurisdiction", "United States"),
        "watchlist_seed": fixture["watchlist_seed"],
        "thesis": fixture["thesis"],
    }
