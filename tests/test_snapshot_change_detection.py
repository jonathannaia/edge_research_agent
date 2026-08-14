from src.services.snapshot_service import compare_snapshots


def test_revenue_growth_improvement_is_confirming():
    prior = {"revenue_yoy_growth": 0.05}
    current = {"revenue_yoy_growth": 0.15}
    diff = compare_snapshots(prior, current)
    assert any("Revenue growth improved" in item for item in diff["confirming"])


def test_debt_increase_is_disconfirming():
    prior = {"total_debt": 10_000_000}
    current = {"total_debt": 25_000_000}
    diff = compare_snapshots(prior, current)
    assert any("Total debt deteriorated" in item for item in diff["disconfirming"])


def test_dilution_increase_is_disconfirming():
    prior = {"shares_outstanding_yoy_change": 0.01}
    current = {"shares_outstanding_yoy_change": 0.08}
    diff = compare_snapshots(prior, current)
    assert any("Dilution" in item for item in diff["disconfirming"])


def test_bottom_line_change_is_noted_as_neutral_bucket():
    prior = {"bottom_line": "Mixed setup"}
    current = {"bottom_line": "Bullish setup"}
    diff = compare_snapshots(prior, current)
    assert any("Bottom line changed" in item for item in diff["neutral"])


def test_new_field_with_no_prior_value_is_new_unknown():
    prior = {"institutional_ownership_pct": None}
    current = {"institutional_ownership_pct": 0.6}
    diff = compare_snapshots(prior, current)
    assert any("now available" in item for item in diff["new_unknowns"])


def test_no_change_produces_neutral_entries_not_confirming_or_disconfirming():
    prior = {"revenue_yoy_growth": 0.10}
    current = {"revenue_yoy_growth": 0.10}
    diff = compare_snapshots(prior, current)
    assert diff["confirming"] == []
    assert diff["disconfirming"] == []
    assert any("unchanged" in item.lower() for item in diff["neutral"])


def test_risk_evidence_increase_is_disconfirming():
    prior = {"n_risk_evidence": 1}
    current = {"n_risk_evidence": 4}
    diff = compare_snapshots(prior, current)
    assert any("New risk-tagged evidence" in item for item in diff["disconfirming"])
