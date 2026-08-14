"""Guardrail principle #9: auditability. Every material state change writes
an audit_logs row so the user can reconstruct how a conclusion was reached."""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional


def log_event(conn: sqlite3.Connection, event_type: str, payload: dict[str, Any], ticker: Optional[str] = None) -> int:
    cur = conn.execute(
        "INSERT INTO audit_logs (event_type, ticker, payload_json) VALUES (?, ?, ?)",
        (event_type, ticker, json.dumps(payload, default=str)),
    )
    return cur.lastrowid


def list_events_for_ticker(conn: sqlite3.Connection, ticker: str, event_types: Optional[list[str]] = None, limit: int = 100) -> list[sqlite3.Row]:
    if event_types:
        placeholders = ",".join("?" for _ in event_types)
        rows = conn.execute(
            f"SELECT * FROM audit_logs WHERE ticker = ? AND event_type IN ({placeholders}) "
            "ORDER BY created_at DESC, id DESC LIMIT ?",
            (ticker, *event_types, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM audit_logs WHERE ticker = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (ticker, limit),
        ).fetchall()
    return rows


def list_recent_events(conn: sqlite3.Connection, limit: int = 50) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM audit_logs ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
    ).fetchall()
