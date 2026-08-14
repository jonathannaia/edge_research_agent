"""Provider selection. Swap mock -> live here, one domain at a time.

EDGE_DATA_MODE=live currently activates live SEC EDGAR filings and
fundamentals for US-listed tickers (src/providers/live_edgar.py) — the
rest of the domains (transcripts, insiders, ownership, price, earnings
calendar, news) are still mock; see README's Data Provider Integration
Guide for what each would take. Non-US filings (Japan/Korea/China/Hong
Kong) are also not live yet — see README section 4's jurisdiction table.

Live filings/fundamentals fall back to mock per-ticker (not per-app) if
EDGAR has no data for that ticker or a request fails — the app never
breaks because one company isn't in the SEC's system, and the fallback
result is still correctly labeled is_mock=True so the UI never presents
degraded data as real.
"""
from __future__ import annotations

from src.config.settings import Settings, get_settings
from src.providers.base import (
    FilingHighlight,
    FilingsProvider,
    FundamentalsProvider,
    FundamentalsSnapshot,
    ProviderBundle,
)
from src.providers.edgar_client import EdgarError
from src.providers.live_edgar import (
    EdgarUnavailableError,
    LiveFilingsProvider,
    LiveFundamentalsProvider,
)
from src.providers.mock_providers import (
    MockEarningsCalendarProvider,
    MockFilingsProvider,
    MockFundamentalsProvider,
    MockInsiderProvider,
    MockNewsProvider,
    MockOwnershipProvider,
    MockPriceProvider,
    MockTranscriptProvider,
)


class _FilingsWithFallback(FilingsProvider):
    """Live SEC EDGAR filings, falling back to mock per-ticker on any
    EDGAR-side failure (unlisted ticker, network error, no data)."""

    def __init__(self, live: LiveFilingsProvider, mock: MockFilingsProvider):
        self._live = live
        self._mock = mock

    def get_recent_filings(self, ticker: str, limit: int = 5) -> list[FilingHighlight]:
        try:
            filings = self._live.get_recent_filings(ticker, limit)
            if filings:
                return filings
        except (EdgarUnavailableError, EdgarError):
            pass
        return self._mock.get_recent_filings(ticker, limit)


class _FundamentalsWithFallback(FundamentalsProvider):
    def __init__(self, live: LiveFundamentalsProvider, mock: MockFundamentalsProvider):
        self._live = live
        self._mock = mock

    def get_fundamentals(self, ticker: str) -> FundamentalsSnapshot:
        try:
            return self._live.get_fundamentals(ticker)
        except (EdgarUnavailableError, EdgarError):
            return self._mock.get_fundamentals(ticker)


def get_provider_bundle(settings: Settings | None = None) -> ProviderBundle:
    settings = settings or get_settings()

    mock_filings = MockFilingsProvider()
    mock_fundamentals = MockFundamentalsProvider()

    if settings.data_mode == "live":
        filings: FilingsProvider = _FilingsWithFallback(LiveFilingsProvider(settings), mock_filings)
        fundamentals: FundamentalsProvider = _FundamentalsWithFallback(
            LiveFundamentalsProvider(settings), mock_fundamentals
        )
    else:
        filings = mock_filings
        fundamentals = mock_fundamentals

    return ProviderBundle(
        fundamentals=fundamentals,
        filings=filings,
        transcripts=MockTranscriptProvider(),
        insiders=MockInsiderProvider(),
        ownership=MockOwnershipProvider(),
        price=MockPriceProvider(),
        earnings_calendar=MockEarningsCalendarProvider(),
        news=MockNewsProvider(),
    )
