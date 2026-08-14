"""Shared Streamlit UI building blocks used across pages."""
from __future__ import annotations

from typing import Any

import streamlit as st

from src.utils.export import SECTION_TITLES, fact_line
from src.utils.formatting import freshness_badge

# Substring-matches on `kind`/`data-testid` (not exact matches) because
# Streamlit gives form-submit buttons kind="primaryFormSubmit" /
# "secondaryFormSubmit" rather than plain "primary"/"secondary" — this
# catches every actual action button (including inside st.form) while
# still excluding chrome buttons like header/icon/toolbar controls.
_BUTTON_GLOW_CSS = """
<style>
button[kind*="primary"], button[kind*="secondary"],
button[data-testid*="stBaseButton-primary"], button[data-testid*="stBaseButton-secondary"],
button[data-testid*="baseButton-primary"], button[data-testid*="baseButton-secondary"] {
    transition: box-shadow 0.25s ease, transform 0.15s ease;
}

button[kind*="primary"], button[data-testid*="stBaseButton-primary"],
button[data-testid*="baseButton-primary"] {
    box-shadow: 0 0 14px rgba(88, 166, 255, 0.45);
}
button[kind*="primary"]:hover, button[data-testid*="stBaseButton-primary"]:hover,
button[data-testid*="baseButton-primary"]:hover {
    box-shadow: 0 0 22px rgba(88, 166, 255, 0.7);
    transform: translateY(-1px);
}

button[kind*="secondary"], button[data-testid*="stBaseButton-secondary"],
button[data-testid*="baseButton-secondary"] {
    box-shadow: 0 0 8px rgba(88, 166, 255, 0.15);
}
button[kind*="secondary"]:hover, button[data-testid*="stBaseButton-secondary"]:hover,
button[data-testid*="baseButton-secondary"]:hover {
    box-shadow: 0 0 14px rgba(88, 166, 255, 0.3);
    transform: translateY(-1px);
}
</style>
"""


def inject_button_glow() -> None:
    st.markdown(_BUTTON_GLOW_CSS, unsafe_allow_html=True)


TIER_BADGES = {
    "Active Research": "Active Research",
    "Watch Closely": "Watch Closely",
    "Avoid / Broken Thesis": "Avoid / Broken Thesis",
}

EVIDENCE_BADGES = {
    "Strengthening": "Strengthening",
    "Unchanged": "Unchanged",
    "Weakening": "Weakening",
    "Insufficient evidence": "Insufficient evidence",
}

CONFIDENCE_BADGES = {"Low": "Low", "Medium": "Medium", "High": "High"}

BOTTOM_LINE_BADGES = {
    "Bullish setup": "Bullish setup",
    "Bearish setup": "Bearish setup",
    "Mixed setup": "Mixed setup",
    "Insufficient evidence": "Insufficient evidence",
}

APP_DISCLAIMER = (
    "**Edge Research Agent** organizes and cites evidence to help you research potential business "
    "inflections. It does **not** execute trades, move money, or give personalized investment advice. "
    "It never says buy/sell/hold or gives a price target — only evidence-based bull/bear/mixed setups. "
    "You make all final investment decisions."
)


def render_top_disclaimer() -> None:
    st.caption(APP_DISCLAIMER)


def navigate_to(page_name: str, ticker: str | None = None) -> None:
    """Requests a page change from inside a page's own render() function.

    Streamlit forbids writing to a widget-bound session_state key (here,
    the sidebar radio's "nav_page") after that widget has already been
    instantiated in the current script run — which a button click always
    is, since the sidebar renders before the page body. So this stages the
    request in a separate key; app.py applies it to "nav_page" at the top
    of the *next* run, before the radio widget is created.
    """
    st.session_state["_requested_page"] = page_name
    if ticker:
        st.session_state["selected_ticker"] = ticker
    st.rerun()


def tier_badge(tier: str) -> str:
    return TIER_BADGES.get(tier, tier)


