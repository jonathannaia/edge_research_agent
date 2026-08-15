from datetime import datetime, timedelta, timezone

from src.logic.formatting import days_ago, fmt_currency, fmt_date, fmt_datetime, fmt_pct


def test_fmt_pct_signed_positive():
    assert fmt_pct(4.0) == "+4.0%"


def test_fmt_pct_signed_negative():
    assert fmt_pct(-1.5) == "-1.5%"


def test_fmt_pct_unsigned():
    assert fmt_pct(4.0, signed=False) == "4.0%"


def test_fmt_pct_decimals():
    assert fmt_pct(4.567, decimals=2) == "+4.57%"


def test_fmt_currency_basic():
    assert fmt_currency(1234567) == "$1,234,567"


def test_fmt_date_valid_date_only():
    assert fmt_date("2026-09-05") == "Sep 5, 2026"


def test_fmt_date_valid_datetime():
    assert fmt_date("2026-09-05T12:00:00+00:00") == "Sep 5, 2026"


def test_fmt_date_invalid_returns_original():
    assert fmt_date("not-a-date") == "not-a-date"


def test_fmt_datetime_valid():
    result = fmt_datetime("2026-09-05T12:30:00+00:00")
    assert "Sep 5, 2026" in result
    assert "12:30" in result


def test_fmt_datetime_invalid_returns_original():
    assert fmt_datetime("garbage") == "garbage"


def test_days_ago_computes_correctly():
    ts = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    assert days_ago(ts) == 3


def test_days_ago_invalid_returns_none():
    assert days_ago("garbage") is None
