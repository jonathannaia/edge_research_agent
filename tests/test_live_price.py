"""Tests for LivePriceProvider. Uses the real field values from a live
Finnhub response (AAPL, confirmed via scripts/finnhub_smoke_test.py before
this was written) to catch the two unit-conversion traps that field names
alone don't reveal: percent fields are points not fractions, and market
cap/volume fields are in millions."""
from unittest.mock import patch

import pytest

from src.config.settings import Settings
from src.providers.live_price import LivePriceProvider, PriceUnavailableError

REAL_QUOTE = {"c": 305.93, "d": 0.67, "dp": 0.2195, "h": 307.49, "l": 304.3, "o": 306, "pc": 305.26, "t": 1786737600}

REAL_METRIC = {
    "metric": {
        "52WeekHigh": 344.5699,
        "52WeekLow": 223.78,
        "13WeekPriceReturnDaily": 2.3622,
        "52WeekPriceReturnDaily": 31.4245,
        "3MonthAverageTradingVolume": 53.24394,
        "marketCapitalization": 4430136,
        "evRevenueTTM": 9.5859,
        "evEbitdaTTM": 26.643,
        "psTTM": 9.49,
    }
}


def test_price_context_converts_percent_points_to_fraction():
    settings = Settings(finnhub_api_key="fake-key")
    provider = LivePriceProvider(settings)
    with patch("src.providers.live_price.finnhub_client.get_quote", return_value=REAL_QUOTE):
        with patch("src.providers.live_price.finnhub_client.get_basic_financials", return_value=REAL_METRIC):
            ctx = provider.get_price_context("AAPL")

    # 31.4245 (percentage points) must become 0.314245 (fraction), not stay as 31.4245
    assert ctx.pct_change_1y == pytest.approx(0.314245)
    assert ctx.pct_change_3m == pytest.approx(0.023622)


def test_price_context_converts_volume_from_millions():
    settings = Settings(finnhub_api_key="fake-key")
    provider = LivePriceProvider(settings)
    with patch("src.providers.live_price.finnhub_client.get_quote", return_value=REAL_QUOTE):
        with patch("src.providers.live_price.finnhub_client.get_basic_financials", return_value=REAL_METRIC):
            ctx = provider.get_price_context("AAPL")

    # 53.24394 (millions) must become ~53.24M shares, not literally 53.24
    assert ctx.avg_volume_30d == pytest.approx(53_243_940)


def test_price_context_uses_real_last_price_and_range():
    settings = Settings(finnhub_api_key="fake-key")
    provider = LivePriceProvider(settings)
    with patch("src.providers.live_price.finnhub_client.get_quote", return_value=REAL_QUOTE):
        with patch("src.providers.live_price.finnhub_client.get_basic_financials", return_value=REAL_METRIC):
            ctx = provider.get_price_context("AAPL")

    assert ctx.last_price == 305.93
    assert ctx.fifty_two_week_low == 223.78
    assert ctx.fifty_two_week_high == 344.5699
    assert ctx.is_mock is False


def test_price_context_raises_without_api_key():
    settings = Settings(finnhub_api_key="")
    provider = LivePriceProvider(settings)
    with pytest.raises(PriceUnavailableError):
        provider.get_price_context("AAPL")


def test_price_context_raises_on_zero_price():
    """Finnhub returns c=0 (not an error) for an unrecognized symbol."""
    settings = Settings(finnhub_api_key="fake-key")
    provider = LivePriceProvider(settings)
    with patch("src.providers.live_price.finnhub_client.get_quote", return_value={"c": 0, "h": 0, "l": 0}):
        with pytest.raises(PriceUnavailableError):
            provider.get_price_context("NOTREAL")


def test_valuation_context_converts_market_cap_from_millions():
    settings = Settings(finnhub_api_key="fake-key")
    provider = LivePriceProvider(settings)
    with patch("src.providers.live_price.finnhub_client.get_basic_financials", return_value=REAL_METRIC):
        ctx = provider.get_valuation_context("AAPL")

    # 4,430,136 (millions) must become ~$4.43 trillion, not literally $4.43M
    assert ctx.market_cap == pytest.approx(4_430_136_000_000)
    assert ctx.ev_to_revenue == pytest.approx(9.5859)
    assert ctx.ev_to_ebitda == pytest.approx(26.643)
    assert ctx.price_to_sales == pytest.approx(9.49)
    assert ctx.is_mock is False


def test_valuation_context_leaves_peer_comparison_unset_not_fabricated():
    settings = Settings(finnhub_api_key="fake-key")
    provider = LivePriceProvider(settings)
    with patch("src.providers.live_price.finnhub_client.get_basic_financials", return_value=REAL_METRIC):
        ctx = provider.get_valuation_context("AAPL")

    assert ctx.peer_median_ev_to_revenue is None
