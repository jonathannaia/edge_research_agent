from src.guardrails.citation_validator import validate_brief, validate_brief_facts, validate_fact


def test_fact_with_source_id_is_valid():
    ok, err = validate_fact({"text": "Revenue grew 10% YoY.", "source_id": 1})
    assert ok is True
    assert err is None


def test_fact_with_estimate_label_is_valid():
    ok, err = validate_fact({"text": "Estimated backlog is roughly flat.", "label": "estimate"})
    assert ok is True


def test_fact_with_insufficient_evidence_label_is_valid():
    ok, err = validate_fact({"text": "No data available on customer concentration.", "label": "insufficient evidence"})
    assert ok is True


def test_fact_with_neither_source_nor_label_is_invalid():
    ok, err = validate_fact({"text": "Revenue is going to double next year."})
    assert ok is False
    assert "neither a source_id nor" in err


def test_fact_with_unrecognized_label_is_invalid():
    ok, err = validate_fact({"text": "Some claim.", "label": "trust me"})
    assert ok is False


def test_fact_with_invalid_source_id_type_is_invalid():
    ok, err = validate_fact({"text": "Some claim.", "source_id": "not-a-number"})
    assert ok is False


def test_validate_brief_facts_collects_all_errors():
    facts = [
        {"text": "Cited claim.", "source_id": 1},
        {"text": "Uncited claim."},
        {"text": "Another uncited claim."},
    ]
    result = validate_brief_facts(facts)
    assert result.is_valid is False
    assert len(result.errors) == 2


def test_validate_brief_walks_nested_sections():
    sections = {
        "verified_evidence": [
            {"text": "Cited fact one.", "source_id": 5},
            {"text": "Cited fact two.", "label": "unverified"},
        ],
        "bull_case_evidence": [{"text": "Bull point.", "source_id": 7}],
        "bottom_line": "Mixed setup",  # plain string, not a Fact — must be ignored, not flagged
    }
    result = validate_brief(sections)
    assert result.is_valid is True


def test_validate_brief_catches_uncited_claim_deep_in_structure():
    sections = {
        "fundamentals_snapshot": [
            {"text": "Revenue grew 10%.", "source_id": 1},
            {"text": "Margin will expand next year."},  # missing citation
        ]
    }
    result = validate_brief(sections)
    assert result.is_valid is False
    assert len(result.errors) == 1
