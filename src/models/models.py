"""Typed data model for EevaResearch AI's foundation build.

Every model that carries a claim about the world (a Ticker's thesis, a
Signal's interpretation, a ResearchClaim, a ChatAnswer) is either a
ClaimType-tagged claim itself or backed by EvidenceItem(s) — the same
"every claim ties to something" principle the app is built around, applied
structurally rather than left to convention.

Phase 1 is demo-data-only: every EvidenceItem in this build has
is_demo=True, source_name="EevaResearch Demo Data", and no source_url. The
fields exist now (source_type, retrieved_at, freshness_label, ticker_symbol,
theme_slug) so a real evidence pipeline can populate them later without a
schema migration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ClaimType(str, Enum):
    """The four categories EevaResearch distinguishes for every claim it
    surfaces — see Methodology page. Not optional decoration: every UI
    surface showing a claim must show which of these it is."""

    FACT = "Fact"
    INTERPRETATION = "Interpretation"
    INFERENCE = "Inference"
    UNCERTAINTY = "Uncertainty"


class Exposure(str, Enum):
    PRIMARY = "Primary"
    SECONDARY = "Secondary"


class Direction(str, Enum):
    IMPROVING = "Improving"
    WEAKENING = "Weakening"
    EMERGING = "Emerging"
    MIXED = "Mixed"


class Strength(str, Enum):
    WEAK = "Weak"
    MODERATE = "Moderate"
    STRONG = "Strong"


class Horizon(str, Enum):
    INTRADAY = "Intraday"
    SWING = "Swing"
    MULTI_WEEK = "Multi-week"
    MULTI_QUARTER = "Multi-quarter"


FRESHNESS_FRESH_DAYS = 3
FRESHNESS_AGING_DAYS = 10


@dataclass
class EvidenceItem:
    """One piece of evidence backing a claim. In this phase, always demo
    data: source_name is always "EevaResearch Demo Data", source_url is
    always None (no external link presented as real), is_demo is always
    True. freshness_label is derived from retrieved_at, not stored, so it's
    always correct relative to "now" rather than going stale itself."""

    id: str
    title: str
    source_name: str
    source_type: str  # e.g. "Demo Dataset" in phase 1
    published_at: str  # ISO 8601
    retrieved_at: str  # ISO 8601
    excerpt: str
    claim_type: ClaimType
    source_url: str | None = None
    is_demo: bool = True
    ticker_symbol: str | None = None
    theme_slug: str | None = None
    # Original-language text for non-English source excerpts, rendered
    # above the (English) `excerpt` translation per brief §7. None for
    # English-language sources. document_location is the in-document
    # pointer (e.g. "p.7") shown in the excerpt's <cite> line.
    excerpt_original: str | None = None
    document_location: str = ""

    @property
    def freshness_label(self) -> str:
        try:
            retrieved = datetime.fromisoformat(self.retrieved_at)
            if retrieved.tzinfo is None:
                retrieved = retrieved.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return "Unknown"
        age_days = (datetime.now(timezone.utc) - retrieved).total_seconds() / 86400
        if age_days <= FRESHNESS_FRESH_DAYS:
            return "Fresh"
        if age_days <= FRESHNESS_AGING_DAYS:
            return "Aging"
        return "Stale"


@dataclass
class ResearchClaim:
    text: str
    claim_type: ClaimType
    evidence: list[EvidenceItem] = field(default_factory=list)


@dataclass
class Subtheme:
    slug: str
    name: str
    description: str
    theme_slug: str


@dataclass
class Theme:
    slug: str
    name: str
    description: str
    subthemes: list[Subtheme] = field(default_factory=list)


@dataclass
class Ticker:
    """A ticker record. In phase 1 the only instance is the fictional DEMO
    company — theme pages otherwise show an empty state rather than any
    populated ticker table. is_demo=True on every record in this phase."""

    symbol: str
    company_name: str
    theme_slug: str
    subtheme_slug: str | None
    exposure: Exposure
    market_cap_bucket: str  # e.g. "Large", "Mid", "Small" — placeholder buckets
    liquidity_bucket: str  # e.g. "High", "Medium", "Low"
    technical_strength: str  # e.g. "Strong", "Neutral", "Weak" — placeholder, not computed
    risk_level: str  # e.g. "Low", "Medium", "High"
    thesis: str
    market_expectation: str = ""
    underappreciated: str = ""
    bull_factors: list[str] = field(default_factory=list)
    base_factors: list[str] = field(default_factory=list)
    bear_factors: list[str] = field(default_factory=list)
    key_risks: list[str] = field(default_factory=list)
    what_would_change_thesis: str = ""
    is_demo: bool = True


@dataclass
class Catalyst:
    id: str
    title: str
    date: str  # ISO 8601 date
    catalyst_type: str  # e.g. "Earnings", "Product Launch", "Regulatory", "Industry Event"
    description: str
    theme_slug: str
    ticker_symbol: str | None = None
    is_demo: bool = True


@dataclass
class Signal:
    id: str
    title: str
    theme_slug: str
    subtheme_slug: str | None
    direction: Direction
    strength: Strength
    horizon: Horizon
    evidence_count: int
    interpretation: str
    contrary_evidence: str
    validation_criteria: str
    invalidation_criteria: str
    related_tickers: list[str]
    last_updated: str  # ISO 8601
    is_demo: bool = True


@dataclass
class CapitalRotationMetric:
    theme_slug: str
    relative_performance_pct: float  # vs. broad-market placeholder benchmark
    breadth_pct: float  # % of theme's tickers showing positive momentum, placeholder
    leaders: list[str]
    laggards: list[str]
    as_of: str  # ISO 8601
    is_demo: bool = True


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant"
    content: str
    created_at: str


@dataclass
class ChatAnswer:
    question: str
    what_happened: str
    why_it_matters: str
    underappreciated: str
    risks: str
    what_to_watch: str
    sources: list[EvidenceItem]
    confidence: Strength
    freshness: str
    claim_type: ClaimType = ClaimType.INTERPRETATION
    is_demo: bool = True
    # Per-claim breakdown for the evidence-spine rendering (brief §7) — each
    # claim carries its own ClaimType, distinct from the single summary
    # claim_type above. Empty for answers that predate this (e.g. the
    # generic fallback), which render as plain text instead.
    claims: list[ResearchClaim] = field(default_factory=list)


@dataclass
class WatchlistEntry:
    list_name: str
    ticker_symbol: str
    added_at: str
    note: str = ""
    invalidates_if: str = ""
