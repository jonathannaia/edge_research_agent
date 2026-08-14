"""Provider interfaces (abstract base classes) and their data transfer objects.

Each interface is intentionally narrow (one data domain per provider) so a
live provider can be swapped in for a single domain without touching the
others. See mock_providers.py for the V1 implementations and
registry.py for how the app selects between mock/live.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class FundamentalsSnapshot:
    ticker: str
    period_label: str
    period_end_date: str
    revenue: float
    revenue_yoy_growth: float
    gross_margin: float
    gross_margin_prior_year: float
    operating_margin: float
    free_cash_flow: float
    cash_and_equivalents: float
    total_debt: float
    shares_outstanding: float
    shares_outstanding_yoy_change: float
    source_title: str
    source_url_or_identifier: str
    source_date: str
    source_type: str
    is_mock: bool = True


@dataclass
class FilingHighlight:
    ticker: str
    filing_type: str
    title: str
    url_or_identifier: str
    filing_date: str
    highlights: list[tuple[str, str]]  # (excerpt_text, tag)
    is_mock: bool = True


@dataclass
class ManagementCommentary:
    ticker: str
    event_label: str
    event_date: str
    url_or_identifier: str
    quotes: list[tuple[str, str]]  # (quote_text, tag)
    is_mock: bool = True


@dataclass
class InsiderTransaction:
    ticker: str
    insider_name: str
    role: str
    transaction_type: str  # "Buy" | "Sell"
    shares: float
    value_usd: float
    filing_date: str
    url_or_identifier: str
    is_mock: bool = True


@dataclass
class OwnershipSummary:
    ticker: str
    institutional_ownership_pct: float
    insider_ownership_pct: float
    as_of_date: str
    source_url_or_identifier: str
    is_mock: bool = True


@dataclass
class PriceContext:
    ticker: str
    last_price: float
    fifty_two_week_low: float
    fifty_two_week_high: float
    pct_change_3m: float
    pct_change_1y: float
    avg_volume_30d: float
    trend_note: str
    as_of_date: str
    is_mock: bool = True


@dataclass
class ValuationContext:
    ticker: str
    market_cap: float
    ev_to_revenue: Optional[float]
    ev_to_ebitda: Optional[float]
    price_to_sales: Optional[float]
    peer_median_ev_to_revenue: Optional[float]
    as_of_date: str
    is_mock: bool = True


@dataclass
class EarningsCalendarEntry:
    ticker: str
    next_earnings_date: str
    is_confirmed: bool
    is_mock: bool = True


@dataclass
class NewsItem:
    ticker: str
    title: str
    url_or_identifier: str
    published_date: str
    source_type: str
    snippet: str
    tag: str
    is_mock: bool = True


class FundamentalsProvider(ABC):
    @abstractmethod
    def get_fundamentals(self, ticker: str) -> FundamentalsSnapshot: ...


class FilingsProvider(ABC):
    @abstractmethod
    def get_recent_filings(self, ticker: str, limit: int = 5) -> list[FilingHighlight]: ...


class TranscriptProvider(ABC):
    @abstractmethod
    def get_latest_commentary(self, ticker: str) -> Optional[ManagementCommentary]: ...


class InsiderProvider(ABC):
    @abstractmethod
    def get_insider_transactions(self, ticker: str, limit: int = 5) -> list[InsiderTransaction]: ...


class OwnershipProvider(ABC):
    @abstractmethod
    def get_ownership_summary(self, ticker: str) -> Optional[OwnershipSummary]: ...


class PriceProvider(ABC):
    @abstractmethod
    def get_price_context(self, ticker: str) -> Optional[PriceContext]: ...

    @abstractmethod
    def get_valuation_context(self, ticker: str) -> Optional[ValuationContext]: ...


class EarningsCalendarProvider(ABC):
    @abstractmethod
    def get_next_earnings(self, ticker: str) -> Optional[EarningsCalendarEntry]: ...


class NewsProvider(ABC):
    @abstractmethod
    def get_recent_news(self, ticker: str, limit: int = 5) -> list[NewsItem]: ...


@dataclass
class ProviderBundle:
    """All providers the research service needs, grouped for convenience."""

    fundamentals: FundamentalsProvider
    filings: FilingsProvider
    transcripts: TranscriptProvider
    insiders: InsiderProvider
    ownership: OwnershipProvider
    price: PriceProvider
    earnings_calendar: EarningsCalendarProvider
    news: NewsProvider
