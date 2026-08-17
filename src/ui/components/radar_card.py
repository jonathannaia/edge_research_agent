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
from src.models.models import CandidateStatus
from src.ui.components.radar_status import RadarItem, status_pill, translation_unavailable_tag_html

_TRANSLATION_LABEL = "Machine translation · For convenience · Verify against original Korean"


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


def candidate_row(item: RadarItem, on_process: Callable[[str], None] | None = None) -> None:
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
                    if st.button("Process now", key=f"process-{candidate.id}", use_container_width=True):
                        on_process(candidate.id)
                elif retry_policy.is_retryable(candidate):
                    eligibility = retry_policy.retry_eligibility(candidate)
                    if eligibility.eligible:
                        if st.button("Retry processing", key=f"retry-{candidate.id}", use_container_width=True):
                            on_process(candidate.id)
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
            is_dart = filing.source_name == "OpenDART / DART"
            with st.expander("Details"):
                _detail_row("DART receipt number" if is_dart else "SEC accession number", filing.rcept_no)
                _detail_row("Filer", filing.flr_nm)
                _detail_row("Filed", filing.rcept_dt)
                _detail_row("Retrieved", filing.retrieved_at)
                _detail_row("Extraction state", candidate.extraction_state.value)
                _detail_row("Translation state", candidate.translation_state.value)
                _detail_row("Excerpt quality", candidate.excerpt_quality.value)
                if candidate.excerpt_original:
                    excerpt_label = "Korean original excerpt" if is_dart else "Original excerpt (English)"
                    st.markdown(f'<div class="er-muted" style="margin-top:0.4rem;"><strong>{excerpt_label}</strong></div>', unsafe_allow_html=True)
                    st.markdown(f'<div>{candidate.excerpt_original}</div>', unsafe_allow_html=True)
                if candidate.excerpt_translation is not None:
                    st.markdown('<div class="er-muted" style="margin-top:0.4rem;"><strong>English translation</strong></div>', unsafe_allow_html=True)
                    st.markdown(f'<div>{candidate.excerpt_translation.translated_text}</div>', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="er-muted" style="margin-top:0.2rem;">'
                        f'{candidate.excerpt_translation.provider} · Korean → English · translated at {candidate.excerpt_translation.translated_at}</div>',
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
