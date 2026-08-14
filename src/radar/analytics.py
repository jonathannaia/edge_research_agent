"""Pure aggregation functions over Radar's findings history — no Streamlit
dependency, so they're directly testable. Used by src/ui/radar_trends.py.

These only aggregate what's already been saved to data/radar_findings.json
— they never fetch anything new or make an LLM call.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from src.radar.models import RadarFinding


def _parse_retrieved_at(f: RadarFinding) -> datetime | None:
    try:
        ts = datetime.fromisoformat(f.retrieved_at)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
    except (ValueError, TypeError):
        return None


def findings_within(findings: list[RadarFinding], days: int) -> list[RadarFinding]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return [f for f in findings if (ts := _parse_retrieved_at(f)) is not None and ts >= cutoff]


def mentions_per_niche(findings: list[RadarFinding]) -> dict[str, int]:
    return dict(Counter(f.niche for f in findings))


def mentions_per_day(findings: list[RadarFinding], days: int) -> dict[str, int]:
    """Zero-filled day buckets (oldest first) so a quiet day shows 0 rather
    than being missing from the chart entirely."""
    today = datetime.now(timezone.utc).date()
    buckets = {(today - timedelta(days=i)).isoformat(): 0 for i in range(days - 1, -1, -1)}
    for f in findings:
        ts = _parse_retrieved_at(f)
        if ts is None:
            continue
        day = ts.date().isoformat()
        if day in buckets:
            buckets[day] += 1
    return buckets


def top_tickers(findings: list[RadarFinding], limit: int = 15) -> list[dict]:
    """Most-mentioned tickers, most-mentioned first. Each row: ticker,
    company_name/jurisdiction from its most recent tag, mention count, and
    the most recent retrieved_at among its mentions."""
    counts: dict[str, dict] = {}
    for f in findings:
        for t in f.tickers:
            key = t.ticker.upper()
            entry = counts.setdefault(
                key,
                {"ticker": key, "company_name": t.company_name, "jurisdiction": t.jurisdiction,
                 "count": 0, "last_mention": f.retrieved_at},
            )
            entry["count"] += 1
            if f.retrieved_at > entry["last_mention"]:
                entry["last_mention"] = f.retrieved_at
                entry["company_name"] = t.company_name
                entry["jurisdiction"] = t.jurisdiction
    rows = sorted(counts.values(), key=lambda r: r["count"], reverse=True)
    return rows[:limit]
