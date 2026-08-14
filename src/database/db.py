"""SQLite connection management and initialization.

No ORM: plain sqlite3 with row_factory=sqlite3.Row keeps the mapping to the
dataclasses in src.models explicit and easy to audit.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from src.config.settings import Settings, get_settings

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(settings: Settings | None = None) -> None:
    """Create all tables if they don't already exist. Safe to call repeatedly."""
    settings = settings or get_settings()
    conn = _connect(settings.db_path)
    try:
        schema_sql = _SCHEMA_PATH.read_text()
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_connection(settings: Settings | None = None) -> Iterator[sqlite3.Connection]:
    """Context manager yielding a connection; commits on success, rolls back on error."""
    settings = settings or get_settings()
    conn = _connect(settings.db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
