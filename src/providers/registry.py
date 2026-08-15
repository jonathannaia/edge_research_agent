"""Provider selection. Swap mock -> live here, one domain at a time.

EDGE_DATA_MODE=live currently activates:
  - Live SEC EDGAR filings/fundamentals for US-listed tickers (free, keyless).
  - Live DART filings/fundamentals for South Korea-listed tickers, IF
    EDGE_DART_API_KEY is set (DART requires a free registered key — see
    README "Filings beyond the US"). Korean tickers are DART's 6-digit
    exchange stock codes (e.g. "005930" for Samsung Electronics), not
    letter symbols.
  - Everything else (transcripts, insiders, ownership, price, earnings
    calendar, news; and filings/fundamentals for every other jurisdiction)
    is still mock — see README's Data Provider Integration Guide.

Both live filings/fundamentals providers fall back to mock per-ticker (not
per-app) on any failure — unlisted ticker, network error, missing DART key,
no data for that ticker/year. The app never breaks because one company
isn't in a regulator's system, and the fallback result is still correctly
labeled is_mock=True so the UI never presents degraded data as real.

Routing by jurisdiction happens here, not inside the provider classes
themselves, since a ticker's jurisdiction lives in the app's own database
(the `tickers` table) — something none of the provider interfaces have
access to on their own.
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
from src.providers.dart_client import DartError
from src.providers.edgar_client import EdgarError
from src.providers.live_dart import (
    DartUnavailableError,
    LiveDartFilingsProvider,
    LiveDartFundamentalsProvider,
)
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

UNITED_STATES = "United States"
SOUTH_KOREA = "South Korea"


def _ticker_jurisdiction(settings: Settings, ticker: str) -> str:
    """Looks up a ticker's jurisdiction from the app's own database. Falls
    back to "United States" if the ticker isn't found or the DB isn't
    reachable — matches the app's existing default for new tickers, and
    means a lookup failure degrades to EDGAR/mock rather than crashing."""
    try:
        from src.database.db import get_connection
        from src.services import ticker_service

        with get_connection(settings) as conn:
            row = ticker_service.get_ticker(conn, ticker)
            return row["jurisdiction"] if row else UNITED_STATES
    except Exception:
        return UNITED_STATES


class _RoutedFilingsProvider(FilingsProvider):
    """Routes each call to the right regulator by the ticker's jurisdiction,
    falling back to mock on any live-provider failure."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._mock = MockFilingsProvider()
        self._edgar = LiveFilingsProvider(settings)
        self._dart = LiveDartFilingsProvider(settings)

    def get_recent_filings(self, ticker: str, limit: int = 5) -> list[FilingHighlight]:
        jurisdiction = _ticker_jurisdiction(self._settings, ticker)
        try:
            if jurisdiction == UNITED_STATES:
                filings = self._edgar.get_recent_filings(ticker, limit)
            elif jurisdiction == SOUTH_KOREA:
                filings = self._dart.get_recent_filings(ticker, limit)
            else:
                filings = []
            if filings:
                return filings
        except (EdgarUnavailableError, EdgarError, DartUnavailableError, DartError):
            pass
        return self._mock.get_recent_filings(ticker, limit)


class _RoutedFundamentalsProvider(FundamentalsProvider):
    def __init__(self, settings: Settings):
        self._settings = settings
        self._mock = MockFundamentalsProvider()
        self._edgar = LiveFundamentalsProvider(settings)
        self._dart = LiveDartFundamentalsProvider(settings)

    def get_fundamentals(self, ticker: str) -> FundamentalsSnapshot:
        jurisdiction = _ticker_jurisdiction(self._settings, ticker)
        try:
            if jurisdiction == UNITED_STATES:
                return self._edgar.get_fundamentals(ticker)
            elif jurisdiction == SOUTH_KOREA:
                return self._dart.get_fundamentals(ticker)
        except (EdgarUnavailableError, EdgarError, DartUnavailableError, DartError):
            pass
        return self._mock.get_fundamentals(ticker)


def get_provider_bundle(settings: Settings | None = None) -> ProviderBundle:
    settings = settings or get_settings()

    if settings.data_mode == "live":
        filings: FilingsProvider = _RoutedFilingsProvider(settings)
        fundamentals: FundamentalsProvider = _RoutedFundamentalsProvider(settings)
    else:
        filings = MockFilingsProvider()
        fundamentals = MockFundamentalsProvider()

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
