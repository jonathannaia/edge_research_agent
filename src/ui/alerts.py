from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from src.config.settings import Settings
from src.database.db import get_connection
from src.services import alert_service

SEVERITY_LABEL = {"info": "Info", "warning": "Warning"}


def render(settings: Settings) -> None:
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        catalyst_days = st.number_input("Catalyst alert window (days)", min_value=1, value=14)
    with c2:
        note_stale_days = st.number_input("Note staleness threshold (days)", min_value=1, value=30)
    with c3:
        st.write("")
        if st.button("Run alert checks now", type="primary"):
            with get_connection(settings) as conn:
                n = alert_service.run_alert_checks(conn, settings, catalyst_days, note_stale_days)
            st.success(f"Alert check complete — {n} new alert(s) created.")
            st.rerun()

    st.caption(
        "Alerts are only created when you click the button above — this app never runs background jobs "
        "or sends external notifications. Everything stays local."
    )

    status_filter = st.radio("Status", ["open", "reviewed", "snoozed", "archived"], horizontal=True)

    with get_connection(settings) as conn:
        alerts = alert_service.list_alerts(conn, status=status_filter)

        if not alerts:
            st.info(f"No {status_filter} alerts.")
            return

        for a in alerts:
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**[{a['ticker'] or 'general'}] {SEVERITY_LABEL.get(a['severity'], a['severity'])}** — {a['rule_type']}")
                    st.write(a["message"])
                    st.caption(f"Created {a['created_at']}" + (f" · snoozed until {a['snooze_until']}" if a["snooze_until"] else ""))
                with col2:
                    if a["status"] != "reviewed" and st.button("Mark reviewed", key=f"rev_{a['id']}"):
                        alert_service.set_alert_status(conn, a["id"], "reviewed")
                        st.rerun()
                    if a["status"] != "snoozed" and st.button("Snooze 7d", key=f"snz_{a['id']}"):
                        alert_service.set_alert_status(conn, a["id"], "snoozed", (date.today() + timedelta(days=7)).isoformat())
                        st.rerun()
                    if a["status"] != "archived" and st.button("Archive", key=f"arc_{a['id']}"):
                        alert_service.set_alert_status(conn, a["id"], "archived")
                        st.rerun()
