"""Primary-source authority ranking (guardrail principle #2).

Lower rank number = higher authority. Used to (a) stamp a numeric
authority_rank on every Source row at ingestion time and (b) resolve
conflicts between excerpts that disagree.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.models.models import SourceType

AUTHORITY_RANK: dict[SourceType, int] = {
    SourceType.SEC_FILING: 1,
    SourceType.EARNINGS_RELEASE: 2,
    SourceType.TRANSCRIPT: 2,
    SourceType.INVESTOR_PRESENTATION: 2,
    SourceType.IR_PAGE: 3,
    SourceType.PRESS_RELEASE: 3,
    SourceType.INSIDER_FILING: 1,
    SourceType.OWNERSHIP_DATA: 3,
    SourceType.NEWS: 4,
    SourceType.SOCIAL_MEDIA: 5,
}

AUTHORITY_LABELS: dict[int, str] = {
    1: "Regulatory & insider filings — SEC EDGAR (US), EDINET (Japan), DART (Korea), "
       "CNINFO/HKEXnews (China/Hong Kong) — highest authority",
    2: "Earnings releases, transcripts, investor presentations",
    3: "Company IR pages, press releases, ownership data",
    4: "Reputable financial reporting / research",
    5: "Social media (unverified lead only — never treated as evidence)",
}


def authority_rank(source_type: SourceType | str) -> int:
    if isinstance(source_type, str):
        try:
            source_type = SourceType(source_type)
        except ValueError:
            return 5
    return AUTHORITY_RANK.get(source_type, 5)


@dataclass
class ExcerptRef:
    source_id: int
    source_type: str
    source_date: str
    tag: str
    excerpt_text: str


def resolve_conflict(excerpts: list[ExcerptRef]) -> tuple[ExcerptRef, str]:
    """Given excerpts that disagree (mixed bullish/bearish tags on the same
    topic), pick the one to weight most heavily: higher authority first,
    then more recent. Returns (winning_excerpt, explanation)."""
    if not excerpts:
        raise ValueError("resolve_conflict requires at least one excerpt")

    ranked = sorted(
        excerpts,
        key=lambda e: (authority_rank(e.source_type), -_date_ordinal(e.source_date)),
    )
    winner = ranked[0]
    tags = {e.tag for e in excerpts}
    if len(tags) <= 1:
        explanation = "Sources agree; no conflict to resolve."
    else:
        explanation = (
            f"Sources disagree ({', '.join(sorted(tags))}). Weighted toward "
            f"{winner.source_type} dated {winner.source_date} as the higher-authority "
            "and/or more recent source. Both sides are shown in the brief — see "
            "'Contradictions and uncertainty'."
        )
    return winner, explanation


def _date_ordinal(date_str: str) -> int:
    try:
        return datetime.fromisoformat(date_str).date().toordinal()
    except ValueError:
        return date.min.toordinal()
