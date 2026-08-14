"""Normalized, already-cited evidence bundle that scoring functions consume.

src.services.research_service is responsible for building a ResearchContext:
it fetches from providers, persists each piece as a Source (+ SourceExcerpt
where applicable), and records the resulting source_id here. Every field in
this object is therefore already traceable to a citation — scoring never
sees raw provider data, only cited evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.providers.base import (
    FundamentalsSnapshot,
    InsiderTransaction,
    OwnershipSummary,
    PriceContext,
    ValuationContext,
)


@dataclass
class EvidenceItem:
    text: str
    tag: str  # demand | margin | risk | bullish | bearish | dilution | product_cycle | neutral | insider | ...
    source_id: int
    source_type: str
    source_date: str


@dataclass
class ResearchContext:
    ticker: str
    fundamentals: Optional[FundamentalsSnapshot] = None
    fundamentals_source_id: Optional[int] = None
    evidence: list[EvidenceItem] = field(default_factory=list)
    insider_txns: list[InsiderTransaction] = field(default_factory=list)
    insider_source_ids: list[int] = field(default_factory=list)
    ownership: Optional[OwnershipSummary] = None
    ownership_source_id: Optional[int] = None
    price: Optional[PriceContext] = None
    price_source_id: Optional[int] = None
    valuation: Optional[ValuationContext] = None
    valuation_source_id: Optional[int] = None
    next_earnings_date: Optional[str] = None
    earnings_source_id: Optional[int] = None
    all_source_dates: list[tuple[int, str]] = field(default_factory=list)

    def evidence_with_tag(self, *tags: str) -> list[EvidenceItem]:
        wanted = set(tags)
        return [e for e in self.evidence if e.tag in wanted]
