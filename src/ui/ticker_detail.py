from __future__ import annotations

import json

import streamlit as st

from src.config.settings import Settings
from src.database.db import get_connection
from src.guardrails.language_filters import warn_no_advice_language
from src.radar import snapshots as radar_snapshots
from src.radar import store as radar_store
from src.services import audit_service, notes_service, thesis_service, ticker_service, watchlist_service
from src.ui.components import render_brief_sections, render_mock_badge, render_radar_finding_card, render_ticker_snapshot


def render(settings: Settings) -> None:
    with get_connection(settings) as conn:
        tickers = [t["ticker"] for t in ticker_service.list_tickers(conn)]
        if not tickers:
            st.info("No tickers exist yet. Add one from the Watchlist page.")
            return

        default_ticker = st.session_state.get("selected_ticker", tickers[0])
        if default_ticker not in tickers:
            default_ticker = tickers[0]
        ticker = st.selectbox("Ticker", tickers, index=tickers.index(default_ticker))
        st.session_state["selected_ticker"] = ticker

        t = ticker_service.get_ticker(conn, ticker)
        w = watchlist_service.get_watchlist_record(conn, ticker)
        thesis = thesis_service.get_current_thesis(conn, ticker)

        render_mock_badge(bool(t["is_mock"]))
        st.header(f"{ticker} — {t['company_name']}")
        st.caption(f"{t['sector']} · {t['subtheme']} · {t['market_cap_category']} · {t['jurisdiction']}")

        if w:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tier", w["tier"])
            c2.metric("Conviction score", f"{w['conviction_score']}/5")
            c3.metric("Evidence status", w["evidence_status"])
            c4.metric("Date added", w["date_added"][:10] if w["date_added"] else "—")

        radar_findings = radar_store.find_for_ticker(ticker)
        radar_tab_label = f"Radar Mentions ({len(radar_findings)})" if radar_findings else "Radar Mentions"
        tabs = st.tabs(["Thesis Record", "Research Briefs", "Change Log", "Notes", radar_tab_label])

        with tabs[0]:
            if not thesis:
                st.info("No thesis record yet.")
            else:
                st.subheader("Inflection thesis")
                st.write(thesis["inflection_thesis"])
                st.caption(f"Theme: {thesis['theme']} · Created: {thesis['thesis_date_created'][:10]} · Version {thesis['version']}")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Confirmation conditions**")
                    st.write(thesis["confirmation_conditions"] or "—")
                    st.markdown("**Key risks**")
                    st.write(thesis["key_risks"] or "—")
                with col2:
                    st.markdown("**Invalidation conditions**")
                    st.write(thesis["invalidation_conditions"] or "—")
                    st.markdown("**Next catalyst**")
                    st.write(f"{thesis['next_catalyst'] or '—'} ({thesis['next_catalyst_date'] or '—'})")

                st.markdown("**Owner notes**")
                st.write(thesis["thesis_owner_notes"] or "—")
                st.markdown("**Tags**")
                st.write(thesis["tags"] or "—")

                with st.expander("Prior thesis versions"):
                    for v in thesis_service.list_thesis_versions(conn, ticker):
                        st.write(f"v{v['version']} ({v['thesis_date_created'][:10]}, tier={v['tier']}, score={v['score']}): {v['inflection_thesis']}")

            with st.expander("Edit thesis (creates a new version)"):
                with st.form("edit_thesis_form"):
                    inflection_thesis = st.text_area("Inflection thesis", value=thesis["inflection_thesis"] if thesis else "")
                    owner_notes = st.text_area("Owner notes", value=thesis["thesis_owner_notes"] if thesis else "")
                    confirmation = st.text_area("Confirmation conditions", value=thesis["confirmation_conditions"] if thesis else "")
                    invalidation = st.text_area("Invalidation conditions", value=thesis["invalidation_conditions"] if thesis else "")
                    key_risks = st.text_area("Key risks", value=thesis["key_risks"] if thesis else "")
                    tags = st.text_input("Tags (comma separated)", value=thesis["tags"] if thesis else "")
                    if st.form_submit_button("Save new thesis version"):
                        warnings = warn_no_advice_language(inflection_thesis + " " + owner_notes)
                        thesis_service.save_thesis(
                            conn, ticker=ticker, theme=thesis["theme"] if thesis else t["subtheme"],
                            subtheme=t["subtheme"], why_on_watchlist=w["why_on_watchlist"] if w else "",
                            inflection_thesis=inflection_thesis, thesis_owner_notes=owner_notes,
                            evidence_supporting=json.loads(thesis["evidence_supporting"]) if thesis else [],
                            evidence_contradicting=json.loads(thesis["evidence_contradicting"]) if thesis else [],
                            confirmation_conditions=confirmation, invalidation_conditions=invalidation,
                            key_risks=key_risks, next_catalyst=w["next_catalyst"] if w else None,
                            next_catalyst_date=w["next_catalyst_date"] if w else None,
                            tier=w["tier"] if w else "Watch Closely", score=float(w["conviction_score"]) if w else 3.0,
                            tags=tags,
                        )
                        if warnings:
                            st.warning(f"Note: your text contains advice-style language ({warnings}) — this is your own note and was saved as-is, but the system's own generated content is never allowed to include this.")
                        st.success("New thesis version saved.")
                        st.rerun()

        with tabs[1]:
            briefs = conn.execute(
                "SELECT * FROM research_briefs WHERE ticker = ? ORDER BY version DESC", (ticker,)
            ).fetchall()
            if not briefs:
                st.info("No research briefs yet. Generate one from 'New Research Brief'.")
            for b in briefs:
                with st.expander(f"Brief v{b['version']} — {b['bottom_line']} ({b['confidence_level']} confidence) — {b['created_at'][:16]}"):
                    sections = json.loads(b["sections_json"])
                    render_brief_sections(sections)

        with tabs[2]:
            events = audit_service.list_events_for_ticker(
                conn, ticker, event_types=["watchlist_change", "thesis_updated", "research_brief_generated"], limit=100
            )
            if not events:
                st.info("No changes logged yet.")
            for e in events:
                payload = json.loads(e["payload_json"])
                st.write(f"**{e['created_at']}** — `{e['event_type']}`")
                st.json(payload, expanded=False)

        with tabs[3]:
            with st.form("add_note_form", clear_on_submit=True):
                note_text = st.text_area("New note")
                note_tags = st.text_input("Tags (comma separated)")
                if st.form_submit_button("Add note"):
                    if note_text.strip():
                        _id, warnings = notes_service.add_note(conn, ticker, note_text, note_tags)
                        if warnings:
                            st.warning(f"Advice-style language detected in your note ({warnings}) — saved as-is since this is your private note.")
                        st.success("Note added.")
                        st.rerun()
            for n in notes_service.list_notes(conn, ticker):
                tag_suffix = f" ({n['tags']})" if n["tags"] else ""
                st.markdown(f"**{n['created_at'][:16]}**{tag_suffix}")
                st.write(n["note_text"])
                st.divider()

        with tabs[4]:
            st.caption(
                "Autonomous findings from Radar that tag this ticker — separate from your manual "
                "research above. Radar runs unattended with no human review; read the source before "
                "acting on anything. See the Radar page for the full feed across all tracked niches."
            )

            snapshot = radar_snapshots.load_snapshots().get(ticker.upper())
            if snapshot:
                st.markdown("### Auto-tracked snapshot")
                render_ticker_snapshot(snapshot)
                st.divider()
            elif t["jurisdiction"] == "United States":
                st.caption(
                    "No auto-tracked snapshot yet — Radar only snapshots US tickers it tags itself, or "
                    "ones listed in `data/tracked_tickers.json`. Add this ticker there to get automatic "
                    "price/insider/news refreshes even if Radar's own niches never mention it."
                )

            st.markdown("### Radar findings mentioning this ticker")
            if not radar_findings:
                st.info("No Radar findings mention this ticker yet.")
            for f in radar_findings:
                render_radar_finding_card(f)
