"""Analyst view — the first structured, human-readable section inside a
processed Radar candidate's "Details," built on the real DART/SK Hynix
processed filing that proved the underlying pipeline works (see
design/DECISIONS.md). Every sentence here is either copied verbatim from
a structured FilingEvent field or selected from a small, hand-reviewed
template table keyed by the candidate's own matched category — never
generated, never a guess, never a market judgment, price target, rating,
or action recommendation. Reuses this app's existing Fact/Interpretation/
Inference/Uncertainty vocabulary (evidence_chips.py) rather than inventing
a new one.

Deliberately renders only when there is real extracted text to reason
about (`should_render_analyst_view`) — a deferred, failed, or
not-yet-processed candidate gets none of this, same "never fabricate
what wasn't actually retrieved" discipline as the rest of Radar Inbox.
"""
from __future__ import annotations

import streamlit as st

from src.models.models import CandidateSignal, ClaimType, ExtractionState, FilingEvent, TranslationState
from src.ui.components.evidence_chips import evidence_chip_html

_DART_SOURCE = "OpenDART / DART"
_EDINET_SOURCE = "EDINET"

# --- "What is unconfirmed" — deterministic, per-category, hand-reviewed.
# Only one real category has a specific template so far (the one this was
# built against — a real DART market_rumor_response filing). Every other
# category, from any source, gets the same honest fallback rather than a
# guessed template.
_UNCONFIRMED_TEMPLATES: dict[str, str] = {
    "market_rumor_response": (
        "This filing is a disclosure inquiry or response about reported information. "
        "It does not confirm that a transaction has occurred."
    ),
}
_UNCONFIRMED_FALLBACK = (
    "This filing type has no specific uncertainty template yet. "
    "Read the source excerpt directly before drawing conclusions."
)

# --- "Follow-up evidence to watch" — deterministic checklist only, no
# AI-generated synthesis or predictions. Every item names a piece of
# evidence that could later confirm/clarify the filing, never an action.
_FOLLOWUP_TEMPLATES: dict[str, list[str]] = {
    "market_rumor_response": [
        "A formal company response or clarification",
        "A subsequent filing that confirms or denies the reported matter",
        "An amendment or related disclosure",
    ],
}
_FOLLOWUP_FALLBACK: list[str] = [
    "Review subsequent company filings or official statements related to this disclosure.",
]


def should_render_analyst_view(candidate: CandidateSignal) -> bool:
    """The only gate: real extracted text must exist. Deliberately not
    gated on translation, review, or materiality — a Korean-only excerpt
    with no translation yet is still real source text worth structuring."""
    return candidate.extraction_state == ExtractionState.EXTRACTED and bool(candidate.excerpt_original)


def _matched_category(matched_rules: list[str]) -> str | None:
    """The first real (non-amendment-marker) matched category — matching
    the same category a candidate's confidence score was actually
    computed from. `amendment_or_correction` is a modifier, not a
    category of its own (see dart_rules.py), so it's skipped here."""
    for rule in matched_rules:
        if rule == "amendment_or_correction":
            continue
        return rule.split(":", 1)[0]
    return None


def _category_label(category: str) -> str:
    return category.replace("_", " ").capitalize()


def _why_entered_radar_phrases(source_name: str, matched_rules: list[str]) -> list[str]:
    """Source-aware on purpose: DART/EDGAR's matched_rules entries name a
    real native/documented *keyword or item number* (see
    dart_rules.py/edgar_rules.py) — "keyword match" is an accurate
    description there. EDINET's entries name a *routing code triplet*
    (ordinanceCode:formCode:docTypeCode — see edinet_rules.py), never a
    keyword — calling that a "keyword match" would misrepresent what was
    actually matched, so EDINET gets its own, honestly-worded phrasing."""
    if source_name == _EDINET_SOURCE:
        phrases: list[str] = []
        for rule in matched_rules:
            parts = rule.split(":", 1)
            if len(parts) == 2:
                category, code = parts
                phrases.append(f"{_category_label(category)} — matched by filing type/form code ({code})")
            else:
                phrases.append(rule)
        return phrases

    phrases = []
    for rule in matched_rules:
        if rule == "amendment_or_correction":
            phrases.append("Amends or corrects an earlier filing")
            continue
        parts = rule.split(":", 2)
        if len(parts) == 3:
            category, _rule_name, keyword = parts
            phrases.append(f"{_category_label(category)} — matched keyword “{keyword}”")
        elif len(parts) == 2:
            category, detail = parts
            phrases.append(f"{_category_label(category)} ({detail})")
        else:
            phrases.append(rule)
    return phrases


