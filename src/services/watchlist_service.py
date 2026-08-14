from __future__ import annotations

import sqlite3
from typing import Optional

from src.services import audit_service


def get_watchlist_record(conn: sqlite3.Connection, ticker: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM watchlist_records WHERE ticker = ? AND is_active = 1", (ticker.upper(),)
    ).fetchone()


def list_watchlist(conn: sqlite3.Connection, active_only: bool = True) -> list[sqlite3.Row]:
    query = "SELECT w.*, t.company_name, t.sector, t.subtheme, t.market_cap_category, t.jurisdiction, t.is_mock " \
            "FROM watchlist_records w JOIN tickers t ON t.ticker = w.ticker"
    if active_only:
        query += " WHERE w.is_active = 1"
    query += " ORDER BY w.tier ASC, w.conviction_score DESC"
    return conn.execute(query).fetchall()


def upsert_watchlist_record(
    conn: sqlite3.Connection,
    ticker: str,
    tier: str,
    thesis_short: str,
    why_on_watchlist: str,
    conviction_score: int,
    evidence_status: str,
    next_catalyst: Optional[str] = None,
    next_catalyst_date: Optional[str] = None,
    key_confirmation_metric: Optional[str] = None,
    key_invalidation_metric: Optional[str] = None,
    latest_material_change: Optional[str] = None,
    reason: str = "Manual edit",
) -> None:
    ticker = ticker.upper()
    existing = get_watchlist_record(conn, ticker)

    if existing:
        changes = {}
        for field, new_val in [
            ("tier", tier),
            ("conviction_score", conviction_score),
            ("evidence_status", evidence_status),
        ]:
            old_val = existing[field]
            if str(old_val) != str(new_val):
                changes[field] = {"old": old_val, "new": new_val}

        conn.execute(
            """UPDATE watchlist_records SET
                tier = ?, thesis_short = ?, why_on_watchlist = ?, conviction_score = ?,
                evidence_status = ?, next_catalyst = ?, next_catalyst_date = ?,
                key_confirmation_metric = ?, key_invalidation_metric = ?,
                latest_material_change = ?, date_last_reviewed = datetime('now'),
                updated_at = datetime('now')
               WHERE ticker = ?""",
            (
                tier, thesis_short, why_on_watchlist, conviction_score, evidence_status,
                next_catalyst, next_catalyst_date, key_confirmation_metric,
                key_invalidation_metric, latest_material_change, ticker,
            ),
        )
        if changes:
            audit_service.log_event(
                conn, "watchlist_change", {"changes": changes, "reason": reason}, ticker=ticker
            )
    else:
        conn.execute(
            """INSERT INTO watchlist_records
                (ticker, tier, thesis_short, why_on_watchlist, conviction_score, evidence_status,
                 next_catalyst, next_catalyst_date, key_confirmation_metric, key_invalidation_metric,
                 latest_material_change)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ticker, tier, thesis_short, why_on_watchlist, conviction_score, evidence_status,
                next_catalyst, next_catalyst_date, key_confirmation_metric, key_invalidation_metric,
                latest_material_change,
            ),
        )
        audit_service.log_event(
            conn, "watchlist_change", {"changes": {"created": True, "tier": tier}, "reason": reason}, ticker=ticker
        )


def update_risk_flags(conn: sqlite3.Connection, ticker: str, risk_flags: list[str]) -> None:
    conn.execute(
        "UPDATE watchlist_records SET risk_flags = ? WHERE ticker = ?",
        (", ".join(risk_flags), ticker.upper()),
    )


def deactivate(conn: sqlite3.Connection, ticker: str) -> None:
    conn.execute("UPDATE watchlist_records SET is_active = 0 WHERE ticker = ?", (ticker.upper(),))
    audit_service.log_event(conn, "watchlist_change", {"changes": {"removed": True}}, ticker=ticker.upper())
