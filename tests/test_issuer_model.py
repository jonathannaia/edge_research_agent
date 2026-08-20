"""Issuer domain model — pure dataclass/enum behavior, zero registry data."""
from src.models.issuer import CoverageState, Issuer, LifecycleState


def test_issuer_requires_only_the_documented_core_fields():
    issuer = Issuer(
        issuer_id="test:ABC",
        legal_name="Test Co",
        country_or_jurisdiction="Unconfirmed",
        coverage_state=CoverageState.DISCOVERED,
    )
    assert issuer.lifecycle_state == LifecycleState.ACTIVE  # default
    assert issuer.identifiers == {}
    assert issuer.themes == ()
    assert issuer.aliases == ()
    assert issuer.evidence_confidence == "Not assessed"


def test_issuer_is_frozen():
    issuer = Issuer(
        issuer_id="test:ABC", legal_name="Test Co",
        country_or_jurisdiction="Unconfirmed", coverage_state=CoverageState.SEED,
    )
    try:
        issuer.legal_name = "Changed"
        assert False, "expected dataclasses.FrozenInstanceError"
    except Exception as exc:
        assert type(exc).__name__ == "FrozenInstanceError"


def test_issuer_identifiers_default_is_not_shared_across_instances():
    a = Issuer(issuer_id="a", legal_name="A", country_or_jurisdiction="X", coverage_state=CoverageState.SEED)
    b = Issuer(issuer_id="b", legal_name="B", country_or_jurisdiction="X", coverage_state=CoverageState.SEED)
    a.identifiers["SEC EDGAR"] = "0000000001"
    assert b.identifiers == {}


def test_coverage_state_values():
    assert {s.value for s in CoverageState} == {"Seed", "Discovered", "Rejected"}


def test_lifecycle_state_values():
    assert {s.value for s in LifecycleState} == {"Active", "Monitoring", "Delisted", "Merged"}
