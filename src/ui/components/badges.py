"""Badge/indicator components. Claim-type rendering now delegates to
evidence_chips.py (brief §7's custom HTML chip system replaces st.badge for
that one case — see that module's docstring for why). Freshness/strength
badges still use native st.badge for now; freshness gets a real 3-state
Live/Stale/Demo treatment in the dedicated freshness pass (brief §13).
Direction is glyph + text-weight only, never color (brief §5 — zero accent
color anywhere).
"""
from __future__ import annotations

import streamlit as st

from src.models.models import Direction, EvidenceItem, Strength, ClaimType
from src.ui.components.evidence_chips import evidence_chip

_FRESHNESS_COLOR = {"Fresh": "green", "Aging": "orange", "Stale": "gray", "Unknown": "gray"}

_STRENGTH_COLOR = {Strength.STRONG: "green", Strength.MODERATE: "yellow", Strength.WEAK: "gray"}

_DIRECTION_GLYPH = {
    Direction.IMPROVING: "▲",
    Direction.WEAKENING: "▼",
    Direction.EMERGING: "●",
    Direction.MIXED: "◆",
}

_DIRECTION_WEIGHT_CLASS = {
    Direction.IMPROVING: "er-dir",
    Direction.WEAKENING: "er-dir er-dir-weakening",
    Direction.EMERGING: "er-dir",
    Direction.MIXED: "er-dir er-dir-mixed",
}


def claim_type_badge(claim_type: ClaimType, has_source: bool = True) -> None:
    evidence_chip(claim_type, has_source=has_source)


def freshness_badge(evidence: EvidenceItem) -> None:
    label = evidence.freshness_label
    st.badge(label, color=_FRESHNESS_COLOR.get(label, "gray"))


def strength_badge(strength: Strength) -> None:
    st.badge(strength.value, color=_STRENGTH_COLOR.get(strength, "gray"))


def demo_badge(label: str = "Demo data") -> None:
    st.badge(label, color="gray")


def direction_dot_html(direction: Direction) -> str:
    """Direction shown as a glyph + label, weight-differentiated — never
    color (zero accent-color rule, brief §5)."""
    glyph = _DIRECTION_GLYPH.get(direction, "●")
    cls = _DIRECTION_WEIGHT_CLASS.get(direction, "er-dir")
    return f'<span class="{cls}"><span class="er-dir-glyph">{glyph}</span>{direction.value}</span>'
