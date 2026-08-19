"""Radar Inbox's per-item row + detail — a dense filing-review layout,
not a Signal-Board-style card. Deliberately reuses the app's existing
tokens/chip conventions (evidence_chips.py's dashed/outline treatment,
freshness.py's live/demo chip) rather than inventing a new visual system,
while keeping every label Radar-specific (radar_status.py) so a Radar
item is never mistaken for a curated, published Signal.
"""
from __future__ import annotations

from typing import Callable

import streamlit as st

from src.data_access.dart import dart_rules, retry_policy
from src.models.models import CandidateSignal, CandidateStatus, FilingEvent
from src.ui.components.radar_status import (
    RadarItem,
    evidence_document_id_label,
    evidence_native_text_label,
    evidence_review_label,
    evidence_source_link_label,
    evidence_translation_label,
    status_pill,
    translation_unavailable_tag_html,
)

_TRANSLATION_LABEL = "Machine translation · For convenience · Verify against the original-language source"

_PREPARE_ANALYST_VIEW_LABEL = "Prepare analyst view"
_RETRY_ANALYST_VIEW_LABEL = "Retry analyst view preparation"
_PREPARING_SPINNER_TEXT = "Preparing analyst view — retrieving and interpreting the filing…"
_ANALYST_VIEW_CAPTION = "When ready, the analyst-ready summary appears in this filing’s Details."
_UNAVAILABLE_REASON = "Preparation is unavailable until this source is configured."


def _why_flagged_phrases(matched_rules: list[str]) -> list[str]:
    """Parses matched-rule strings into short, human-readable phrases —
    presentation-only, no rule-engine logic here. Handles both real rule
    shapes in this app: DART's dart_rules.evaluate_report_name
    `category:rule_name:keyword` (3 parts, plus the bare
    "amendment_or_correction" marker) and EDGAR's edgar_rules
    `category:8-K item X.XX` / `category:FORM-TYPE` (2 parts)."""
    phrases: list[str] = []
    for rule in matched_rules:
        if rule == "amendment_or_correction":
            phrases.append("Amends or corrects an earlier filing")
            continue
        parts = rule.split(":", 2)
        if len(parts) == 3:
            category, _rule_name, keyword = parts
            label = category.replace("_", " ").capitalize()
            phrases.append(f"{label} keyword match ({keyword})")
        elif len(parts) == 2:
            category, detail = parts
            label = category.replace("_", " ").capitalize()
            phrases.append(f"{label} ({detail})")
        else:
            phrases.append(rule)
    return phrases


def _detail_row(label: str, value: str) -> None:
    st.markdown(
        f'<div class="er-muted" style="margin-top:0.15rem;"><strong>{label}:</strong> {value}</div>',
        unsafe_allow_html=True,
    )


def _evidence_status_panel(filing: FilingEvent, candidate: CandidateSignal | None) -> None:
    """Compact, honest, source-neutral evidence summary — plain-language
    labels only (see radar_status.py's evidence_* helpers), never a raw
    enum `.value`. Shown for every item, with or without a CandidateSignal
    yet; the existing raw technical rows further below are untouched and
    still show `.value` strings for anyone who wants them."""
    st.markdown('<div class="er-muted" style="margin-top:0.2rem;"><strong>Evidence status</strong></div>', unsafe_allow_html=True)
    _detail_row("Original document", evidence_source_link_label(filing))
    if candidate is not None:
        _detail_row("Native text", evidence_native_text_label(candidate.extraction_state))
        _detail_row("Translation", evidence_translation_label(candidate.translation_state))
        _detail_row("Review", evidence_review_label(candidate))
    else:
        # A bare FilingEvent has no extraction/translation/candidate-status
        # data to show — never fabricate one. The exact copy below is the
        # honest, source-neutral answer to "what about translation?" for a
        # filing no candidate pipeline has touched yet.
        _detail_row("Document processing", "Not started")
        _detail_row("Translation", "Available after document processing")
    _detail_row(evidence_document_id_label(filing.source_name), filing.rcept_no)