def evidence_badge(status: str) -> str:
    return EVIDENCE_BADGES.get(status, status)


def confidence_badge(level: str) -> str:
    return CONFIDENCE_BADGES.get(level, level)


def bottom_line_badge(value: str) -> str:
    return BOTTOM_LINE_BADGES.get(value, value)


def render_mock_badge(is_mock: bool) -> None:
    if is_mock:
        st.warning("MOCK DATA — synthetic/fictional, for demo purposes only. Not real financials.")


def render_scorecard(scorecard: dict[str, Any]) -> None:
    st.metric("Total conviction score", f"{scorecard.get('total_score', 0):.1f} / 5")
    if scorecard.get("is_capped"):
        st.error(f"Score capped: {scorecard.get('cap_reason')}")
    components = scorecard.get("components", [])
    if not components:
        return
    st.caption(
        "Formula: total = Σ(weight × raw_score) across components below, weights normalized to sum to 1.0. "
        "A poor evidence-quality score caps the total regardless of other components. "
        "This is a research aid, not investment advice or a prediction."
    )
    for c in components:
        with st.expander(f"{c['label']} — {c['raw_score']}/5 (weight {c['weight']:.0%}, weighted {c['weighted_score']:.2f})"):
            st.write(c["explanation"])
            if c.get("citation_source_ids"):
                st.caption(f"Cited sources: {', '.join('#' + str(s) for s in c['citation_source_ids'])}")


def render_brief_sections(sections: dict[str, Any]) -> None:
    st.subheader(bottom_line_badge(sections.get("bottom_line", "")))
    st.write(f"**Confidence:** {confidence_badge(sections.get('confidence_level', ''))} — {sections.get('confidence_explanation', '')}")

    what_changed = sections.get("what_changed_recently") or {}
    if any(what_changed.values()):
        st.markdown("### What Changed Since Last Review?")
        cols = st.columns(4)
        labels = [("confirming", "Confirming"), ("disconfirming", "Disconfirming"), ("neutral", "Neutral"), ("new_unknowns", "New Unknowns")]
        for col, (key, label) in zip(cols, labels):
            with col:
                st.markdown(f"**{label}**")
                for item in what_changed.get(key, []):
                    st.write(f"- {item}")
                if not what_changed.get(key):
                    st.caption("None")

    skip_keys = {"bottom_line", "confidence_level", "confidence_explanation", "what_changed_recently", "sources_table", "scorecard", "data_freshness"}
    for key, title in SECTION_TITLES:
        if key in skip_keys:
            continue
        value = sections.get(key)
        if value in (None, "", [], {}):
            continue
        st.markdown(f"### {title}")
        if isinstance(value, list):
            for item in value:
                st.write(f"- {fact_line(item) if isinstance(item, dict) else item}")
        elif isinstance(value, dict):
            st.write(fact_line(value))
        else:
            st.write(value)

    freshness = sections.get("data_freshness") or {}
    if freshness:
        st.markdown("### Data Freshness")
        st.write(
            f"{freshness.get('n_sources', 0)} source(s) reviewed; "
            f"{freshness.get('stale_or_very_stale_count', 0)} flagged stale or very stale "
            f"(thresholds: fresh ≤{freshness.get('freshness_thresholds_days', {}).get('fresh')}d, "
            f"stale >{freshness.get('freshness_thresholds_days', {}).get('stale')}d)."
        )

    sources = sections.get("sources_table") or []
    if sources:
        st.markdown("### Sources")
        st.dataframe(
            [
                {
                    "#": s["source_id"], "Type": s["source_type"], "Title": s["title"],
                    "Source Date": s["source_date"], "Retrieved": s["retrieval_date"],
                    "Freshness": freshness_badge(s["freshness_status"]), "Identifier / URL": s["url_or_identifier"],
                }
                for s in sources
            ],
            width='stretch', hide_index=True,
        )

    scorecard = sections.get("scorecard")
    if scorecard:
        st.markdown("### Full Scorecard")
        render_scorecard(scorecard)
