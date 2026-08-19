"""Promotes eligible real Radar candidates (DART/EDINET/EDGAR) into the
Signal model the Signals page renders — the "separate, human review step"
that CandidateSignal's own docstring names as distinct from detection.
Pure, no I/O: takes an already-loaded CandidateSignal, returns a bool or a
Signal.

Every judgment-shaped field below reuses the same deterministic,
hand-reviewed template logic already proven in
src/ui/components/analyst_view.py — one source of truth for "what does
this filing type mean," never a second, independently-invented copy.
`direction`/`horizon` have no analytical source anywhere on
CandidateSignal (this pilot never computes trend direction or a forecast
horizon), so both are fixed, conservative defaults rather than a guess:
EMERGING (a newly detected item, not yet trended) and MULTI_WEEK (a
neutral default) — same "never invent a judgment" discipline as
everywhere else in Radar."""
from __future__ import annotations

from src.models.models import (
    CandidateSignal,
    CandidateStatus,
    Direction,
    FilingEvent,
    Horizon,
    Signal,
    Strength,
)
from src.ui.components.analyst_view import (
    _FOLLOWUP_FALLBACK,
    _FOLLOWUP_TEMPLATES,
    _UNCONFIRMED_FALLBACK,
    _UNCONFIRMED_TEMPLATES,
    _DART_SOURCE,
    _matched_category,
    _why_entered_radar_phrases,
)

# Per the approved plan: only these two statuses promote a candidate to
# Signals. Every other status (including PROCESSING_DEFERRED and
# NOT_MATERIAL) is excluded by omission, not by name — an explicit
# allowlist rather than a denylist, so a future status added to
# CandidateStatus is excluded by default rather than silently included.
_ELIGIBLE_STATUSES = frozenset({CandidateStatus.EXTRACTED, CandidateStatus.NEEDS_REVIEW})

_STRENGTH_BY_CONFIDENCE = {"Low": Strength.WEAK, "Moderate": Strength.MODERATE, "High": Strength.STRONG}
_EDGAR_SOURCE = "SEC EDGAR"


def is_eligible_for_signal(candidate: CandidateSignal) -> bool:
    return candidate.status in _ELIGIBLE_STATUSES


def _title(candidate: CandidateSignal, filing: FilingEvent) -> str:
    """Prefer the machine translation when one exists (for readability on
    an English-first page), but fall back to the native title verbatim —
    never a paraphrase — matching the same translation-is-convenience-only
    discipline as analyst_view.py."""
    if candidate.title_translation is not None:
        return candidate.title_translation.translated_text
    return filing.report_nm


def _interpretation(candidate: CandidateSignal, filing: FilingEvent) -> str:
    """Reuses analyst_view.py's own "why this was flagged" phrase builder
    — a statement of which rule matched, never a market judgment."""
    phrases = _why_entered_radar_phrases(filing.source_name, candidate.matched_rules)
    if not phrases:
        return f"Flagged by Radar's rule-based detection on {filing.source_name}."
    return "; ".join(phrases)


def _validation_criteria(candidate: CandidateSignal, filing: FilingEvent) -> str:
    category = _matched_category(candidate.matched_rules)
    if filing.source_name == _DART_SOURCE and category == "market_rumor_response":
        items = _FOLLOWUP_TEMPLATES["market_rumor_response"]
    else:
        items = _FOLLOWUP_FALLBACK
    return "; ".join(items)


def _invalidation_criteria(candidate: CandidateSignal, filing: FilingEvent) -> str:
    category = _matched_category(candidate.matched_rules)
    if filing.source_name == _DART_SOURCE and category == "market_rumor_response":
        return _UNCONFIRMED_TEMPLATES["market_rumor_response"]
    return _UNCONFIRMED_FALLBACK


def _source_url(filing: FilingEvent) -> str:
    """For EDGAR only, prefer a direct link to the primary readable
    document over the bare accession-directory URL — using the exact
    same concatenation EdgarClient.fetch_document() already performs
    (source_url + primary_document; see src/data_access/edgar/client.py),
    never a guessed or scraped filename. Falls back to the stored
    source_url verbatim whenever primary_document is missing or
    source_url doesn't have the expected trailing-slash directory shape
    — no fabricated replacement. DART/EDINET are untouched: their
    FilingEvent.primary_document is always empty, so this is a no-op for
    both."""
    if filing.source_name == _EDGAR_SOURCE and filing.primary_document and filing.source_url.endswith("/"):
        return filing.source_url + filing.primary_document
    return filing.source_url


def candidate_to_signal(candidate: CandidateSignal) -> Signal:
    filing = candidate.filing
    last_updated = candidate.reviewed_at or (
        candidate.state_history[-1].at if candidate.state_history else filing.retrieved_at
    )
    return Signal(
        id=f"signal-{candidate.id}",
        title=_title(candidate, filing),
        theme_slug=filing.theme_slug,
        subtheme_slug=filing.subtheme_slug,
        direction=Direction.EMERGING,
        strength=_STRENGTH_BY_CONFIDENCE.get(candidate.confidence, Strength.MODERATE),
        horizon=Horizon.MULTI_WEEK,
        evidence_count=1,
        interpretation=_interpretation(candidate, filing),
        contrary_evidence="Not yet reviewed.",
        validation_criteria=_validation_criteria(candidate, filing),
        invalidation_criteria=_invalidation_criteria(candidate, filing),
        related_tickers=[filing.stock_code] if filing.stock_code else [],
        last_updated=last_updated,
        is_demo=False,
        issuer=filing.corp_name,
        source_name=filing.source_name,
        source_url=_source_url(filing),
        excerpt=candidate.excerpt_original,
    )
