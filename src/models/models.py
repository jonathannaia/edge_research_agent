"""Structured domain models used across the app.

Dataclasses are used (not an ORM) to keep the dependency surface small and
the mapping to/from SQLite rows explicit and auditable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Tier(str, Enum):
    ACTIVE_RESEARCH = "Active Research"
    WATCH_CLOSELY = "Watch Closely"
    AVOID_BROKEN_THESIS = "Avoid / Broken Thesis"


class EvidenceStatus(str, Enum):
    STRENGTHENING = "Strengthening"
    UNCHANGED = "Unchanged"
    WEAKENING = "Weakening"
    INSUFFICIENT = "Insufficient evidence"


class Jurisdiction(str, Enum):
    """Which market/regulator a ticker's primary filings come from. Purely
    informational plus a hint for which regulatory filing system a live
    FilingsProvider should query (SEC EDGAR, EDINET, DART, CNINFO/HKEX, ...)."""

    UNITED_STATES = "United States"
    JAPAN = "Japan"
    SOUTH_KOREA = "South Korea"
    CHINA = "China"
    HONG_KONG = "Hong Kong"
    OTHER = "Other"


JURISDICTION_REGULATOR: dict[str, str] = {
    Jurisdiction.UNITED_STATES.value: "SEC EDGAR",
    Jurisdiction.JAPAN.value: "EDINET",
    Jurisdiction.SOUTH_KOREA.value: "DART",
    Jurisdiction.CHINA.value: "CNINFO / SSE / SZSE",
    Jurisdiction.HONG_KONG.value: "HKEXnews",
    Jurisdiction.OTHER.value: "Other / unspecified",
}


class SourceType(str, Enum):
    """Ordered roughly by authority; see guardrails.source_hierarchy for the
    canonical numeric ranking used in conflict resolution. "Regulatory
    Filing" is deliberately jurisdiction-agnostic — it covers SEC EDGAR
    (US), EDINET (Japan), DART (Korea), and CNINFO/HKEXnews (China/Hong
    Kong) alike; which regulator applies is determined by the ticker's
    Jurisdiction, not by the source type itself."""

    SEC_FILING = "Regulatory Filing"
    EARNINGS_RELEASE = "Earnings Release"
    TRANSCRIPT = "Earnings Call Transcript"
    INVESTOR_PRESENTATION = "Investor Presentation"
    IR_PAGE = "Investor Relations Page"
    PRESS_RELEASE = "Press Release"
    INSIDER_FILING = "Insider/Ownership Filing"
    OWNERSHIP_DATA = "Ownership Data"
    NEWS = "Reputable Financial News"
    SOCIAL_MEDIA = "Social Media (unverified lead)"


class BottomLine(str, Enum):
    BULLISH_SETUP = "Bullish setup"
    BEARISH_SETUP = "Bearish setup"
    MIXED_SETUP = "Mixed setup"
    INSUFFICIENT_EVIDENCE = "Insufficient evidence"


class ConfidenceLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class AlertStatus(str, Enum):
    OPEN = "open"
    REVIEWED = "reviewed"
    SNOOZED = "snoozed"
    ARCHIVED = "archived"


@dataclass
class Ticker:
    ticker: str
    company_name: str
    sector: str
    subtheme: str
    market_cap_category: str
    jurisdiction: str = "United States"
    is_mock: bool = True
    id: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class WatchlistRecord:
    ticker: str
    tier: Tier
    thesis_short: str
    why_on_watchlist: str
    conviction_score: int
    evidence_status: EvidenceStatus
    next_catalyst: Optional[str] = None
    next_catalyst_date: Optional[str] = None
    key_confirmation_metric: Optional[str] = None
    key_invalidation_metric: Optional[str] = None
    latest_material_change: Optional[str] = None
    risk_flags: str = ""  # comma-separated short flags, derived from latest scorecard
    date_added: Optional[str] = None
    date_last_reviewed: Optional[str] = None
    is_active: bool = True
    id: Optional[int] = None


@dataclass
class Source:
    ticker: str
    source_type: SourceType
    title: str
    url_or_identifier: str
    source_date: str  # ISO date the underlying document was published/filed
    retrieval_date: str  # ISO date we retrieved/ingested it
    authority_rank: int
    id: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class SourceExcerpt:
    source_id: int
    excerpt_text: str
    tag: str  # bullish | bearish | neutral | risk | demand | margin | guidance | insider | ...
    id: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class Catalyst:
    ticker: str
    description: str
    catalyst_date: str
    status: str = "upcoming"
    id: Optional[int] = None


@dataclass
class ScoreComponent:
    scorecard_id: int
    component_key: str
    label: str
    weight: float
    raw_score: int  # 1-5, 5 = most favorable
    explanation: str
    citation_source_ids: list[int] = field(default_factory=list)
    id: Optional[int] = None

    @property
    def weighted_score(self) -> float:
        return round(self.weight * self.raw_score, 4)


@dataclass
class Scorecard:
    ticker: str
    total_score: float
    is_capped: bool
    cap_reason: Optional[str]
    brief_id: Optional[int] = None
    id: Optional[int] = None
    created_at: Optional[str] = None
    components: list[ScoreComponent] = field(default_factory=list)


@dataclass
class ResearchBrief:
    ticker: str
    question: str
    version: int
    bottom_line: BottomLine
    confidence_level: ConfidenceLevel
    confidence_explanation: str
    sections_json: str  # full structured section payload, JSON-encoded
    id: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class ResearchSnapshot:
    ticker: str
    brief_id: int
    snapshot_json: str  # normalized extracted-facts payload used for diffing
    id: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class Alert:
    rule_type: str
    message: str
    severity: str
    ticker: Optional[str] = None
    status: AlertStatus = AlertStatus.OPEN
    snooze_until: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Note:
    ticker: str
    note_text: str
    tags: str = ""
    id: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class AuditLogEntry:
    event_type: str
    payload_json: str
    ticker: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None
