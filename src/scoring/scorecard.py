"""Orchestrates the 12 component scorers into a full, weighted, capped
scorecard. Weights are supplied by the caller (loaded from app_settings,
falling back to DEFAULT_WEIGHTS) so they stay editable via the UI without
this module needing to know about persistence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.config.settings import Settings
from src.scoring import component_scorers as scorers
from src.scoring.context import ResearchContext
from src.scoring.defaults import (
    DEFAULT_COMPONENTS,
    EVIDENCE_QUALITY_CAP_THRESHOLD,
    EVIDENCE_QUALITY_CAP_VALUE,
    RISK_WARNING_THRESHOLD,
)


@dataclass
class ComponentScore:
    key: str
    label: str
    weight: float
    raw_score: int
    weighted_score: float
    explanation: str
    citation_source_ids: list[int]


@dataclass
class ScorecardResult:
    total_score: float
    is_capped: bool
    cap_reason: str | None
    components: list[ComponentScore]
    risk_warnings: list[str]


_SCORER_FN = {
    "revenue_growth_demand": lambda ctx, settings, today: scorers.score_revenue_growth_demand(ctx),
    "gross_margin_operating_leverage": lambda ctx, settings, today: scorers.score_gross_margin_operating_leverage(ctx),
    "cash_flow_balance_sheet": lambda ctx, settings, today: scorers.score_cash_flow_balance_sheet(ctx),
    "guidance_earnings_quality": lambda ctx, settings, today: scorers.score_guidance_earnings_quality(ctx),
    "bookings_backlog_customer": lambda ctx, settings, today: scorers.score_bookings_backlog_customer(ctx),
    "product_cycle_tech_partnerships": lambda ctx, settings, today: scorers.score_product_cycle_tech_partnerships(ctx),
    "insider_ownership": lambda ctx, settings, today: scorers.score_insider_ownership(ctx),
    "valuation_context": lambda ctx, settings, today: scorers.score_valuation_context(ctx),
    "technical_setup": lambda ctx, settings, today: scorers.score_technical_setup(ctx),
    "catalyst_strength_timing": lambda ctx, settings, today: scorers.score_catalyst_strength_timing(ctx, today),
    "risk_level_thesis_fragility": lambda ctx, settings, today: scorers.score_risk_level_thesis_fragility(ctx),
    "evidence_quality_freshness": lambda ctx, settings, today: scorers.score_evidence_quality_freshness(ctx, settings, today),
}

_LABELS = {c["key"]: c["label"] for c in DEFAULT_COMPONENTS}


def compute_scorecard(
    ctx: ResearchContext,
    settings: Settings,
    weights: dict[str, float] | None = None,
    today_iso: str | None = None,
) -> ScorecardResult:
    weights = weights or {c["key"]: c["weight"] for c in DEFAULT_COMPONENTS}
    today_iso = today_iso or date.today().isoformat()

    # Normalize weights so they always sum to 1.0, however the UI edited them.
    weight_sum = sum(weights.values()) or 1.0
    normalized = {k: v / weight_sum for k, v in weights.items()}

    components: list[ComponentScore] = []
    for key, fn in _SCORER_FN.items():
        result = fn(ctx, settings, today_iso)
        weight = normalized.get(key, 0.0)
        components.append(
            ComponentScore(
                key=key,
                label=_LABELS[key],
                weight=weight,
                raw_score=result.raw_score,
                weighted_score=round(weight * result.raw_score, 4),
                explanation=result.explanation,
                citation_source_ids=result.citation_source_ids,
            )
        )

    raw_total = round(sum(c.weighted_score for c in components), 3)

    evidence_component = next(c for c in components if c.key == "evidence_quality_freshness")
    is_capped = evidence_component.raw_score <= EVIDENCE_QUALITY_CAP_THRESHOLD
    cap_reason = None
    total = raw_total
    if is_capped and raw_total > EVIDENCE_QUALITY_CAP_VALUE:
        cap_reason = (
            f"Evidence quality/freshness scored {evidence_component.raw_score}/5 "
            f"(poor or stale evidence), which caps overall confidence regardless of "
            f"other component scores."
        )
        total = EVIDENCE_QUALITY_CAP_VALUE

    risk_warnings = []
    for key in ("cash_flow_balance_sheet", "risk_level_thesis_fragility"):
        c = next(x for x in components if x.key == key)
        if c.raw_score <= RISK_WARNING_THRESHOLD:
            risk_warnings.append(f"{c.label} scored {c.raw_score}/5 — {c.explanation}")

    return ScorecardResult(
        total_score=total,
        is_capped=is_capped and cap_reason is not None,
        cap_reason=cap_reason,
        components=components,
        risk_warnings=risk_warnings,
    )
