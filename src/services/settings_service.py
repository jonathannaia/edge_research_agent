"""Generic key/value app_settings store, used for editable scoring weights
and editable freshness thresholds so those survive app restarts without
requiring an env var change."""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.scoring.defaults import DEFAULT_WEIGHTS


def get_setting(conn: sqlite3.Connection, key: str, default: Any = None) -> Any:
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row["value"])
    except (json.JSONDecodeError, TypeError):
        return row["value"]


def set_setting(conn: sqlite3.Connection, key: str, value: Any) -> None:
    encoded = json.dumps(value)
    conn.execute(
        "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')",
        (key, encoded),
    )


def get_score_weights(conn: sqlite3.Connection) -> dict[str, float]:
    return get_setting(conn, "score_weights", DEFAULT_WEIGHTS.copy())


def set_score_weights(conn: sqlite3.Connection, weights: dict[str, float]) -> None:
    set_setting(conn, "score_weights", weights)


def get_freshness_thresholds(conn: sqlite3.Connection, defaults: dict[str, int]) -> dict[str, int]:
    return get_setting(conn, "freshness_thresholds", defaults)


def set_freshness_thresholds(conn: sqlite3.Connection, thresholds: dict[str, int]) -> None:
    set_setting(conn, "freshness_thresholds", thresholds)
