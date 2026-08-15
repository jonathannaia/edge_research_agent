"""Methodology — the evidence-first framework, claim-type legend, and
disclaimer. The one page every other page's "demo data" and claim-type
labels implicitly point back to."""
from __future__ import annotations

import streamlit as st

from src.models.models import ClaimType
from src.ui.chrome import METHODOLOGY_STATEMENT
from src.ui.components.badges import claim_type_badge, freshness_badge
from src.ui.components.section import section_header


def render() -> None:
    st.markdown("# Methodology")
    st.write(METHODOLOGY_STATEMENT)

    section_header("Claim types")
    st.write("Every material claim in EevaResearch is labeled as one of four types:")
    for ct, description in [
        (ClaimType.FACT, "A source-backed statement — something that happened, verifiable against a cited source."),
        (ClaimType.INTERPRETATION, "A read on what a fact or set of facts means — reasonable, but not itself a fact."),
        (ClaimType.INFERENCE, "A conclusion drawn from incomplete or indirect evidence — flagged as more speculative than an interpretation."),
        (ClaimType.UNCERTAINTY, "An open question or a point where the evidence doesn't yet support a confident read."),
    ]:
        with st.container(border=True):
            cols = st.columns([1, 4])
            with cols[0]:
                claim_type_badge(ct)
            with cols[1]:
                st.write(description)

    section_header("Freshness")
    st.write("Evidence is labeled by how recently it was retrieved:")
    freshness_cols = st.columns(3)
    for col, label, color in zip(freshness_cols, ["Fresh", "Aging", "Stale"], ["green", "yellow", "gray"]):
        with col:
            st.badge(label, color=color)

    section_header("What this app does not do")
    st.write(
        "EevaResearch does not execute trades, move money, or give personalized investment advice. "
        "It never says buy/sell/hold and never gives a price target. Rotation and signal reads are "
        "evidence-based research inputs, not trading recommendations — you make all final investment decisions."
    )

    section_header("Phase 1 — Foundation (this build)")
    st.write(
        "Application foundation, data model, navigation, UI system, and mock/demo data only. No real "
        "ticker coverage, no paid APIs, no autonomous research loops, no live news ingestion, no "
        "trading integrations, and no LLM wiring. See MIGRATION_NOTES.md and IMPLEMENTATION_NOTES.md "
        "in the repository for the full detail."
    )

    section_header("Phase 2 — Data integration (planned)")
    st.write(
        "Real evidence ingestion and market-data providers wired in behind the existing repository "
        "interfaces (src/data_access/interfaces.py) — no page-rendering code changes required. See "
        "IMPLEMENTATION_NOTES.md for the specific plan."
    )

    section_header("Phase 3 — Curated ticker universe (planned)")
    st.write(
        "A real, curated ticker universe replacing the single demo ticker, populated through the same "
        "TickerRepository interface. See IMPLEMENTATION_NOTES.md for the specific plan."
    )
