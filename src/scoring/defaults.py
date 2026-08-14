"""Default scorecard weights. Editable at runtime via the Scoring Settings
page (persisted to app_settings); this module only supplies the starting
point and the canonical component metadata (key, label, description)."""
from __future__ import annotations

DEFAULT_COMPONENTS: list[dict] = [
    {
        "key": "revenue_growth_demand",
        "label": "Revenue growth & demand trajectory",
        "weight": 0.14,
        "description": "Is revenue accelerating, and is there corroborating evidence of real demand (not just a one-quarter beat)?",
    },
    {
        "key": "gross_margin_operating_leverage",
        "label": "Gross-margin trend & operating leverage",
        "weight": 0.12,
        "description": "Is gross margin expanding, and is the business showing operating leverage as it scales?",
    },
    {
        "key": "cash_flow_balance_sheet",
        "label": "Cash flow, balance sheet, debt, liquidity & dilution risk",
        "weight": 0.12,
        "description": "Free cash flow trend, debt load, liquidity runway, and share-count dilution.",
    },
    {
        "key": "guidance_earnings_quality",
        "label": "Guidance, earnings quality & estimate-revision context",
        "weight": 0.10,
        "description": "Is management raising, maintaining, or cutting guidance, and does commentary read as confident or defensive?",
    },
    {
        "key": "bookings_backlog_customer",
        "label": "Bookings, backlog, contracts & customer commentary",
        "weight": 0.12,
        "description": "Evidence of new bookings, backlog growth, contract wins, or customer concentration risk.",
    },
    {
        "key": "product_cycle_tech_partnerships",
        "label": "Product cycle, technology transition, capacity & partnerships",
        "weight": 0.08,
        "description": "Is there a concrete product cycle, technology transition, capacity expansion, or strategic partnership underway?",
    },
    {
        "key": "insider_ownership",
        "label": "Insider activity & ownership signals",
        "weight": 0.06,
        "description": "Recent insider buying/selling and institutional ownership trends.",
    },
    {
        "key": "valuation_context",
        "label": "Valuation context",
        "weight": 0.06,
        "description": "How the current valuation compares to peers and its own history — context only, never a price target.",
    },
    {
        "key": "technical_setup",
        "label": "Technical setup / price & volume context",
        "weight": 0.04,
        "description": "Price action and volume context relative to the evidence — context only, never a trade signal.",
    },
    {
        "key": "catalyst_strength_timing",
        "label": "Catalyst strength & timing",
        "weight": 0.06,
        "description": "Is there a concrete, dated upcoming catalyst that could confirm or invalidate the thesis?",
    },
    {
        "key": "risk_level_thesis_fragility",
        "label": "Risk level & thesis fragility",
        "weight": 0.06,
        "description": "How fragile is the thesis — customer concentration, balance-sheet stress, competitive displacement risk. 5 = low risk, 1 = high risk.",
    },
    {
        "key": "evidence_quality_freshness",
        "label": "Evidence quality & freshness",
        "weight": 0.04,
        "description": "How much of the evidence is primary-source and how fresh is it. A low score here caps overall confidence regardless of other components.",
    },
]

DEFAULT_WEIGHTS: dict[str, float] = {c["key"]: c["weight"] for c in DEFAULT_COMPONENTS}

EVIDENCE_QUALITY_CAP_THRESHOLD = 2  # raw_score <= this triggers a hard cap
EVIDENCE_QUALITY_CAP_VALUE = 2.5  # total_score is capped to this value
RISK_WARNING_THRESHOLD = 2  # raw_score <= this on cash_flow or risk components triggers a warning
