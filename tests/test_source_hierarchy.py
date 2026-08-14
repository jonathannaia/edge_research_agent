from src.guardrails.source_hierarchy import ExcerptRef, authority_rank, resolve_conflict
from src.models.models import SourceType


def test_sec_filing_outranks_social_media():
    assert authority_rank(SourceType.SEC_FILING) < authority_rank(SourceType.SOCIAL_MEDIA)


def test_insider_filing_and_sec_filing_are_top_authority():
    assert authority_rank(SourceType.SEC_FILING) == authority_rank(SourceType.INSIDER_FILING) == 1


def test_authority_rank_accepts_string_values():
    assert authority_rank("Regulatory Filing") == 1
    assert authority_rank("Social Media (unverified lead)") == 5


def test_authority_rank_unknown_type_defaults_to_lowest_authority():
    assert authority_rank("Some Unrecognized Type") == 5


def test_resolve_conflict_prefers_higher_authority():
    sec_excerpt = ExcerptRef(1, "Regulatory Filing", "2026-06-01", "bearish", "Filing says demand is soft.")
    social_excerpt = ExcerptRef(2, "Social Media (unverified lead)", "2026-08-01", "bullish", "A forum post says demand is booming.")
    winner, explanation = resolve_conflict([sec_excerpt, social_excerpt])
    assert winner.source_id == 1
    assert "disagree" in explanation


def test_resolve_conflict_prefers_more_recent_when_authority_ties():
    older = ExcerptRef(1, "Regulatory Filing", "2026-01-01", "bearish", "Old filing says demand is soft.")
    newer = ExcerptRef(2, "Regulatory Filing", "2026-07-01", "bullish", "New filing says demand improved.")
    winner, _explanation = resolve_conflict([older, newer])
    assert winner.source_id == 2


def test_resolve_conflict_reports_agreement_when_tags_match():
    a = ExcerptRef(1, "Regulatory Filing", "2026-01-01", "bullish", "Demand is strong.")
    b = ExcerptRef(2, "Earnings Call Transcript", "2026-02-01", "bullish", "Demand is strong here too.")
    _winner, explanation = resolve_conflict([a, b])
    assert "agree" in explanation.lower()


def test_resolve_conflict_requires_at_least_one_excerpt():
    try:
        resolve_conflict([])
        assert False, "expected ValueError"
    except ValueError:
        pass
