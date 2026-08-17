"""edinet_rules — pure functions, no I/O. Gate 1's DEFAULT_CODE_CATEGORY_MAP
is intentionally empty (see the module docstring — no real EDINET
ordinanceCode/formCode mapping has been confirmed), so every test that
needs a match injects its own explicit, clearly-fictional test map rather
than relying on any real EDINET code. Tests using the real empty default
confirm the honest "no match yet" Gate 1 behavior itself."""
from __future__ import annotations

from src.data_access.edinet.edinet_rules import (
    DEFAULT_CODE_CATEGORY_MAP,
    EDINET_CATEGORIES,
    evaluate_document,
    merge_evaluations,
)

# Fictional test codes — NOT real EDINET ordinanceCode/formCode values.
_TEST_MAP = {
    "010:030": "earnings_or_results",
    "010:040": "ownership_or_large_shareholding",
}


def test_default_code_category_map_is_empty():
    assert DEFAULT_CODE_CATEGORY_MAP == {}


def test_evaluate_document_with_default_empty_map_never_matches():
    result = evaluate_document("010", "030")
    assert result.confidence is None
    assert result.matched_rules == ()


def test_evaluate_document_matches_when_given_an_explicit_test_map():
    result = evaluate_document("010", "030", code_category_map=_TEST_MAP)
    assert result.confidence == "Moderate"
    assert result.matched_rules == ("earnings_or_results:010:030",)


def test_evaluate_document_unmatched_code_with_test_map_yields_no_confidence():
    result = evaluate_document("999", "999", code_category_map=_TEST_MAP)
    assert result.confidence is None
    assert result.matched_rules == ()


def test_evaluate_document_is_whitespace_tolerant_in_routing_key():
    result = evaluate_document(" 010 ", " 030 ", code_category_map=_TEST_MAP)
    assert result.confidence == "Moderate"


def test_all_edinet_categories_are_english_slugs():
    assert all(isinstance(c, str) and c == c.lower() for c in EDINET_CATEGORIES)
    assert "ownership_or_large_shareholding" in EDINET_CATEGORIES
    assert "other" in EDINET_CATEGORIES


def test_merge_evaluations_unions_matched_rules_without_duplicates():
    a = evaluate_document("010", "030", code_category_map=_TEST_MAP)
    b = evaluate_document("010", "040", code_category_map=_TEST_MAP)
    merged = merge_evaluations([a, b])
    assert merged.confidence == "High"  # two distinct categories
    assert set(merged.matched_rules) == {"earnings_or_results:010:030", "ownership_or_large_shareholding:010:040"}


def test_merge_evaluations_deduplicates_identical_rules():
    a = evaluate_document("010", "030", code_category_map=_TEST_MAP)
    merged = merge_evaluations([a, a])
    assert merged.matched_rules == a.matched_rules
    assert merged.confidence == "Moderate"


def test_merge_evaluations_empty_list_yields_no_confidence():
    merged = merge_evaluations([])
    assert merged.confidence is None
    assert merged.matched_rules == ()


def test_merge_evaluations_all_no_match_yields_no_confidence():
    a = evaluate_document("999", "999", code_category_map=_TEST_MAP)
    b = evaluate_document("888", "888", code_category_map=_TEST_MAP)
    merged = merge_evaluations([a, b])
    assert merged.confidence is None
