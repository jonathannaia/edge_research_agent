"""Change detection between research snapshots (guardrail area #5).

A "snapshot" is a small, normalized dict of extracted facts (not the full
brief) captured every time a brief is saved. Comparing two snapshots buckets
what moved into confirming / disconfirming / neutral / new_unknowns so the
"What Changed Since Last Review?" section never has to re-read full prose.
"""
from __future__ import annotations

from typing import Any

from src.scoring.context import ResearchContext
from src.scoring.scorecard import ScorecardResult

# Fields where a HIGHER value is favorable (confirming) and a LOWER value is
# unfavorable (disconfirming). Used generically by compare_snapshots.
_FAVORABLE_UP_FIELDS = {
    "revenue_yoy_growth": "Revenue growth",
    "gross_margin": "Gross margin",
    "free_cash_flow": "Free cash flow",
    "total_score": "Conviction score",
    "insider_buy_count": "Insider buying",
    "institutional_ownership_pct": "Institutional ownership",
}
_FAVORABLE_DOWN_FIELDS = {
    "shares_outstanding_yoy_change": "Dilution (share count growth)",
    "total_debt": "Total debt",
    "insider_sell_count": "Insider selling",
}


def build_snapshot_facts(
    ctx: ResearchContext, scorecard: ScorecardResult, bottom_line: str, evidence_quality_raw_score: int
) -> dict[str, Any]:
    f = ctx.fundamentals
    buys = [t for t in ctx.insider_txns if t.transaction_type.lower() == "buy"]
    sells = [t for t in ctx.insider_txns if t.transaction_type.lower() == "sell"]
    return {
        "bottom_line": bottom_line,
        "total_score": scorecard.total_score,
        "evidence_quality_raw_score": evidence_quality_raw_score,
        "revenue_yoy_growth": f.revenue_yoy_growth if f else None,
        "gross_margin": f.gross_margin if f else None,
        "free_cash_flow": f.free_cash_flow if f else None,
        "total_debt": f.total_debt if f else None,
        "shares_outstanding_yoy_change": f.shares_outstanding_yoy_change if f else None,
        "insider_buy_count": len(buys),
        "insider_sell_count": len(sells),
        "institutional_ownership_pct": ctx.ownership.institutional_ownership_pct if ctx.ownership else None,
        "n_risk_evidence": len(ctx.evidence_with_tag("risk", "bearish", "dilution")),
        "n_demand_evidence": len(ctx.evidence_with_tag("demand", "bullish", "product_cycle")),
        "next_earnings_date": ctx.next_earnings_date,
        "n_sources": len({sid for sid, _ in ctx.all_source_dates}),
    }


def compare_snapshots(prior: dict[str, Any], current: dict[str, Any]) -> dict[str, list[str]]:
    confirming: list[str] = []
    disconfirming: list[str] = []
    neutral: list[str] = []
    new_unknowns: list[str] = []

    for field, label in _FAVORABLE_UP_FIELDS.items():
        old, new = prior.get(field), current.get(field)
        if old is None and new is not None:
            new_unknowns.append(f"{label} is now available ({new}); no prior value to compare.")
            continue
        if old is None or new is None:
            continue
        if new > old:
            confirming.append(f"{label} improved: {old} -> {new}.")
        elif new < old:
            disconfirming.append(f"{label} declined: {old} -> {new}.")
        else:
            neutral.append(f"{label} unchanged at {new}.")

    for field, label in _FAVORABLE_DOWN_FIELDS.items():
        old, new = prior.get(field), current.get(field)
        if old is None and new is not None:
            new_unknowns.append(f"{label} is now available ({new}); no prior value to compare.")
            continue
        if old is None or new is None:
            continue
        if new < old:
            confirming.append(f"{label} improved: {old} -> {new}.")
        elif new > old:
            disconfirming.append(f"{label} deteriorated: {old} -> {new}.")
        else:
            neutral.append(f"{label} unchanged at {new}.")

    old_bl, new_bl = prior.get("bottom_line"), current.get("bottom_line")
    if old_bl and new_bl and old_bl != new_bl:
        neutral.append(f"Bottom line changed: '{old_bl}' -> '{new_bl}'.")

    old_risk, new_risk = prior.get("n_risk_evidence"), current.get("n_risk_evidence")
    if old_risk is not None and new_risk is not None:
        if new_risk > old_risk:
            disconfirming.append(f"New risk-tagged evidence items found: {old_risk} -> {new_risk}.")
        elif new_risk < old_risk:
            confirming.append(f"Fewer risk-tagged evidence items than before: {old_risk} -> {new_risk}.")

    old_demand, new_demand = prior.get("n_demand_evidence"), current.get("n_demand_evidence")
    if old_demand is not None and new_demand is not None and new_demand != old_demand:
        (confirming if new_demand > old_demand else disconfirming).append(
            f"Demand/bullish-tagged evidence items changed: {old_demand} -> {new_demand}."
        )

    old_cat, new_cat = prior.get("next_earnings_date"), current.get("next_earnings_date")
    if old_cat != new_cat:
        new_unknowns.append(f"Next catalyst date changed or newly identified: {old_cat} -> {new_cat}.")

    return {
        "confirming": confirming,
        "disconfirming": disconfirming,
        "neutral": neutral,
        "new_unknowns": new_unknowns,
    }
