"""Pure formatting helpers — no Streamlit, no I/O, unit-testable in
isolation. Shared across every page so a percentage or date never gets
formatted two different ways in two different places."""
from __future__ import annotations

from datetime import datetime, timezone


def fmt_pct(value: float, decimals: int = 1, signed: bool = True) -> str:
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def fmt_currency(value: float, decimals: int = 0) -> str:
    return f"${value:,.{decimals}f}"


def fmt_date(iso_str: str) -> str:
    """'2026-09-05' or a full ISO datetime -> 'Sep 5, 2026'. Returns the
    original string unparsed rather than raising on bad input."""
    for parser in (lambda s: datetime.fromisoformat(s), lambda s: datetime.strptime(s, "%Y-%m-%d")):
        try:
            return parser(iso_str).strftime("%b %-d, %Y")
        except (ValueError, TypeError):
            continue
    return iso_str


def fmt_datetime(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%b %-d, %Y, %H:%M UTC")
    except (ValueError, TypeError):
        return iso_str


def days_ago(iso_str: str) -> int | None:
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None
    return int((datetime.now(timezone.utc) - dt).total_seconds() // 86400)
