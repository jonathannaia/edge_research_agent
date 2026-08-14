from datetime import date, timedelta

from src.config.settings import Settings
from src.providers.base import FundamentalsSnapshot
from src.scoring.context import ResearchContext
from src.scoring.defaults import EVIDENCE_QUALITY_CAP_VALUE
from src.scoring.scorecard import compute_scorecard

TODAY = date.today().isoformat()


def _fundamentals(**overrides) -> FundamentalsSnapshot:
    defaults = dict(
        ticker="TEST", period_label="Q1", period_end_date=TODAY, revenue=100_000_000,
        revenue_yoy_growth=0.20, gross_margin=0.30, gross_margin_prior_year=0.30,
        operating_margin=0.10, free_cash_flow=5_000_000, cash_and_equivalents=100_000_000,
        total_debt=10_000_000, shares_outstanding=10_000_000, shares_outstanding_yoy_change=0.0,
        source_title="Test 10-Q", source_url_or_identifier="TEST-10Q", source_date=TODAY,
        source_type="Regulatory Filing",
    )
    defaults.update(overrides)
    return FundamentalsSnapshot(**defaults)


def test_total_score_matches_weighted_formula_for_single_weighted_component():
    ctx = ResearchContext(ticker="TEST")
    ctx.fundamentals = _fundamentals(revenue_yoy_growth=0.20)
    ctx.fundamentals_source_id = 1
    ctx.all_source_dates = [(1, TODAY)]  # fresh -> evidence_quality raw_score = 5, no cap

    weights = {"revenue_growth_demand": 1.0}  # everything else normalizes to 0
    settings = Settings()
    result = compute_scorecard(ctx, settings, weights, today_iso=TODAY)

    revenue_component = next(c for c in result.components if c.key == "revenue_growth_demand")
    assert revenue_component.raw_score == 5  # 3 + 0.20/0.05 = 7, clamped to 5
    assert result.total_score == 5.0
    assert result.is_capped is False


def test_poor_evidence_quality_caps_total_score():
    ctx = ResearchContext(ticker="TEST")
    ctx.fundamentals = _fundamentals(revenue_yoy_growth=0.30, gross_margin=0.40, gross_margin_prior_year=0.20)
    ctx.fundamentals_source_id = 1
    stale_date = (date.today() - timedelta(days=400)).isoformat()
    ctx.all_source_dates = [(1, stale_date)]  # very stale -> evidence_quality raw_score = 1

    settings = Settings()
    result = compute_scorecard(ctx, settings, weights=None, today_iso=TODAY)

    evidence_component = next(c for c in result.components if c.key == "evidence_quality_freshness")
    assert evidence_component.raw_score <= 2
    assert result.is_capped is True
    assert result.total_score == EVIDENCE_QUALITY_CAP_VALUE
    assert result.cap_reason is not None


def test_weights_are_normalized_even_if_they_do_not_sum_to_one():
    ctx = ResearchContext(ticker="TEST")
    ctx.fundamentals = _fundamentals(revenue_yoy_growth=0.0, gross_margin=0.30, gross_margin_prior_year=0.30)
    ctx.fundamentals_source_id = 1
    ctx.all_source_dates = [(1, TODAY)]

    # Two components weighted equally at 2.0 each (not normalized) should behave
    # identically to 0.5/0.5 once normalized.
    weights = {"revenue_growth_demand": 2.0, "gross_margin_operating_leverage": 2.0}
    settings = Settings()
    result = compute_scorecard(ctx, settings, weights, today_iso=TODAY)

    revenue_component = next(c for c in result.components if c.key == "revenue_growth_demand")
    margin_component = next(c for c in result.components if c.key == "gross_margin_operating_leverage")
    assert revenue_component.weight == 0.5
    assert margin_component.weight == 0.5
    # both raw scores are 3 (flat growth, flat margin) -> total should be 3.0
    assert result.total_score == 3.0


def test_risk_and_cash_flow_warnings_are_generated_when_scores_are_poor():
    ctx = ResearchContext(ticker="TEST")
    ctx.fundamentals = _fundamentals(
        free_cash_flow=-5_000_000, cash_and_equivalents=1_000_000, total_debt=50_000_000,
        shares_outstanding_yoy_change=0.15,
    )
    ctx.fundamentals_source_id = 1
    ctx.all_source_dates = [(1, TODAY)]

    settings = Settings()
    result = compute_scorecard(ctx, settings, weights=None, today_iso=TODAY)

    cash_flow_component = next(c for c in result.components if c.key == "cash_flow_balance_sheet")
    assert cash_flow_component.raw_score <= 2
    assert any("Cash flow" in w for w in result.risk_warnings)
