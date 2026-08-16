"""Capital Rotation — where theme leadership and attention are shifting.
All figures are demo data (data/seed/rotation_metrics.json). Rotation
narrative cards use the "What changed / Why it may matter / Evidence / What
would invalidate this read" pattern throughout, and every read here is
Interpretation or Inference, never presented as a trading recommendation.
"""
from __future__ import annotations

import streamlit as st

from src.data_access.container import get_repositories
from src.logic.formatting import fmt_date, fmt_pct
from src.logic.theme_metrics import average_breadth, leaders_and_laggards, rank_by_performance
from src.models.models import ClaimType
from src.ui.ui import get_page
from src.ui.components.badges import claim_type_badge
from src.ui.components.cards import catalyst_timeline_row
from src.ui.components.charts import rotation_bar_chart
from src.ui.components.empty_state import empty_state
from src.ui.components.section import section_header
from src.ui.components.tables import leaderboard_table


def _rotation_narrative_card(title: str, what_changed: str, why_it_matters: str, evidence: str, invalidation: str) -> None:
    with st.container(border=True, key="card-rotation-narrative"):
        top = st.columns([4, 1])
        top[0].markdown(f'<div class="er-card-title">{title}</div>', unsafe_allow_html=True)
        with top[1]:
            claim_type_badge(ClaimType.INTERPRETATION)
        st.markdown(f"**What changed**\n\n{what_changed}")
        st.markdown(f"**Why it may matter**\n\n{why_it_matters}")
        st.markdown(f"**Evidence**\n\n{evidence}")
        st.markdown(f"**What would invalidate this read**\n\n{invalidation}")


def render() -> None:
    ctx = get_repositories()
    themes = {t.slug: t for t in ctx.theme_repository.get_all_themes()}
    metrics = ctx.market_data_provider.get_rotation_metrics()

    st.markdown('<div class="er-page-title">Capital Rotation</div>', unsafe_allow_html=True)
    st.write(
        "A price-momentum-style comparison across the five tracked themes, built entirely from demo "
        "data in this phase. Rotation reads are interpretations across multiple data points, not "
        "trading recommendations — see the methodology note below."
    )

    section_header("Theme relative performance")
    ranked = rank_by_performance(metrics)
    leaderboard_table(ranked, themes)
    st.altair_chart(rotation_bar_chart(ranked, themes), width="stretch")
    if ranked and ranked[0].theme_slug in themes:
        st.markdown(
            f'<div class="er-muted">Rotation read: <strong>{themes[ranked[0].theme_slug].name}</strong> leads; '
            f'<strong>{themes[ranked[-1].theme_slug].name}</strong> is weakest. Investigate the leading theme\'s '
            "nearest catalyst below before treating this as durable.</div>",
            unsafe_allow_html=True,
        )

    section_header("Relative strength vs. benchmarks", "Placeholder — requires a live benchmark data source, not built in this phase.")
    st.dataframe(
        [{"Theme": themes[m.theme_slug].name, "RS vs. broad market": "—", "RS vs. semiconductor index": "—"} for m in ranked if m.theme_slug in themes],
        hide_index=True, width="stretch",
    )

    section_header("Breadth")
    avg = average_breadth(metrics)
    st.markdown(
        f'<div class="er-metric-label">Average breadth across themes</div>'
        f'<div class="er-metric-value" style="font-size:1.4rem;">{f"{avg:.0f}%" if avg is not None else "—"}</div>',
        unsafe_allow_html=True,
    )

    section_header("Leaders and laggards")
    leaders, laggards = leaders_and_laggards(metrics, top_n=2)
    cols = st.columns(2)
    with cols[0]:
        st.markdown('<div class="er-metric-label">Leading</div>', unsafe_allow_html=True)
        for m in leaders:
            if m.theme_slug in themes:
                st.markdown(f'<div class="er-mono">{themes[m.theme_slug].name} — {fmt_pct(m.relative_performance_pct)}</div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown('<div class="er-metric-label">Lagging</div>', unsafe_allow_html=True)
        for m in laggards:
            if m.theme_slug in themes:
                st.markdown(f'<div class="er-mono">{themes[m.theme_slug].name} — {fmt_pct(m.relative_performance_pct)}</div>', unsafe_allow_html=True)

    section_header("Rotation narrative")
    if leaders and laggards and leaders[0].theme_slug in themes and laggards[0].theme_slug in themes:
        lead_theme, lag_theme = themes[leaders[0].theme_slug], themes[laggards[0].theme_slug]
        _rotation_narrative_card(
            f"{lead_theme.name} leading, {lag_theme.name} lagging",
            f"{lead_theme.name} shows the strongest demo relative-performance read this period "
            f"({fmt_pct(leaders[0].relative_performance_pct)}); {lag_theme.name} the weakest "
            f"({fmt_pct(laggards[0].relative_performance_pct)}).",
            "A sustained leadership gap between themes is one input into where research attention "
            "and (eventually) capital may be concentrating — on its own it is not conclusive.",
            "Demo rotation_metrics.json — relative_performance_pct and breadth_pct fields.",
            "A real evidence pipeline (Phase 2) reversing this gap, or a specific sourced catalyst "
            "in the lagging theme, would invalidate this read.",
        )
    else:
        empty_state("Not enough theme data to build a rotation narrative yet.")

    section_header("Sub-theme rotation", "Framework only in this phase — subtheme-level rotation metrics aren't populated yet.")
    empty_state(
        "Sub-theme rotation isn't populated yet.",
        "Once subtheme-level metrics exist (Phase 2+), this section would show rotation within a "
        "theme (e.g. DRAM vs. HBM within Memory) using the same leaders/laggards pattern as above.",
    )

    section_header("Positioning / short interest", "Delayed and informational only — not built in this phase.")
    empty_state(
        "No positioning or short-interest data connected.",
        "This section is reserved for delayed, informational positioning data (e.g. short interest) "
        "once a real source is wired up — never real-time, and never a trading signal on its own.",
    )

    section_header("Catalyst timeline", "Full upcoming catalyst calendar across all five themes — moved here from Overview.")
    upcoming = ctx.catalyst_repository.get_upcoming_catalysts(limit=10)
    if not upcoming:
        empty_state("No catalysts scheduled.")
    else:
        for c in upcoming:
            catalyst_timeline_row(c)

    section_header("Catalysts in leading/lagging themes")
    if leaders and leaders[0].theme_slug in themes:
        lead_catalysts = ctx.catalyst_repository.get_catalysts_for_theme(leaders[0].theme_slug)
        if lead_catalysts:
            st.write(f"Nearest catalyst in {themes[leaders[0].theme_slug].name}: {lead_catalysts[0].title} ({fmt_date(lead_catalysts[0].date)}).")
        else:
            st.caption("No catalysts scheduled in the leading theme.")

    with st.expander("Methodology"):
        st.write(
            "Rotation conclusions on this page are built from demo relative-performance and breadth "
            "figures only. They require evidence to be meaningful and should never be treated as "
            "trading recommendations — EevaResearch does not provide investment advice."
        )
        page = get_page("methodology")
        if page is not None:
            with st.container(key="cta-tertiary-rotation-methodology"):
                st.page_link(page, label="Read the full evidence-first framework →")