def _render_process_action(candidate_id: str, label: str, key: str, ready: bool, on_process: Callable[[str], None]) -> None:
    """Renders the one "Prepare analyst view" / "Retry analyst view
    preparation" button — the seam that used to click and appear to do
    nothing (no visible spinner during the synchronous retrieval/
    extraction/translation call, which can legitimately take a long
    time). Now: a visible spinner covers the call, a disabled state with
    an honest, non-secret reason covers the "this source isn't
    configured" case (readiness is checked here, not inferred), and a
    narrow except-Exception guards only against a truly unexpected
    failure outside the pipeline's own typed retrieval/parse/translation
    failure states — those are already caught and persisted as a
    CandidateStatus inside the pipeline itself and must reach the UI
    unchanged; this is defense-in-depth only, same pattern as the Scan
    buttons' own try/except in radar_inbox.py."""
    if not ready:
        st.button(label, key=key, use_container_width=True, disabled=True)
        st.markdown(f'<div class="er-muted" style="margin-top:0.2rem; font-size:0.78rem;">{_UNAVAILABLE_REASON}</div>', unsafe_allow_html=True)
        return

    error_key = f"radar-process-error-{candidate_id}"
    if st.button(label, key=key, use_container_width=True):
        st.session_state.pop(error_key, None)
        with st.spinner(_PREPARING_SPINNER_TEXT):
            try:
                on_process(candidate_id)
            except Exception:  # noqa: BLE001 — defense-in-depth only; see docstring above
                st.session_state[error_key] = "Preparing the analyst view failed unexpectedly — see server logs for detail."
    if st.session_state.get(error_key):
        st.markdown(f'<div class="er-muted" style="margin-top:0.2rem; font-size:0.78rem;">{st.session_state[error_key]}</div>', unsafe_allow_html=True)


