from __future__ import annotations

from datetime import date, datetime

FRESHNESS_LABELS = {
    "fresh": "Fresh",
    "aging": "Aging",
    "stale": "Stale",
    "very_stale": "Very stale",
}

def freshness_badge(status: str) -> str:
    return FRESHNESS_LABELS.get(status, status)


def fmt_money(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000_000:
        return f"{sign}${value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{sign}${value / 1_000:.0f}K"
    return f"{sign}${value:.0f}"


def fmt_pct(value: float | None, signed: bool = True) -> str:
    if value is None:
        return "—"
    return f"{value:+.1%}" if signed else f"{value:.1%}"


def days_between(a: str, b: str) -> int | None:
    try:
        return (date.fromisoformat(b) - date.fromisoformat(a)).days
    except (ValueError, TypeError):
        return None


def days_ago(iso_date: str) -> int | None:
    return days_between(iso_date, date.today().isoformat())


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
