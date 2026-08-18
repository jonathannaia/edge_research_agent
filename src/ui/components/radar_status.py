"""Radar Inbox status vocabulary — deliberately distinct wording and
visual language from the curated Signal Board (badges.py's direction
tags). A Radar item is a filing-driven research lead, not a completed
market read, and must never look like one (user's explicit instruction).

RadarItem wraps either a bare FilingEvent the rule engine looked at and
did not flag ("New filing" — no CandidateSignal exists for it at all) or
a CandidateSignal at any point in its lifecycle. Status label/bucket
mapping lives here, in one place, so the page, the card, and the filters
all agree on the same vocabulary.
"""
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from src.models.models import CandidateSignal, CandidateStatus, ExtractionState, FilingEvent, TranslationState


@dataclass(frozen=True)
class RadarItem:
    filing: FilingEvent
    candidate: CandidateSignal | None

    @property
    def is_new_filing(self) -> bool:
        return self.candidate is None


# Deliberately different words from anything badges.py/cards.py uses for
# curated Signals — "Candidate signal" and "New filing" are Radar-only
# vocabulary, never "Signal" alone.
_STATUS_LABEL_OVERRIDES = {
    CandidateStatus.CANDIDATE_DETECTED: "Candidate signal",
    # Radar Calibration milestone — the ownership-materiality gate's own
    # low-emphasis label, shown directly as the status pill for routine
    # ownership updates it filtered out of Needs review.
    CandidateStatus.NOT_MATERIAL: "Not material · routine ownership update",
}

_STATUS_BUCKET = {
    CandidateStatus.CANDIDATE_DETECTED: "info",
    CandidateStatus.QUEUED_FOR_PROCESSING: "info",
    CandidateStatus.RETRIEVAL_IN_PROGRESS: "info",
    CandidateStatus.EXTRACTION_PENDING: "info",
    CandidateStatus.EXTRACTED: "info",
    CandidateStatus.TRANSLATION_PENDING: "info",
    CandidateStatus.TRANSLATED: "info",
    CandidateStatus.NEEDS_REVIEW: "mix",
    CandidateStatus.PROCESSING_DEFERRED: "neutral",
    CandidateStatus.PARSE_FAILED: "neg",
    CandidateStatus.RETRIEVAL_FAILED: "neg",
    CandidateStatus.TRANSLATION_UNAVAILABLE: "neg",
    CandidateStatus.PUBLISHED: "pos",
    CandidateStatus.DISMISSED: "neutral",
    CandidateStatus.NOT_MATERIAL: "neutral",
}


def status_label(item: RadarItem) -> str:
    if item.is_new_filing:
        return "New filing"
    status = item.candidate.status
    return _STATUS_LABEL_OVERRIDES.get(status, status.value)


def status_bucket(item: RadarItem) -> str:
    if item.is_new_filing:
        return "neutral"
    return _STATUS_BUCKET.get(item.candidate.status, "neutral")


def status_pill_html(item: RadarItem) -> str:
    return f'<span class="er-status-tag er-tag-{status_bucket(item)}">{status_label(item)}</span>'


def status_pill(item: RadarItem) -> None:
    st.markdown(status_pill_html(item), unsafe_allow_html=True)


def translation_unavailable_tag_html(item: RadarItem) -> str | None:
    """A separate small tag for the one reachable case the brief's
    "Translation unavailable" bucket actually maps to: a NEEDS_REVIEW
    candidate whose excerpt translation failed (see retry_policy.py's
    module docstring for why this isn't a CandidateStatus value)."""
    if item.candidate is not None and item.candidate.translation_state == TranslationState.UNAVAILABLE:
        return '<span class="er-status-tag er-tag-neg">Translation unavailable</span>'
    return None


# --- Evidence-status panel label mapping (Radar Inbox "Evidence status"
# section) — plain-language, source-neutral labels, kept alongside the
# existing status vocabulary above rather than inlined in radar_card.py.
# Every mapping is deliberately explicit (not derived from `.value`) so
# raw enum wording never reaches this user-facing panel; the existing,
# separate "Details" technical rows in radar_card.py still show the raw
# `.value` strings unchanged, for anyone who wants them.

_EXTRACTION_STATE_EVIDENCE_LABELS: dict[ExtractionState, str] = {
    ExtractionState.EXTRACTED: "Native text extracted",
    ExtractionState.NOT_FETCHED: "Document not fetched",
    ExtractionState.PENDING: "Native text processing",
    ExtractionState.UNSUPPORTED_FORMAT: "Unsupported document format",
    ExtractionState.PARSE_FAILED: "Native text unavailable",
    ExtractionState.RETRIEVAL_FAILED: "Document retrieval failed",
}

_TRANSLATION_STATE_EVIDENCE_LABELS: dict[TranslationState, str] = {
    TranslationState.NOT_REQUESTED: "Not requested",
    TranslationState.PENDING: "Translation processing",
    TranslationState.TRANSLATED: "English translation available",
    TranslationState.UNAVAILABLE: "Translation unavailable",
}

# Keyed on the real FilingEvent.source_name values each source's own
# scan_service sets — "OpenDART / DART", "SEC EDGAR", "EDINET" (see each
# source's scan_service.py). Any other/future source falls back to the
# generic "Document ID" rather than guessing a label.
_SOURCE_DOCUMENT_ID_LABELS: dict[str, str] = {
    "OpenDART / DART": "DART receipt number",
    "SEC EDGAR": "SEC accession number",
    "EDINET": "EDINET document ID",
}


def evidence_source_link_label(filing: FilingEvent) -> str:
    return "Linked source" if filing.source_url else "No source link"


def evidence_native_text_label(extraction_state: ExtractionState) -> str:
    return _EXTRACTION_STATE_EVIDENCE_LABELS.get(extraction_state, extraction_state.value)


def evidence_translation_label(translation_state: TranslationState) -> str:
    return _TRANSLATION_STATE_EVIDENCE_LABELS.get(translation_state, translation_state.value)


def evidence_review_label(candidate: CandidateSignal) -> str:
    if candidate.status == CandidateStatus.NEEDS_REVIEW:
        return "Manual review needed"
    if candidate.reviewed_at:
        return "Reviewed"
    return "Not yet reviewed"


def evidence_document_id_label(source_name: str) -> str:
    return _SOURCE_DOCUMENT_ID_LABELS.get(source_name, "Document ID")
