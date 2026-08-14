"""Tests for the live SEC EDGAR provider. All network calls are mocked —
the test suite must never depend on a live HTTP request to sec.gov."""
from unittest.mock import patch

import pytest

from src.config.settings import Settings
from src.providers.edgar_client import EdgarError
from src.providers.live_edgar import (
    EdgarUnavailableError,
    LiveFilingsProvider,
    LiveFundamentalsProvider,
)
from src.providers.registry import _FilingsWithFallback, _FundamentalsWithFallback
from src.providers.mock_providers import MockFilingsProvider, MockFundamentalsProvider

FAKE_SUBMISSIONS = {
    "filings": {
        "recent": {
            "form": ["4", "8-K", "10-Q", "SCHEDULE 13G"],
            "filingDate": ["2026-08-12", "2026-08-01", "2026-07-15", "2026-07-01"],
            "accessionNumber": ["0001-26-000001", "0001-26-000002", "0001-26-000003", "0001-26-000004"],
            "primaryDocument": ["form4.xml", "8k.htm", "10q.htm", "13g.xml"],
            "primaryDocDescription": ["", "Material event", "Quarterly report", ""],
        }
    }
}

FAKE_COMPANY_FACTS = {
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"end": "2025-06-30", "val": 1000, "form": "10-Q", "fy": 2025, "fp": "Q2", "filed": "2025-07-15", "accn": "0001-25-000009"},
                        {"end": "2026-06-30", "val": 1500, "form": "10-Q", "fy": 2026, "fp": "Q2", "filed": "2026-07-15", "accn": "0001-26-000003"},
                    ]
                }
            },
            "GrossProfit": {
                "units": {"USD": [{"end": "2026-06-30", "val": 900, "form": "10-Q"}]}
            },
            "OperatingIncomeLoss": {
                "units": {"USD": [{"end": "2026-06-30", "val": 300, "form": "10-Q"}]}
            },
            "CashAndCashEquivalentsAtCarryingValue": {
                "units": {"USD": [{"end": "2026-06-30", "val": 5000, "form": "10-Q"}]}
            },
            "NetCashProvidedByUsedInOperatingActivities": {
                "units": {"USD": [{"end": "2026-06-30", "val": 400, "form": "10-Q"}]}
            },
        }
    }
}


# --- LiveFilingsProvider ---

def test_live_filings_filters_to_forms_of_interest():
    settings = Settings()
    provider = LiveFilingsProvider(settings)
    with patch("src.providers.live_edgar.edgar_client.get_cik_for_ticker", return_value=12345):
        with patch("src.providers.live_edgar.edgar_client.get_submissions", return_value=FAKE_SUBMISSIONS):
            filings = provider.get_recent_filings("TEST", limit=5)

    forms = [f.filing_type for f in filings]
    assert "8-K" in forms
    assert "10-Q" in forms
    assert "4" not in forms  # Form 4 (insider) and 13G are not in FILING_FORMS_OF_INTEREST
    assert "SCHEDULE 13G" not in forms
    assert all(f.is_mock is False for f in filings)


def test_live_filings_raises_when_ticker_not_found():
    settings = Settings()
    provider = LiveFilingsProvider(settings)
    with patch("src.providers.live_edgar.edgar_client.get_cik_for_ticker", return_value=None):
        with pytest.raises(EdgarUnavailableError):
            provider.get_recent_filings("NOTREAL")


# --- LiveFundamentalsProvider ---

def test_live_fundamentals_computes_yoy_growth_and_margins():
    settings = Settings()
    provider = LiveFundamentalsProvider(settings)
    with patch("src.providers.live_edgar.edgar_client.get_cik_for_ticker", return_value=12345):
        with patch("src.providers.live_edgar.edgar_client.get_company_facts", return_value=FAKE_COMPANY_FACTS):
            snapshot = provider.get_fundamentals("TEST")

    assert snapshot.revenue == 1500
    assert snapshot.revenue_yoy_growth == pytest.approx(0.5)  # (1500-1000)/1000
    assert snapshot.gross_margin == pytest.approx(900 / 1500)
    assert snapshot.operating_margin == pytest.approx(300 / 1500)
    assert snapshot.free_cash_flow == 400  # no capex tag in fixture -> ocf - 0
    assert snapshot.cash_and_equivalents == 5000
    assert snapshot.is_mock is False


def test_live_fundamentals_raises_when_no_revenue_data():
    settings = Settings()
    provider = LiveFundamentalsProvider(settings)
    with patch("src.providers.live_edgar.edgar_client.get_cik_for_ticker", return_value=12345):
        with patch("src.providers.live_edgar.edgar_client.get_company_facts", return_value={"facts": {"us-gaap": {}}}):
            with pytest.raises(EdgarUnavailableError):
                provider.get_fundamentals("TEST")


# --- registry.py fallback wrappers ---

def test_filings_fallback_to_mock_on_edgar_unavailable():
    live = LiveFilingsProvider(Settings())
    fallback = _FilingsWithFallback(live, MockFilingsProvider())
    with patch("src.providers.live_edgar.edgar_client.get_cik_for_ticker", return_value=None):
        filings = fallback.get_recent_filings("COHR")  # has a bundled mock fixture

    assert len(filings) > 0
    assert all(f.is_mock is True for f in filings)


def test_fundamentals_fallback_to_mock_on_edgar_error():
    live = LiveFundamentalsProvider(Settings())
    fallback = _FundamentalsWithFallback(live, MockFundamentalsProvider())
    with patch("src.providers.live_edgar.edgar_client.get_cik_for_ticker", side_effect=EdgarError("network down")):
        snapshot = fallback.get_fundamentals("COHR")

    assert snapshot.is_mock is True


# --- ticker_registry (Radar ticker verification) ---

def test_verify_ticker_tags_marks_known_us_ticker_verified():
    from src.radar.models import TickerTag
    from src.radar.ticker_registry import verify_ticker_tags

    tags = [TickerTag(ticker="NVDA", company_name="NVIDIA", jurisdiction="United States")]
    with patch("src.radar.ticker_registry.edgar_client.get_all_tickers", return_value={"NVDA": 1045810}):
        result = verify_ticker_tags(tags)

    assert result[0].verified is True


def test_verify_ticker_tags_marks_unknown_us_ticker_unverified():
    from src.radar.models import TickerTag
    from src.radar.ticker_registry import verify_ticker_tags

    tags = [TickerTag(ticker="TOTALLYFAKE", company_name="Fake Co", jurisdiction="United States")]
    with patch("src.radar.ticker_registry.edgar_client.get_all_tickers", return_value={"NVDA": 1045810}):
        result = verify_ticker_tags(tags)

    assert result[0].verified is False


def test_verify_ticker_tags_never_verifies_non_us_jurisdiction():
    from src.radar.models import TickerTag
    from src.radar.ticker_registry import verify_ticker_tags

    tags = [TickerTag(ticker="6758", company_name="Sony", jurisdiction="Japan")]
    result = verify_ticker_tags(tags)  # no EDGAR call needed/patched — must not even try

    assert result[0].verified is False


def test_verify_ticker_tags_never_drops_a_tag_on_registry_failure():
    from src.radar.models import TickerTag
    from src.radar.ticker_registry import edgar_client, verify_ticker_tags

    tags = [TickerTag(ticker="NVDA", company_name="NVIDIA", jurisdiction="United States")]
    with patch("src.radar.ticker_registry.edgar_client.get_all_tickers", side_effect=edgar_client.EdgarError("down")):
        result = verify_ticker_tags(tags)

    assert len(result) == 1
    assert result[0].verified is False
