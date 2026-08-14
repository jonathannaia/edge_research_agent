from __future__ import annotations

import json
import sqlite3
from typing import Optional

from src.services import audit_service

EVIDENCE_STATUSES = ("Strengthening", "Unchanged", "Weakening", "Insufficient evidence")


def get_current_thesis(conn: sqlite3.Connection, ticker: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM theses WHERE ticker = ? AND is_current = 1 ORDER BY version DESC LIMIT 1",
        (ticker.upper(),),
    ).fetchone()


def list_thesis_versions(conn: sqlite3.Connection, ticker: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM theses WHERE ticker = ? ORDER BY version DESC", (ticker.upper(),)
    ).fetchall()


def save_thesis(
    conn: sqlite3.Connection,
    ticker: str,
    theme: str,
    subtheme: str,
    why_on_watchlist: str,
    inflection_thesis: str,
    thesis_owner_notes: str,
    evidence_supporting: list[dict],
    evidence_contradicting: list[dict],
    confirmation_conditions: str,
    invalidation_conditions: str,
    key_risks: str,
    next_catalyst: Optional[str],
    next_catalyst_date: Optional[str],
    tier: str,
    score: float,
    tags: str,
) -> int:
    """Inserts a new thesis version and marks the previous current version as
    superseded, so full research history is preserved rather than overwritten."""
    ticker = ticker.upper()
    prev = get_current_thesis(conn, ticker)
    next_version = (prev["version"] + 1) if prev else 1

    if prev:
        conn.execute("UPDATE theses SET is_current = 0 WHERE id = ?", (prev["id"],))

    cur = conn.execute(
        """INSERT INTO theses (
            ticker, theme, subtheme, why_on_watchlist, inflection_thesis, thesis_owner_notes,
            evidence_supporting, evidence_contradicting, confirmation_conditions, invalidation_conditions,
            key_risks, next_catalyst, next_catalyst_date, last_review_date, tier, score, tags,
            version, is_current
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?, ?, 1)""",
        (
            ticker, theme, subtheme, why_on_watchlist, inflection_thesis, thesis_owner_notes,
            json.dumps(evidence_supporting), json.dumps(evidence_contradicting),
            confirmation_conditions, invalidation_conditions, key_risks,
            next_catalyst, next_catalyst_date, tier, score, tags, next_version,
        ),
    )
    audit_service.log_event(
        conn, "thesis_updated", {"version": next_version, "tier": tier, "score": score}, ticker=ticker
    )
    return cur.lastrowid


def evaluate_thesis_signal(previous_status: str, new_status: str, score_delta: float) -> str:
    """Returns 'confirming', 'invalidating', or 'neutral' given how evidence
    status moved and how the conviction score changed between two research
    briefs. Pure function so it's directly unit-testable."""
    weakening_transition = previous_status in ("Strengthening", "Unchanged") and new_status == "Weakening"
    strengthening_transition = previous_status in ("Weakening", "Unchanged") and new_status == "Strengthening"

    if weakening_transition or (new_status == "Weakening" and score_delta < 0):
        return "invalidating"
    if strengthening_transition or (new_status == "Strengthening" and score_delta > 0):
        return "confirming"
    return "neutral"
