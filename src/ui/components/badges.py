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
