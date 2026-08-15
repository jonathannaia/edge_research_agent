"""Live price/valuation provider — Finnhub, free tier, US-listed tickers
only (confirmed: international exchanges including KRX/Korea require a
paid plan).

Verification note: Finnhub's own documentation site is JS-rendered and
couldn't be read directly the way SEC EDGAR/DART's docs could — so unlike
those two, this was built from a real raw API response
(scripts/finnhub_smoke_test.py against live AAPL data) rather than
official docs. That raw response caught two unit traps that would have
silently produced wrong numbers if guessed from field names alone:
  - Percent-return fields (e.g. "52WeekPriceReturnDaily") are already in
    percentage points (31.42 meaning +31.42%), not fractions — the app's
    PriceContext/fmt_pct expects a fraction (0.3142), so these are divided
    by 100 here.
  - "marketCapitalization" and the *AverageTradingVolume fields are
    expressed in millions, not raw units — multiplied by 1,000,000 here.
Getting either of these wrong would have shipped a scorecard with prices
that look "right" in isolation but are off by 100x internally.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from src.config.settings import Settings
from src.providers import finnhub_client
from src.providers.base import PriceContext, PriceProvider, ValuationContext


class PriceUnavailableError(RuntimeError):
    """Raised when Finnhub has no usable quote for a ticker — callers
    should fall back to mock rather than crash the research pipeline."""


def _require_key(settings: Settings) -> str:
    if not settings.finnhub_api_key:
        raise PriceUnavailableError("EDGE_FINNHUB_API_KEY is not set.")
    return settings.finnhub_api_key


class LivePriceProvider(PriceProvider):
    def __init__(self, settings: Settings):
        self._settings = settings

    def get_price_context(self, ticker: str) -> Optional[PriceContext]:
        api_key = _require_key(self._settings)
        try:
            quote = finnhub_client.get_quote(ticker, api_key)
        except finnhub_client.FinnhubError as exc:
            raise PriceUnavailableError(str(exc)) from exc

        last_price = quote.get("c")
        if not last_price:  # Finnhub returns c=0 for an unrecognized/delisted symbol
            raise PriceUnavailableError(f"No quote data from Finnhub for {ticker!r}.")

        try:
            metrics_resp = finnhub_client.get_basic_financials(ticker, api_key)
        except finnhub_client.FinnhubError as exc:
            raise PriceUnavailableError(str(exc)) from exc
        metric = metrics_resp.get("metric", {})

        week_low = metric.get("52WeekLow")
        week_high = metric.get("52WeekHigh")
        if week_low is None or week_high is None:
            raise PriceUnavailableError(f"No 52-week range from Finnhub for {ticker!r}.")

        pct_3m = metric.get("13WeekPriceReturnDaily")
        pct_1y = metric.get("52WeekPriceReturnDaily")
        # Finnhub doesn't expose an exact 30-day average volume on the free
        # tier — 3-month average is the closest available and used as a
        # documented proxy, not a fabricated 30-day figure.
        avg_volume_3mo = metric.get("3MonthAverageTradingVolume")

        return PriceContext(
            ticker=ticker.upper(),
            last_price=float(last_price),
            fifty_two_week_low=float(week_low),
            fifty_two_week_high=float(week_high),
            pct_change_3m=(float(pct_3m) / 100) if pct_3m is not None else 0.0,
            pct_change_1y=(float(pct_1y) / 100) if pct_1y is not None else 0.0,
            avg_volume_30d=(float(avg_volume_3mo) * 1_000_000) if avg_volume_3mo is not None else 0.0,
            trend_note=(
                "Live price data from Finnhub (free tier). Volume figure is a 3-month average, "
                "not exactly 30 days — Finnhub's free tier doesn't expose that window. "
                "Not a trading signal on its own."
            ),
            as_of_date=date.today().isoformat(),
            is_mock=False,
        )

    def get_valuation_context(self, ticker: str) -> Optional[ValuationContext]:
        api_key = _require_key(self._settings)
        try:
            metrics_resp = finnhub_client.get_basic_financials(ticker, api_key)
        except finnhub_client.FinnhubError as exc:
            raise PriceUnavailableError(str(exc)) from exc
        metric = metrics_resp.get("metric", {})

        market_cap = metric.get("marketCapitalization")
        if market_cap is None:
            raise PriceUnavailableError(f"No market cap from Finnhub for {ticker!r}.")

        return ValuationContext(
            ticker=ticker.upper(),
            market_cap=float(market_cap) * 1_000_000,
            ev_to_revenue=float(metric["evRevenueTTM"]) if metric.get("evRevenueTTM") is not None else None,
            ev_to_ebitda=float(metric["evEbitdaTTM"]) if metric.get("evEbitdaTTM") is not None else None,
            price_to_sales=float(metric["psTTM"]) if metric.get("psTTM") is not None else None,
            # Finnhub's free tier doesn't provide a peer-group comparison —
            # left unset (Optional) rather than fabricated.
            peer_median_ev_to_revenue=None,
            as_of_date=date.today().isoformat(),
            is_mock=False,
        )
