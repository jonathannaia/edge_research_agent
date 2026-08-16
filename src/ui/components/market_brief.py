"""Today's Read — a single, compact editorial card on Overview, replacing
the earlier 4-panel bento Market Brief. Round 2's Overview brief calls for
"one concise Today's Read / rotation card" only; the research-attention,
catalyst, and invalidation panels this file used to hold now live
permanently on Capital Rotation / Signal Board, not previewed here.

The read itself is still an Interpretation, never a Fact — a synthesis
across multiple demo data points, not a single sourced statement.
"""
from __future__ import annotations

import streamlit as st

from src.data_access.container import AppContext
from src.logic.formatting import fmt_pct
from src.logic.theme_metrics import leaders_and_laggards
from src.models.models import ClaimType
from src.ui.ui import get_page
from src.ui.components.badges import claim_type_badge, demo_badge


def render_todays_read(ctx: AppContext) -> None:
    themes = {t.slug: t for t in ctx.theme_repository.get_all_themes()}
    metrics = ctx.market_data_provider.get_rotation_metrics()
    leaders, laggards = leaders_and_laggards(metrics, top_n=2)

    with st.container(border=True, key="card-todays-read"):
        top = st.columns([3, 1, 1])
        top[0].markdown('<div class="er-card-title">Today\'s Read</div>', unsafe_allow_html=True)
        with top[1]:
            claim_type_badge(ClaimType.INTERPRETATION)
        with top[2]:
            demo_badge()

        if leaders and laggards:
            lead_names = ", ".join(themes[m.theme_slug].name for m in leaders if m.theme_slug in themes)
            lag_names = ", ".join(themes[m.theme_slug].name for m in laggards if m.theme_slug in themes)
            lead_vals = ", ".join(fmt_pct(m.relative_performance_pct) for m in leaders)
            st.write(f"**{lead_names}** lead this demo snapshot ({lead_vals}); **{lag_names}** show the weakest reads.")
        else:
            st.caption("Not enough theme data yet.")

        page = get_page("capital_rotation")
        if page is not None:
            with st.container(key="cta-tertiary-todays-read"):
                st.page_link(page, label="Open Capital Rotation →")
