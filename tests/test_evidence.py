from src.logic.evidence import claim_type_badge, freshness_badge, source_label
from src.models.models import ClaimType, EvidenceItem


def _evidence(**overrides) -> EvidenceItem:
    defaults = dict(
        id="1", title="t", source_name="EevaResearch Demo Data", source_type="Demo Dataset",
        published_at="2026-08-15T00:00:00+00:00", retrieved_at="2026-08-15T00:00:00+00:00",
        excerpt="e", claim_type=ClaimType.FACT,
    )
    defaults.update(overrides)
    return EvidenceItem(**defaults)


def test_claim_type_badge_returns_label_and_color_for_all_types():
    for ct in ClaimType:
        label, color = claim_type_badge(ct)
        assert label == ct.value
        assert color != "unknown"


def test_freshness_badge_matches_evidence_freshness_label():
    ev = _evidence(retrieved_at="2026-08-15T00:00:00+00:00")
    label, color = freshness_badge(ev)
    assert label == ev.freshness_label
    assert color != "unknown" or label == "Unknown"


def test_source_label_no_url_states_demo_data_explicitly():
    ev = _evidence(source_url=None)
    label = source_label(ev)
    assert "demo data" in label.lower()
    assert "EevaResearch Demo Data" in label


def test_source_label_with_url_includes_it():
    ev = _evidence(source_url="https://example.com/demo-only")
    label = source_label(ev)
    assert "https://example.com/demo-only" in label
