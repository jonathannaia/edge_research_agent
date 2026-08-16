"""Signal Board — structured, filterable view of every tracked signal.
All signals are demo data (data/seed/signals.json)."""
from __future__ import annotations

import streamlit as st

from src.data_access.container import get_repositories
from src.ui.chrome import get_page
from src.ui.components.cards import signal_card
from src.ui.components.empty_state import empty_state


def render() -> None:
    ctx = get_repositories()
    themes = {t.slug: t.name for t in ctx.theme_repository.get_all_themes()}
    signals = ctx.signal_repository.get_all_signals()

    st.markdown('<div class="er-page-title">Signal Board</div>', unsafe_allow_html=True)
    st.write("Every tracked signal in one place — demo data in this phase, filterable by theme, direction, strength, and time horizon.")

    if not signals:
        empty_state("No signals loaded.")
        return

    filter_cols = st.columns(4)
    theme_filter = filter_cols[0].multiselect("Theme", sorted(themes.values()))
    direction_filter = filter_cols[1].multiselect("Direction", sorted({s.direction.value for s in signals}))
    strength_filter = filter_cols[2].multiselect("Strength", sorted({s.strength.value for s in signals}))
    horizon_filter = filter_cols[3].multiselect("Time horizon", sorted({s.horizon.value for s in signals}))

    filtered = signals
    if theme_filter:
        name_to_slug = {v: k for k, v in themes.items()}
        slugs = {name_to_slug[n] for n in theme_filter}
        filtered = [s for s in filtered if s.theme_slug in slugs]
    if direction_filter:
        filtered = [s for s in filtered if s.direction.value in direction_filter]
    if strength_filter:
        filtered = [s for s in filtered if s.strength.value in strength_filter]
    if horizon_filter:
        filtered = [s for s in filtered if s.horizon.value in horizon_filter]

    st.caption(f"{len(filtered)} of {len(signals)} signals shown.")
    if not filtered:
        empty_state("No signals match the current filters.")
        return

    theme_page = get_page("themes")
    for s in filtered:
        signal_card(s, theme_page=theme_page)
