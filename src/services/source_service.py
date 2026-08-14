from __future__ import annotations

import sqlite3
from datetime import date
from typing import Optional

from src.guardrails.source_hierarchy import authority_rank


def save_source(
    conn: sqlite3.Connection,
    ticker: str,
    source_type: str,
    title: str,
    url_or_identifier: str,
    source_date: str,
    retrieval_date: Optional[str] = None,
) -> int:
    retrieval_date = retrieval_date or date.today().isoformat()
    cur = conn.execute(
        """INSERT INTO sources (ticker, source_type, title, url_or_identifier, source_date, retrieval_date, authority_rank)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (ticker.upper(), source_type, title, url_or_identifier, source_date, retrieval_date, authority_rank(source_type)),
    )
    return cur.lastrowid


def save_excerpt(conn: sqlite3.Connection, source_id: int, excerpt_text: str, tag: str = "neutral") -> int:
    cur = conn.execute(
        "INSERT INTO source_excerpts (source_id, excerpt_text, tag) VALUES (?, ?, ?)",
        (source_id, excerpt_text, tag),
    )
    return cur.lastrowid


def list_sources_for_ticker(conn: sqlite3.Connection, ticker: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM sources WHERE ticker = ? ORDER BY source_date DESC", (ticker.upper(),)
    ).fetchall()


def list_all_sources(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM sources ORDER BY source_date DESC").fetchall()


def list_excerpts_for_source(conn: sqlite3.Connection, source_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM source_excerpts WHERE source_id = ? ORDER BY id ASC", (source_id,)
    ).fetchall()


def get_source(conn: sqlite3.Connection, source_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
