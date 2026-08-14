from __future__ import annotations

from datetime import date

import streamlit as st

from src.config.settings import Settings
from src.database.db import get_connection
from src.models.models import EvidenceStatus, Jurisdiction, Tier
from src.services import thesis_service, ticker_service, watchlist_service
from src.ui.components import evidence_badge, navigate_to, render_mock_badge, tier_badge


def _add_ticker_form(conn, settings: Settings) -> None:
    with st.expander("Add a ticker to the watchlist", expanded=False):
        if len(watchlist_service.list_watchlist(conn)) >= settings.max_watchlist_size:
            st.warning(f"Watchlist is at the MVP soft limit of {settings.max_watchlist_size} tickers.")
        with st.form("add_ticker_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                ticker = st.text_input("Ticker *").upper().strip()
                company_name = st.text_input("Company name *")
                sector = st.text_input("Sector", value="Technology Hardware & Components")
                subtheme = st.text_input("Subtheme", value="")
                market_cap = st.selectbox("Market cap category", ["Micro Cap", "Small Cap", "Mid Cap", "Large Cap"])
                jurisdiction = st.selectbox(
                    "Jurisdiction (primary regulator)", [j.value for j in Jurisdiction],
                    help="Which regulator this ticker's filings come from — SEC EDGAR (US), EDINET (Japan), "
                    "DART (Korea), or CNINFO/HKEXnews (China/Hong Kong). Informational in mock mode; used to "
                    "route to the right live filings provider once one is wired up.",
                )
            with col2:
                tier = st.selectbox("Tier", [t.value for t in Tier], index=1)
                conviction_score = st.slider("Conviction score", 1, 5, 3)
                evidence_status = st.selectbox("Evidence status", [e.value for e in EvidenceStatus], index=3)
                next_catalyst = st.text_input("Next catalyst")
                next_catalyst_date = st.date_input("Next catalyst date", value=None)

            thesis_short = st.text_area("Inflection thesis (1-3 sentences) *", max_chars=500)
            why_on_watchlist = st.text_area("Why it's on the watchlist *", max_chars=500)
            key_confirmation = st.text_input("Key confirmation metric")
            key_invalidation = st.text_input("Key invalidation metric")

            submitted = st.form_submit_button("Add to watchlist")
            if submitted:
                if not ticker or not company_name or not thesis_short or not why_on_watchlist:
                    st.error("Ticker, company name, thesis, and 'why on watchlist' are required.")
                else:
                    ticker_service.upsert_ticker(
                        conn, ticker, company_name, sector, subtheme, market_cap,
                        jurisdiction=jurisdiction, is_mock=True,
                    )
                    watchlist_service.upsert_watchlist_record(
                        conn, ticker=ticker, tier=tier, thesis_short=thesis_short,
                        why_on_watchlist=why_on_watchlist, conviction_score=conviction_score,
                        evidence_status=evidence_status, next_catalyst=next_catalyst or None,
                        next_catalyst_date=next_catalyst_date.isoformat() if next_catalyst_date else None,
                        key_confirmation_metric=key_confirmation or None,
                        key_invalidation_metric=key_invalidation or None,
                        reason="Added to watchlist",
                    )
                    thesis_service.save_thesis(
                        conn, ticker=ticker, theme=subtheme, subtheme=subtheme,
                        why_on_watchlist=why_on_watchlist, inflection_thesis=thesis_short,
                        thesis_owner_notes="", evidence_supporting=[], evidence_contradicting=[],
                        confirmation_conditions=key_confirmation or "", invalidation_conditions=key_invalidation or "",
                        key_risks="", next_catalyst=next_catalyst or None,
                        next_catalyst_date=next_catalyst_date.isoformat() if next_catalyst_date else None,
                        tier=tier, score=float(conviction_score), tags="",
                    )
                    st.success(f"Added {ticker} to the watchlist.")
                    st.rerun()


def render(settings: Settings) -> None:
    st.caption(
        "Add and manage the companies you're tracking here — tier, thesis, and confirmation/"
        "invalidation metrics. To actually pull evidence and generate a scored, cited research "
        "brief for one of these tickers, go to **New Research Brief**."
    )
    with get_connection(settings) as conn:
        _add_ticker_form(conn, settings)

        watchlist = watchlist_service.list_watchlist(conn)
        if not watchlist:
            st.info("No tickers yet — add one above.")
            return

        st.subheader("Filters")
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            search = st.text_input("Search ticker or company")
        with f2:
            tiers = st.multiselect("Tier", [t.value for t in Tier], default=[])
        with f3:
            evidence_filter = st.multiselect("Evidence status", [e.value for e in EvidenceStatus], default=[])
        with f4:
            sectors = sorted({w["sector"] for w in watchlist})
            sector_filter = st.multiselect("Sector", sectors, default=[])

        f5, f6, f7 = st.columns(3)
        with f5:
            min_score = st.slider("Minimum score", 1, 5, 1)
        with f6:
            catalyst_window = st.number_input("Catalyst within N days (0 = ignore)", min_value=0, value=0, step=5)
        with f7:
            risk_only = st.checkbox("Only show tickers with risk flags")

        rows = list(watchlist)
        if search:
            s = search.lower()
            rows = [w for w in rows if s in w["ticker"].lower() or s in w["company_name"].lower()]
        if tiers:
            rows = [w for w in rows if w["tier"] in tiers]
        if evidence_filter:
            rows = [w for w in rows if w["evidence_status"] in evidence_filter]
        if sector_filter:
            rows = [w for w in rows if w["sector"] in sector_filter]
        rows = [w for w in rows if w["conviction_score"] >= min_score]
        if risk_only:
            rows = [w for w in rows if w["risk_flags"]]
        if catalyst_window > 0:
            def _within(w):
                if not w["next_catalyst_date"]:
                    return False
                try:
                    return 0 <= (date.fromisoformat(w["next_catalyst_date"]) - date.today()).days <= catalyst_window
                except ValueError:
                    return False
            rows = [w for w in rows if _within(w)]

        st.subheader(f"Watchlist ({len(rows)} of {len(watchlist)})")
        for w in rows:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 3, 2, 1])
                with c1:
                    st.markdown(f"**{w['ticker']}** — {w['company_name']}")
                    st.caption(f"{w['sector']} · {w['subtheme']} · {w['market_cap_category']} · {w['jurisdiction']}")
                    render_mock_badge(bool(w["is_mock"]))
                with c2:
                    st.write(w["thesis_short"])
                    st.caption(f"Next catalyst: {w['next_catalyst'] or '—'} ({w['next_catalyst_date'] or '—'})")
                    if w["risk_flags"]:
                        st.caption(f"Risk flags: {w['risk_flags']}")
                with c3:
                    st.write(tier_badge(w["tier"]))
                    st.write(evidence_badge(w["evidence_status"]))
                    st.write(f"Score: **{w['conviction_score']}/5**")
                with c4:
                    if st.button("View", key=f"view_{w['ticker']}"):
                        navigate_to("Ticker Detail", w["ticker"])
                    if st.button("Remove", key=f"remove_{w['ticker']}"):
                        watchlist_service.deactivate(conn, w["ticker"])
                        st.rerun()
