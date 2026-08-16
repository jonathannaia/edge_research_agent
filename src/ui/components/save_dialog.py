"""Watchlist save dialog (brief §15) — "nothing goes on a watchlist
without a written invalidation condition," enforced, not just stated.
Triggered from anywhere (Company page, the signal drawer) by setting
`st.session_state["open_save_dialog_for"] = <ticker_symbol>` and rerunning;
`render_pending_save_dialog()` is called once per page load from
`src.ui.ui.with_chrome` and opens the dialog if that flag is set.
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from src.data_access.container import get_repositories
from src.models.models import WatchlistEntry

TRIGGER_KEY = "open_save_dialog_for"

INVALIDATION_PLACEHOLDER = (
    "Domestic China routing falls below 40% of revenue, or an export permit denial is disclosed."
)


def _clear_trigger() -> None:
    st.session_state[TRIGGER_KEY] = None


def render_pending_save_dialog() -> None:
    symbol = st.session_state.get(TRIGGER_KEY)
    if not symbol:
        return

    from src.ui.pages.watchlists import SESSION_KEY, WATCHLIST_NAMES, seed_watchlists

    ctx = get_repositories()
    ticker = ctx.ticker_repository.get_ticker(symbol)

    @st.dialog(f"Save {symbol} to a watchlist", on_dismiss=_clear_trigger)
    def _dialog() -> None:
        if ticker:
            st.markdown(f'<div class="er-muted">{ticker.company_name} · {ticker.theme_slug}</div>', unsafe_allow_html=True)

        default_list = st.session_state.pop("save_dialog_default_list", None)
        default_index = WATCHLIST_NAMES.index(default_list) if default_list in WATCHLIST_NAMES else 0
        list_name = st.selectbox("Watchlist", WATCHLIST_NAMES, index=default_index, key="save-dialog-list")

        st.markdown(
            '<div style="margin-top:0.5rem;">What would invalidate this '
            '<span style="color:var(--text-3); font-size:0.75rem;">required</span></div>',
            unsafe_allow_html=True,
        )
        invalidate = st.text_area(
            "What would invalidate this", placeholder=INVALIDATION_PLACEHOLDER,
            key="save-dialog-invalidate", label_visibility="collapsed",
        )
        st.markdown(
            '<div class="er-muted" style="font-size:12px;">You\'ll be reminded of this the next time '
            "the position moves against you.</div>",
            unsafe_allow_html=True,
        )

        st.divider()
        btn_cols = st.columns(2)
        with btn_cols[0]:
            with st.container(key="cta-secondary-save-dialog-cancel"):
                if st.button("Cancel", key="save-dialog-cancel", width="stretch"):
                    _clear_trigger()
                    st.rerun()
        with btn_cols[1]:
            with st.container(key="cta-primary-save-dialog-save"):
                if st.button("Save", key="save-dialog-save", width="stretch", disabled=not invalidate.strip()):
                    if SESSION_KEY not in st.session_state:
                        st.session_state[SESSION_KEY] = seed_watchlists()
                    st.session_state[SESSION_KEY].setdefault(list_name, []).append(
                        WatchlistEntry(
                            list_name=list_name, ticker_symbol=symbol,
                            added_at=datetime.now(timezone.utc).isoformat(),
                            note="Added this session — not persisted.",
                            invalidates_if=invalidate.strip(),
                        )
                    )
                    _clear_trigger()
                    st.toast(f"Saved {symbol} to {list_name}")
                    st.rerun()

    _dialog()
