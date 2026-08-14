"""Provider selection. Swap mock -> live here, one domain at a time.

V1 only ships mock providers. To go live for one data domain, implement the
matching interface in a new module (e.g. src/providers/live_edgar.py
implementing FilingsProvider) and swap it in below behind the
EDGE_DATA_MODE check — the rest of the app (services, scoring, UI) never
imports a concrete provider class directly, only ProviderBundle.
"""
from __future__ import annotations

from src.config.settings import Settings, get_settings
from src.providers.base import ProviderBundle
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


def get_provider_bundle(settings: Settings | None = None) -> ProviderBundle:
    settings = settings or get_settings()

    # "live" mode is a placeholder in V1 — see README's Data Provider
    # Integration Guide. We deliberately fall back to mock rather than
    # silently failing so the app never breaks because a key is missing.
    if settings.data_mode == "live":
        pass  # intentionally no live providers wired yet

    return ProviderBundle(
        fundamentals=MockFundamentalsProvider(),
        filings=MockFilingsProvider(),
        transcripts=MockTranscriptProvider(),
        insiders=MockInsiderProvider(),
        ownership=MockOwnershipProvider(),
        price=MockPriceProvider(),
        earnings_calendar=MockEarningsCalendarProvider(),
        news=MockNewsProvider(),
    )
