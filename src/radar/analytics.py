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


def is_scan_overdue(last_run_finished_at: str | None, expected_interval_hours: float = 2, grace_multiplier: float = 3) -> bool:
    """True if it's been more than `grace_multiplier` x the expected cron
    interval since the last recorded run — a signal the scheduled workflow
    has silently stopped firing (broken secret, deleted/disabled workflow,
    GitHub Actions outage) rather than genuinely finding nothing new. Ops
    monitoring for an unattended job with no other alerting."""
    if not last_run_finished_at:
        return False  # no runs at all yet is a different, already-handled state
    try:
        ts = datetime.fromisoformat(last_run_finished_at)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return False
    age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
    return age_hours > expected_interval_hours * grace_multiplier


def find_cross_theme_findings(findings: list[RadarFinding], ticker_themes: dict[str, str]) -> list[dict]:
    """Findings that tag tickers from 2+ different themes within the SAME
    cited article — the only "cross-theme connection" this makes, since it
    requires zero inference: the article itself already, factually,
    discusses companies from multiple themes together. This deliberately
    does NOT try to correlate separate articles by date/keyword and assert
    they're related — that would be an unverified inference the rest of
    this app's guardrails don't allow (see README "Radar" section on why
    cross-theme dependencies are evidence-linked only, not inferential)."""
    results = []
    for f in findings:
        themes_in_finding = sorted({ticker_themes[t.ticker] for t in f.tickers if t.ticker in ticker_themes})
        if len(themes_in_finding) >= 2:
            results.append({"finding": f, "themes": themes_in_finding})
    return results


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