def _source_facts_html(filing: FilingEvent) -> str:
    """Deterministic and source-grounded only: company name, the filing's
    own title (quoted verbatim, never paraphrased), source, and filed
    date — every one a structured FilingEvent field, never a value parsed
    out of unstructured excerpt text. No amount, counterparty, or date is
    ever inferred from free text here."""
    return f"{filing.corp_name} filed “{filing.report_nm}” with {filing.source_name} on {filing.rcept_dt}."


def render_analyst_view(filing: FilingEvent, candidate: CandidateSignal) -> None:
    if not should_render_analyst_view(candidate):
        return

    st.markdown('<div class="er-muted" style="margin-top:0.6rem;"><strong>Analyst view</strong></div>', unsafe_allow_html=True)

    # 1. Source facts
    st.markdown('<div class="er-muted" style="margin-top:0.4rem;"><strong>Source facts</strong></div>', unsafe_allow_html=True)
    if filing.source_url:
        st.markdown(evidence_chip_html(ClaimType.FACT, has_source=True), unsafe_allow_html=True)
    st.markdown(f'<div style="margin-top:0.15rem;">{_source_facts_html(filing)}</div>', unsafe_allow_html=True)
    if filing.source_url:
        st.markdown(
            f'<div style="margin-top:0.15rem;"><a href="{filing.source_url}" target="_blank">Open original filing ↗</a></div>',
            unsafe_allow_html=True,
        )

    # 2. What is unconfirmed
    category = _matched_category(candidate.matched_rules)
    if filing.source_name == _DART_SOURCE and category == "market_rumor_response":
        unconfirmed_text = _UNCONFIRMED_TEMPLATES["market_rumor_response"]
    else:
        unconfirmed_text = _UNCONFIRMED_FALLBACK
    st.markdown('<div class="er-muted" style="margin-top:0.4rem;"><strong>What is unconfirmed</strong></div>', unsafe_allow_html=True)
    st.markdown(evidence_chip_html(ClaimType.UNCERTAINTY), unsafe_allow_html=True)
    st.markdown(f'<div style="margin-top:0.15rem;">{unconfirmed_text}</div>', unsafe_allow_html=True)

    # 3. Why it entered Radar
    st.markdown('<div class="er-muted" style="margin-top:0.4rem;"><strong>Why it entered Radar</strong></div>', unsafe_allow_html=True)
    st.markdown(evidence_chip_html(ClaimType.INTERPRETATION), unsafe_allow_html=True)
    for phrase in _why_entered_radar_phrases(filing.source_name, candidate.matched_rules):
        st.markdown(f'<div style="margin-top:0.1rem; margin-left:0.8rem;">• {phrase}</div>', unsafe_allow_html=True)

    # 4. Follow-up evidence to watch
    if filing.source_name == _DART_SOURCE and category == "market_rumor_response":
        followups = _FOLLOWUP_TEMPLATES["market_rumor_response"]
    else:
        followups = _FOLLOWUP_FALLBACK
    st.markdown('<div class="er-muted" style="margin-top:0.4rem;"><strong>Follow-up evidence to watch</strong></div>', unsafe_allow_html=True)
    for item in followups:
        st.markdown(f'<div style="margin-top:0.1rem; margin-left:0.8rem;">• {item}</div>', unsafe_allow_html=True)

    # 5. Evidence and provenance — a pointer to what's already rendered
    # below (the raw excerpt/translation blocks stay exactly where they
    # are, unmodified), not a duplicate of it.
    st.markdown('<div class="er-muted" style="margin-top:0.4rem;"><strong>Evidence and provenance</strong></div>', unsafe_allow_html=True)
    st.markdown('<div style="margin-top:0.15rem;">Original-language excerpt: see below.</div>', unsafe_allow_html=True)
    if candidate.translation_state != TranslationState.NOT_REQUESTED:
        if candidate.excerpt_translation is not None:
            st.markdown(
                '<div style="margin-top:0.1rem;">Machine translation: see below — for convenience, verify against the original-language source.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div style="margin-top:0.1rem;">Machine translation: not currently available for this excerpt.</div>', unsafe_allow_html=True)
