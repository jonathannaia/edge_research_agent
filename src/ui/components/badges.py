"""Badge components — thin wrappers over Streamlit's native st.badge, so
every claim-type, direction, strength, and freshness indicator in the app
uses one consistent, accessible widget instead of hand-rolled HTML pills.
"""
from __future__ import annotations

import streamlit as st

from src.models.models import ClaimType, Direction, EvidenceItem, Strength

_CLAIM_TYPE_COLOR = {
    ClaimType.FACT: "blue",
    ClaimType.INTERPRETATION: "violet",
    ClaimType.INFERENCE: "orange",
    ClaimType.UNCERTAINTY: "gray",
}

_FRESHNESS_COLOR = {"Fresh": "green", "Aging": "yellow", "Stale": "gray", "Unknown": "gray"}

_DIRECTION_COLOR = {
    Direction.IMPROVING: "green",
    Direction.WEAKENING: "red",
    Direction.EMERGING: "blue",
    Direction.MIXED: "yellow",
}

_STRENGTH_COLOR = {Strength.STRONG: "green", Strength.MODERATE: "yellow", Strength.WEAK: "gray"}


def claim_type_badge(claim_type: ClaimType) -> None:
    st.badge(claim_type.value, color=_CLAIM_TYPE_COLOR.get(claim_type, "gray"))


def freshness_badge(evidence: EvidenceItem) -> None:
    label = evidence.freshness_label
    st.badge(label, color=_FRESHNESS_COLOR.get(label, "gray"))


def direction_badge(direction: Direction) -> None:
    st.badge(direction.value, color=_DIRECTION_COLOR.get(direction, "gray"))


def strength_badge(strength: Strength) -> None:
    st.badge(strength.value, color=_STRENGTH_COLOR.get(strength, "gray"))


def demo_badge(label: str = "Demo data") -> None:
    st.badge(label, color="gray")


_DIRECTION_RAIL_CLASS = {
    Direction.IMPROVING: "er-rail-improving",
    Direction.WEAKENING: "er-rail-weakening",
    Direction.MIXED: "er-rail-mixed",
    Direction.EMERGING: "er-rail-emerging",
}

_DIRECTION_DOT_CLASS = {
    Direction.IMPROVING: "er-dir-improving",
    Direction.WEAKENING: "er-dir-weakening",
    Direction.MIXED: "er-dir-mixed",
    Direction.EMERGING: "er-dir-emerging",
}


def direction_rail_class(direction: Direction) -> str:
    """CSS class for the left accent rail on a signal/market-pulse item —
    used as `st.container(key=..., ...)` doesn't accept a class directly,
    so callers wrap content in `st.markdown(f'<div class="{cls}">')` /
    `</div>` around the block, or apply it via a keyed container's class
    (see cards.py for the exact pattern in use)."""
    return _DIRECTION_RAIL_CLASS.get(direction, "")


def direction_dot_html(direction: Direction) -> str:
    """A small colored dot + the direction label, as a single inline HTML
    snippet — the rail carries the same color for redundant (not
    color-only) encoding of direction."""
    cls = _DIRECTION_DOT_CLASS.get(direction, "")
    return f'<span class="er-dir-dot {cls}"></span>{direction.value}'