def candidate_row(
    item: RadarItem, on_process: Callable[[str], None] | None = None, process_ready: bool = True,
) -> None:
    filing = item.filing
    candidate = item.candidate

    with st.container(border=True, key=f"radar-item-{filing.rcept_no}"):
        top_cols = st.columns([3, 3, 2, 2], vertical_alignment="center")
        with top_cols[0]:
            status_pill(item)
        with top_cols[1]:
            st.markdown(f'<div class="er-muted">{filing.corp_name} · {filing.stock_code}</div>', unsafe_allow_html=True)
        with top_cols[2]:
            st.markdown(f'<div class="er-muted">{filing.source_name}</div>', unsafe_allow_html=True)
        with top_cols[3]:
            st.markdown(f'<div class="er-muted" style="text-align:right;">{filing.rcept_dt} · {filing.original_language}</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="er-card-title" style="margin-top:0.4rem;">{filing.report_nm}</div>', unsafe_allow_html=True)

        if candidate is not None and candidate.title_translation is not None:
            st.markdown(f'<div style="margin-top:0.2rem;">{candidate.title_translation.translated_text}</div>', unsafe_allow_html=True)
            st.markdown(f'<span class="er-chip er-chip-inference">{_TRANSLATION_LABEL}</span>', unsafe_allow_html=True)

        theme_label = filing.theme_slug.replace("-", " ").title() if filing.theme_slug else ""
        if theme_label:
            st.markdown(f'<div class="er-muted" style="margin-top:0.3rem;">{theme_label}</div>', unsafe_allow_html=True)

        if filing.source_name == "EDINET":
            # Gate 8.1: shown unconditionally (not gated behind
            # `candidate is not None` like the "Details" expander below)
            # because an EDINET FilingEvent realistically never has a
            # candidate while the category map stays empty — gating this
            # behind a candidate would mean it never renders in practice.
            # "—" means the code was genuinely absent on the source
            # record; any other value is shown verbatim, exactly as
            # received, never interpreted.
            with st.expander("EDINET form codes"):
                _detail_row("Ordinance code", filing.ordinance_code or "—")
                _detail_row("Form code", filing.pblntf_ty or "—")
                _detail_row("Document type code", filing.pblntf_detail_ty or "—")

        if candidate is not None:
            st.markdown(
                f'<div class="er-muted" style="margin-top:0.2rem;">{dart_rules.format_confidence_label(candidate.confidence)}</div>',
                unsafe_allow_html=True,
            )
            phrases = _why_flagged_phrases(candidate.matched_rules)
            if phrases:
                st.markdown('<div class="er-muted" style="margin-top:0.2rem;"><strong>Why flagged:</strong></div>', unsafe_allow_html=True)
                for phrase in phrases:
                    st.markdown(f'<div class="er-muted" style="margin-left:0.8rem;">• {phrase}</div>', unsafe_allow_html=True)

            if candidate.materiality_assessment != "Not assessed":
                st.markdown(
                    f'<div class="er-muted" style="margin-top:0.2rem;">Potential materiality: {candidate.materiality_assessment}</div>',
                    unsafe_allow_html=True,
                )

            unavailable_tag = translation_unavailable_tag_html(item)
            if unavailable_tag:
                st.markdown(unavailable_tag, unsafe_allow_html=True)

        action_cols = st.columns([2, 2, 4])
        with action_cols[0]:
            st.link_button(f"Open original {filing.source_name} filing ↗", filing.source_url, use_container_width=True)

        if candidate is not None and on_process is not None:
            with action_cols[1]:
                if candidate.status == CandidateStatus.PROCESSING_DEFERRED:
                    _render_process_action(
                        candidate.id, _PREPARE_ANALYST_VIEW_LABEL, f"process-{candidate.id}", process_ready, on_process,
                    )
                    st.markdown(f'<div class="er-muted" style="margin-top:0.2rem; font-size:0.78rem;">{_ANALYST_VIEW_CAPTION}</div>', unsafe_allow_html=True)
                elif retry_policy.is_retryable(candidate):
                    eligibility = retry_policy.retry_eligibility(candidate)
                    if eligibility.eligible:
                        _render_process_action(
                            candidate.id, _RETRY_ANALYST_VIEW_LABEL, f"retry-{candidate.id}", process_ready, on_process,
                        )
                        st.markdown(f'<div class="er-muted" style="margin-top:0.2rem; font-size:0.78rem;">{_ANALYST_VIEW_CAPTION}</div>', unsafe_allow_html=True)
                    elif eligibility.reason == "Retry limit reached":
                        st.button(
                            "Retry limit reached · Review original filing", key=f"retry-{candidate.id}",
                            disabled=True, use_container_width=True,
                        )
                    else:
                        st.button(
                            f"Retry available in {eligibility.cooldown_remaining_seconds}s",
                            key=f"retry-{candidate.id}", disabled=True, use_container_width=True,
                        )

        if candidate is not None:
            with st.expander("Details"):
                _evidence_status_panel(filing, candidate)
                st.markdown('<div class="er-muted" style="margin-top:0.6rem;"><strong>Technical detail</strong></div>', unsafe_allow_html=True)
                _detail_row(evidence_document_id_label(filing.source_name), filing.rcept_no)
                _detail_row("Filer", filing.flr_nm)
                _detail_row("Filed", filing.rcept_dt)
                _detail_row("Retrieved", filing.retrieved_at)
                _detail_row("Extraction state", candidate.extraction_state.value)
                _detail_row("Translation state", candidate.translation_state.value)
                _detail_row("Excerpt quality", candidate.excerpt_quality.value)
                if candidate.excerpt_original:
                    st.markdown('<div class="er-muted" style="margin-top:0.4rem;"><strong>Original-language excerpt</strong></div>', unsafe_allow_html=True)
                    st.markdown(f'<div>{candidate.excerpt_original}</div>', unsafe_allow_html=True)
                if candidate.excerpt_translation is not None:
                    st.markdown('<div class="er-muted" style="margin-top:0.4rem;"><strong>English translation</strong></div>', unsafe_allow_html=True)
                    st.markdown(f'<div>{candidate.excerpt_translation.translated_text}</div>', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="er-muted" style="margin-top:0.2rem;">'
                        f'{candidate.excerpt_translation.provider} · English translation · translated at {candidate.excerpt_translation.translated_at}</div>',
                        unsafe_allow_html=True,
                    )
                if candidate.state_history:
                    st.markdown('<div class="er-muted" style="margin-top:0.4rem;"><strong>State history</strong></div>', unsafe_allow_html=True)
                    for transition in candidate.state_history:
                        detail = f" — {transition.detail}" if transition.detail else ""
                        st.markdown(
                            f'<div class="er-muted" style="margin-left:0.8rem;">{transition.at} · {transition.status.value}{detail}</div>',
                            unsafe_allow_html=True,
                        )
        else:
            with st.expander("Details"):
                _evidence_status_panel(filing, None)
