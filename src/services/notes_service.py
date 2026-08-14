from __future__ import annotations

import sqlite3

from src.guardrails.language_filters import warn_no_advice_language


def add_note(conn: sqlite3.Connection, ticker: str, note_text: str, tags: str = "") -> tuple[int, list[str]]:
    """Returns (note_id, advice_language_warnings). Warnings are informational
    only — the user's own notes are never blocked from saving."""
    warnings = warn_no_advice_language(note_text)
    cur = conn.execute(
        "INSERT INTO notes (ticker, note_text, tags) VALUES (?, ?, ?)", (ticker.upper(), note_text, tags)
    )
    return cur.lastrowid, warnings


def list_notes(conn: sqlite3.Connection, ticker: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM notes WHERE ticker = ? ORDER BY created_at DESC", (ticker.upper(),)
    ).fetchall()
