"""Freshness gate — Radar must never surface anything older than a bounded
window (default 24h), no matter how far back a feed's RSS history goes.

Applied before any LLM call (it's free), using feedparser's normalized
published_parsed/updated_parsed struct rather than re-parsing the raw date
string ourselves, since feeds use inconsistent date formats.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

DEFAULT_MAX_AGE_HOURS = 24


def max_age_hours() -> int:
    raw = os.getenv("EDGE_RADAR_MAX_AGE_HOURS")
    if not raw:
        return DEFAULT_MAX_AGE_HOURS
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_MAX_AGE_HOURS


def is_fresh(published_epoch: int | None, now: datetime | None = None, max_hours: int | None = None) -> bool:
    """True only if the item has a parseable publish time within the
    freshness window. An item with NO parseable date is treated as stale —
    better to miss an edge case than silently show something of unknown
    age, given the explicit "nothing older than 24h" requirement."""
    if published_epoch is None:
        return False
    now = now or datetime.now(timezone.utc)
    max_hours = max_age_hours() if max_hours is None else max_hours
    age_seconds = now.timestamp() - published_epoch
    return age_seconds <= max_hours * 3600
