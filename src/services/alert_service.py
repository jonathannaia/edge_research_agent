"""Local alerts and review queue (guardrail area #6).

Alerts are only ever created by run_alert_checks(), called on-demand from
the Alerts page (a button), never on a background timer — this keeps the
MVP's cost/complexity bounded per guardrail #10 (no uncontrolled loops).
Nothing here sends an external message; everything surfaces inside the app.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Optional

from src.config.settings import Settings


def _alert_exists(conn: sqlite3.Connection, rule_type: str, ticker: Optional[str], message: str) -> bool:
    row = conn.execute(
        "SELECT id FROM alerts WHERE rule_type = ? AND IFNULL(ticker,'') = IFNULL(?, '') AND message = ? "
        "AND status IN ('open', 'snoozed')",
        (rule_type, ticker, message),
    ).fetchone()
    return row is not None


def _create_alert(conn: sqlite3.Connection, rule_type: str, message: str, severity: str, ticker: Optional[str] = None) -> bool:
    if _alert_exists(conn, rule_type, ticker, message):
        return False
    conn.execute(
        "INSERT INTO alerts (ticker, rule_type, message, severity) VALUES (?, ?, ?, ?)",
        (ticker, rule_type, message, severity),
    )
    return True


def run_alert_checks(
    conn: sqlite3.Connection,
    settings: Settings,
    catalyst_days_ahead: int = 14,
    note_stale_days: int = 30,
) -> int:
    created = 0
    today = date.today()

    watchlist = conn.execute("SELECT * FROM watchlist_records WHERE is_active = 1").fetchall()
    for w in watchlist:
        ticker = w["ticker"]

        if w["next_catalyst_date"]:
            try:
                days_out = (date.fromisoformat(w["next_catalyst_date"]) - today).days
                if 0 <= days_out <= catalyst_days_ahead:
                    msg = f"{w['next_catalyst'] or 'Catalyst'} in {days_out} day(s) ({w['next_catalyst_date']})."
                    created += _create_alert(conn, "catalyst_upcoming", msg, "info", ticker)
            except ValueError:
                pass

        if w["risk_flags"]:
            for flag in [f.strip() for f in w["risk_flags"].split(",") if f.strip()]:
                msg = f"Material risk flag: {flag}."
                created += _create_alert(conn, "material_risk_flag", msg, "warning", ticker)

        latest_source = conn.execute(
            "SELECT MAX(source_date) AS d FROM sources WHERE ticker = ?", (ticker,)
        ).fetchone()
        if latest_source and latest_source["d"]:
            try:
                age = (today - date.fromisoformat(latest_source["d"])).days
                if age > settings.freshness_stale_days:
                    msg = f"Most recent source is {age} days old (stale threshold {settings.freshness_stale_days}d)."
                    created += _create_alert(conn, "freshness_exceeded", msg, "warning", ticker)
            except ValueError:
                pass

        scorecards = conn.execute(
            "SELECT total_score, created_at FROM scorecards WHERE ticker = ? ORDER BY id DESC LIMIT 2", (ticker,)
        ).fetchall()
        if len(scorecards) == 2:
            delta = scorecards[0]["total_score"] - scorecards[1]["total_score"]
            if abs(delta) >= 1.0:
                msg = f"Conviction score moved {delta:+.1f} points since prior brief."
                created += _create_alert(conn, "score_move", msg, "info", ticker)

        watchlist_changes = conn.execute(
            "SELECT payload_json FROM audit_logs WHERE ticker = ? AND event_type = 'watchlist_change' "
            "ORDER BY id DESC LIMIT 5",
            (ticker,),
        ).fetchall()
        for row in watchlist_changes:
            import json as _json

            payload = _json.loads(row["payload_json"])
            change = payload.get("changes", {}).get("evidence_status")
            if change and change.get("old") == "Strengthening" and change.get("new") == "Weakening":
                msg = "Thesis evidence moved from Strengthening to Weakening."
                created += _create_alert(conn, "thesis_weakening", msg, "warning", ticker)
                break

        briefs = conn.execute(
            "SELECT bottom_line, created_at FROM research_briefs WHERE ticker = ? ORDER BY id DESC LIMIT 2", (ticker,)
        ).fetchall()
        if len(briefs) == 2 and briefs[0]["bottom_line"] != briefs[1]["bottom_line"]:
            msg = f"Bottom line changed: '{briefs[1]['bottom_line']}' -> '{briefs[0]['bottom_line']}'."
            created += _create_alert(conn, "bottom_line_change", msg, "info", ticker)

        recent_insider_sources = conn.execute(
            "SELECT id, title FROM sources WHERE ticker = ? AND source_type = 'Insider/Ownership Filing' "
            "AND retrieval_date = ?",
            (ticker, today.isoformat()),
        ).fetchall()
        for s in recent_insider_sources:
            msg = f"New insider filing retrieved: {s['title']} (source #{s['id']})."
            created += _create_alert(conn, "new_insider_filing", msg, "info", ticker)

        recent_filing_sources = conn.execute(
            "SELECT id, title FROM sources WHERE ticker = ? AND source_type = 'Regulatory Filing' AND retrieval_date = ?",
            (ticker, today.isoformat()),
        ).fetchall()
        for s in recent_filing_sources:
            msg = f"New regulatory filing retrieved: {s['title']} (source #{s['id']})."
            created += _create_alert(conn, "new_sec_filing", msg, "info", ticker)

    stale_cutoff = (today - timedelta(days=note_stale_days)).isoformat()
    stale_notes = conn.execute(
        "SELECT id, ticker, created_at FROM notes WHERE created_at < ? ORDER BY created_at ASC", (stale_cutoff,)
    ).fetchall()
    for n in stale_notes:
        msg = f"Note #{n['id']} has not been reviewed in {note_stale_days}+ days."
        created += _create_alert(conn, "note_not_reviewed", msg, "info", n["ticker"])

    return created


def list_alerts(conn: sqlite3.Connection, status: Optional[str] = None) -> list[sqlite3.Row]:
    if status:
        return conn.execute(
            "SELECT * FROM alerts WHERE status = ? ORDER BY created_at DESC", (status,)
        ).fetchall()
    return conn.execute("SELECT * FROM alerts ORDER BY created_at DESC").fetchall()


def set_alert_status(conn: sqlite3.Connection, alert_id: int, status: str, snooze_until: Optional[str] = None) -> None:
    conn.execute(
        "UPDATE alerts SET status = ?, snooze_until = ?, updated_at = datetime('now') WHERE id = ?",
        (status, snooze_until, alert_id),
    )
