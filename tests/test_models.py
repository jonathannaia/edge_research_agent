from datetime import datetime, timedelta, timezone

from src.models.models import (
    CapitalRotationMetric,
    Catalyst,
    ChatAnswer,
    ClaimType,
    Direction,
    EvidenceItem,
    Exposure,
    Horizon,
    ResearchClaim,
    Signal,
    Strength,
    Subtheme,
    Theme,
    Ticker,
    WatchlistEntry,
)


def _iso(days_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def test_theme_holds_subthemes():
    sub = Subtheme(slug="optical-transceivers", name="Optical Transceivers", description="d", theme_slug="photonics")
    theme = Theme(slug="photonics", name="Photonics", description="d", subthemes=[sub])
    assert theme.subthemes[0].theme_slug == theme.slug


def test_evidence_item_defaults_are_demo_safe():
    ev = EvidenceItem(
        id="ev-1", title="t", source_name="EevaResearch Demo Data", source_type="Demo Dataset",
        published_at=_iso(1), retrieved_at=_iso(1), excerpt="e", claim_type=ClaimType.FACT,
    )
    assert ev.source_url is None
    assert ev.is_demo is True
    assert ev.source_name == "EevaResearch Demo Data"


def test_evidence_item_freshness_buckets():
    fresh = EvidenceItem(id="1", title="t", source_name="s", source_type="s", published_at=_iso(1), retrieved_at=_iso(1), excerpt="e", claim_type=ClaimType.FACT)
    aging = EvidenceItem(id="2", title="t", source_name="s", source_type="s", published_at=_iso(5), retrieved_at=_iso(5), excerpt="e", claim_type=ClaimType.FACT)
    stale = EvidenceItem(id="3", title="t", source_name="s", source_type="s", published_at=_iso(30), retrieved_at=_iso(30), excerpt="e", claim_type=ClaimType.FACT)
    assert fresh.freshness_label == "Fresh"
    assert aging.freshness_label == "Aging"
    assert stale.freshness_label == "Stale"


def test_evidence_item_freshness_handles_unparseable_timestamp():
    bad = EvidenceItem(id="1", title="t", source_name="s", source_type="s", published_at="not-a-date", retrieved_at="not-a-date", excerpt="e", claim_type=ClaimType.FACT)
    assert bad.freshness_label == "Unknown"


def test_research_claim_carries_evidence_list():
    ev = EvidenceItem(id="1", title="t", source_name="s", source_type="s", published_at=_iso(1), retrieved_at=_iso(1), excerpt="e", claim_type=ClaimType.FACT)
    claim = ResearchClaim(text="claim", claim_type=ClaimType.INTERPRETATION, evidence=[ev])
    assert claim.evidence[0].id == "1"


def test_ticker_defaults_to_demo():
    t = Ticker(
        symbol="DEMO", company_name="Nova Aperture Systems (Demo Company — Not Real)",
        theme_slug="photonics", subtheme_slug="optical-transceivers", exposure=Exposure.PRIMARY,
        market_cap_bucket="Mid", liquidity_bucket="Medium", technical_strength="Neutral",
        risk_level="Medium", thesis="placeholder thesis",
    )
    assert t.is_demo is True


def test_catalyst_theme_and_ticker_optional_linkage():
    c = Catalyst(id="c1", title="t", date="2026-09-01", catalyst_type="Industry Event", description="d", theme_slug="space")
    assert c.ticker_symbol is None


def test_signal_enums_hold_expected_values():
    s = Signal(
        id="s1", title="t", theme_slug="memory", subtheme_slug=None, direction=Direction.EMERGING,
        strength=Strength.MODERATE, horizon=Horizon.MULTI_WEEK, evidence_count=2,
        interpretation="i", contrary_evidence="c", validation_criteria="v", invalidation_criteria="iv",
        related_tickers=["DEMO"], last_updated=_iso(1),
    )
    assert s.direction == Direction.EMERGING
    assert s.strength.value == "Moderate"


def test_capital_rotation_metric_is_demo_by_default():
    m = CapitalRotationMetric(theme_slug="ai-buildout", relative_performance_pct=1.2, breadth_pct=55.0, leaders=["DEMO"], laggards=[], as_of=_iso(0))
    assert m.is_demo is True


def test_chat_answer_defaults_claim_type_interpretation():
    a = ChatAnswer(
        question="q", what_happened="w", why_it_matters="w2", underappreciated="u", risks="r",
        what_to_watch="wtw", sources=[], confidence=Strength.MODERATE, freshness="Fresh",
    )
    assert a.claim_type == ClaimType.INTERPRETATION


def test_watchlist_entry_defaults_note_empty():
    e = WatchlistEntry(list_name="Core Themes", ticker_symbol="DEMO", added_at=_iso(0))
    assert e.note == ""
