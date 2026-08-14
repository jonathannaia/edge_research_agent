"""Deterministic, threshold-based scoring for each of the 12 scorecard
components. Every raw_score is 1-5 (5 = most favorable / lowest risk) and
every explanation cites the source_id(s) it was derived from — nothing here
invents a number that isn't already in the ResearchContext.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.settings import Settings
from src.scoring.context import ResearchContext


@dataclass
class ComponentResult:
    raw_score: int
    explanation: str
    citation_source_ids: list[int]


def _clamp(n: float, lo: int = 1, hi: int = 5) -> int:
    return max(lo, min(hi, round(n)))


def score_revenue_growth_demand(ctx: ResearchContext) -> ComponentResult:
    if not ctx.fundamentals:
        return ComponentResult(1, "No fundamentals data available to assess revenue growth.", [])
    g = ctx.fundamentals.revenue_yoy_growth
    base = 3 + (g / 0.05)  # each 5pp of growth moves score by ~1
    demand_evidence = ctx.evidence_with_tag("demand", "bullish")
    risk_evidence = ctx.evidence_with_tag("bearish")
    base += 0.5 if demand_evidence else 0
    base -= 0.5 if risk_evidence else 0
    score = _clamp(base)
    citations = [ctx.fundamentals_source_id] + [e.source_id for e in demand_evidence + risk_evidence]
    explanation = (
        f"Revenue grew {g:+.1%} YoY ({ctx.fundamentals.period_label}). "
        f"{'Corroborating demand-side evidence found in filings/commentary.' if demand_evidence else 'No corroborating demand commentary found.'}"
    )
    return ComponentResult(score, explanation, [c for c in citations if c])


def score_gross_margin_operating_leverage(ctx: ResearchContext) -> ComponentResult:
    if not ctx.fundamentals:
        return ComponentResult(1, "No fundamentals data available to assess margin trend.", [])
    f = ctx.fundamentals
    delta = f.gross_margin - f.gross_margin_prior_year
    base = 3 + (delta / 0.02)  # each 2pp of margin change moves score by ~1
    score = _clamp(base)
    margin_evidence = ctx.evidence_with_tag("margin")
    explanation = (
        f"Gross margin {f.gross_margin:.1%} vs {f.gross_margin_prior_year:.1%} prior year "
        f"({delta:+.1%} pts). Operating margin {f.operating_margin:.1%}."
    )
    citations = [ctx.fundamentals_source_id] + [e.source_id for e in margin_evidence]
    return ComponentResult(score, explanation, [c for c in citations if c])


def score_cash_flow_balance_sheet(ctx: ResearchContext) -> ComponentResult:
    if not ctx.fundamentals:
        return ComponentResult(1, "No fundamentals data available to assess balance sheet.", [])
    f = ctx.fundamentals
    score = 3
    notes = []
    if f.free_cash_flow > 0:
        score += 1
        notes.append(f"positive free cash flow (${f.free_cash_flow:,.0f})")
    else:
        score -= 1
        notes.append(f"negative free cash flow (${f.free_cash_flow:,.0f})")
    net_cash = f.cash_and_equivalents - f.total_debt
    if net_cash > 0:
        score += 1
        notes.append("net cash position")
    else:
        score -= 1
        notes.append("net debt position")
    if f.shares_outstanding_yoy_change > 0.05:
        score -= 1
        notes.append(f"meaningful dilution ({f.shares_outstanding_yoy_change:+.1%} share count YoY)")
    score = _clamp(score)
    explanation = f"Balance sheet snapshot: {', '.join(notes)}."
    return ComponentResult(score, explanation, [ctx.fundamentals_source_id] if ctx.fundamentals_source_id else [])


def score_guidance_earnings_quality(ctx: ResearchContext) -> ComponentResult:
    guidance_evidence = ctx.evidence_with_tag("bullish", "margin", "demand")
    caution_evidence = ctx.evidence_with_tag("bearish", "risk")
    if not guidance_evidence and not caution_evidence:
        return ComponentResult(3, "No management commentary available to assess guidance tone or earnings quality.", [])
    score = 3 + len(guidance_evidence) - len(caution_evidence)
    score = _clamp(score)
    tone = "constructive" if len(guidance_evidence) >= len(caution_evidence) else "cautious/defensive"
    explanation = (
        f"Management commentary reads as {tone} "
        f"({len(guidance_evidence)} constructive item(s), {len(caution_evidence)} cautious item(s) found)."
    )
    citations = [e.source_id for e in guidance_evidence + caution_evidence]
    return ComponentResult(score, explanation, citations)


def score_bookings_backlog_customer(ctx: ResearchContext) -> ComponentResult:
    demand_evidence = ctx.evidence_with_tag("demand")
    risk_evidence = ctx.evidence_with_tag("risk")
    if not demand_evidence and not risk_evidence:
        return ComponentResult(3, "No bookings/backlog/customer commentary found in reviewed sources.", [])
    score = 3 + len(demand_evidence) - len(risk_evidence)
    score = _clamp(score)
    explanation = (
        f"Found {len(demand_evidence)} demand/bookings-related evidence item(s) and "
        f"{len(risk_evidence)} risk item(s) (e.g. customer concentration) touching bookings/backlog/customer activity."
    )
    citations = [e.source_id for e in demand_evidence + risk_evidence]
    return ComponentResult(score, explanation, citations)


def score_product_cycle_tech_partnerships(ctx: ResearchContext) -> ComponentResult:
    pc_evidence = ctx.evidence_with_tag("product_cycle")
    if not pc_evidence:
        return ComponentResult(3, "No evidence of an active product cycle, technology transition, or new partnership found.", [])
    score = _clamp(3 + len(pc_evidence))
    explanation = f"Found {len(pc_evidence)} item(s) describing a product cycle, technology transition, or partnership."
    return ComponentResult(score, explanation, [e.source_id for e in pc_evidence])


def score_insider_ownership(ctx: ResearchContext) -> ComponentResult:
    buys = [t for t in ctx.insider_txns if t.transaction_type.lower() == "buy"]
    sells = [t for t in ctx.insider_txns if t.transaction_type.lower() == "sell"]
    score = 3 + len(buys) - len(sells)
    score = _clamp(score)
    parts = [f"{len(buys)} insider buy(s)", f"{len(sells)} insider sell(s)"]
    if ctx.ownership:
        parts.append(f"institutional ownership {ctx.ownership.institutional_ownership_pct:.0%}")
    explanation = "; ".join(parts) + "."
    citations = list(ctx.insider_source_ids)
    if ctx.ownership_source_id:
        citations.append(ctx.ownership_source_id)
    return ComponentResult(score, explanation, citations)


def score_valuation_context(ctx: ResearchContext) -> ComponentResult:
    if not ctx.valuation or not ctx.valuation.ev_to_revenue or not ctx.valuation.peer_median_ev_to_revenue:
        return ComponentResult(3, "Insufficient valuation data to compare against peers.", [])
    v = ctx.valuation
    ratio = v.ev_to_revenue / v.peer_median_ev_to_revenue
    if ratio <= 0.7:
        score, note = 5, "trades at a meaningful discount to peer median EV/Revenue"
    elif ratio <= 0.9:
        score, note = 4, "trades modestly below peer median EV/Revenue"
    elif ratio <= 1.1:
        score, note = 3, "trades roughly in line with peer median EV/Revenue"
    elif ratio <= 1.3:
        score, note = 2, "trades modestly above peer median EV/Revenue"
    else:
        score, note = 1, "trades at a meaningful premium to peer median EV/Revenue"
    explanation = (
        f"EV/Revenue {v.ev_to_revenue:.1f}x vs peer median {v.peer_median_ev_to_revenue:.1f}x — {note}. "
        "Valuation context only; not a price target or recommendation."
    )
    return ComponentResult(score, explanation, [ctx.valuation_source_id] if ctx.valuation_source_id else [])


def score_technical_setup(ctx: ResearchContext) -> ComponentResult:
    if not ctx.price:
        return ComponentResult(3, "No price/volume data available.", [])
    p = ctx.price
    rng = p.fifty_two_week_high - p.fifty_two_week_low
    position = (p.last_price - p.fifty_two_week_low) / rng if rng > 0 else 0.5
    score = _clamp(1 + position * 4)
    explanation = (
        f"Trading at ${p.last_price:.2f}, {position:.0%} of the way through its 52-week range "
        f"(${p.fifty_two_week_low:.2f}-${p.fifty_two_week_high:.2f}); {p.pct_change_3m:+.0%} over 3 months. "
        "Price/technical context only — not a trade signal."
    )
    return ComponentResult(score, explanation, [ctx.price_source_id] if ctx.price_source_id else [])


def score_catalyst_strength_timing(ctx: ResearchContext, today_iso: str) -> ComponentResult:
    if not ctx.next_earnings_date:
        return ComponentResult(2, "No confirmed upcoming catalyst identified.", [])
    from datetime import date

    try:
        days_out = (date.fromisoformat(ctx.next_earnings_date) - date.fromisoformat(today_iso)).days
    except ValueError:
        return ComponentResult(3, "Catalyst date could not be parsed.", [])
    if days_out < 0:
        score = 2
    elif days_out <= 45:
        score = 5
    elif days_out <= 90:
        score = 4
    else:
        score = 3
    explanation = f"Next known catalyst (earnings) is {ctx.next_earnings_date} ({days_out} days out)."
    return ComponentResult(score, explanation, [ctx.earnings_source_id] if ctx.earnings_source_id else [])


def score_risk_level_thesis_fragility(ctx: ResearchContext) -> ComponentResult:
    risk_evidence = ctx.evidence_with_tag("risk", "dilution", "bearish")
    score = _clamp(5 - len(risk_evidence))
    if ctx.fundamentals and ctx.fundamentals.total_debt > ctx.fundamentals.cash_and_equivalents * 2:
        score = _clamp(score - 1)
    explanation = (
        f"{len(risk_evidence)} risk/dilution/bearish evidence item(s) identified in reviewed sources. "
        "5 = low risk / durable thesis, 1 = high risk / fragile thesis."
    )
    return ComponentResult(score, explanation, [e.source_id for e in risk_evidence])


def score_evidence_quality_freshness(ctx: ResearchContext, settings: Settings, today_iso: str) -> ComponentResult:
    from datetime import date

    if not ctx.all_source_dates:
        return ComponentResult(1, "No sources were retrieved for this ticker.", [])

    today = date.fromisoformat(today_iso)
    ages = []
    for _sid, source_date in ctx.all_source_dates:
        try:
            ages.append((today - date.fromisoformat(source_date)).days)
        except ValueError:
            continue
    if not ages:
        return ComponentResult(1, "Source dates could not be parsed.", [])

    avg_age = sum(ages) / len(ages)
    if avg_age <= settings.freshness_fresh_days:
        score = 5
    elif avg_age <= settings.freshness_aging_days:
        score = 4
    elif avg_age <= settings.freshness_stale_days:
        score = 2
    else:
        score = 1
    n_sources = len({sid for sid, _ in ctx.all_source_dates})
    explanation = (
        f"{n_sources} distinct source(s), average age {avg_age:.0f} days "
        f"(fresh <= {settings.freshness_fresh_days}d, stale > {settings.freshness_stale_days}d)."
    )
    return ComponentResult(score, explanation, [sid for sid, _ in ctx.all_source_dates])
