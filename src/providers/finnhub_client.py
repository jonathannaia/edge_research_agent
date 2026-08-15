"""Shared low-level client for Finnhub's free-tier stock API.

Requires a free API key (EDGE_FINNHUB_API_KEY) — register at finnhub.io.
Free tier covers US-listed tickers only; international exchanges (including
KRX/Korea) need a paid plan, so this stays US-only for now, same scope as
LiveInsiderProvider and LiveNewsProvider.

Unlike SEC EDGAR and DART, Finnhub's own documentation site is JavaScript-
rendered and couldn't be read directly the same way — so unlike those two,
the exact response field names here were NOT independently confirmed
against official docs before writing live_price.py. Instead,
scripts/finnhub_smoke_test.py dumps the *raw* real response first, which is
inspected before any parsing logic is trusted — see live_price.py's module
docstring for what's actually been verified.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from src.utils.ssl_context import SSL_CONTEXT

BASE_URL = "https://finnhub.io/api/v1"
_MIN_REQUEST_INTERVAL_SECONDS = 1.1  # free tier: 60/min: stay comfortably under
_last_request_at = 0.0


class FinnhubError(RuntimeError):
    pass


def _get(path: str, params: dict, api_key: str) -> dict:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < _MIN_REQUEST_INTERVAL_SECONDS:
        time.sleep(_MIN_REQUEST_INTERVAL_SECONDS - elapsed)

    query = urllib.parse.urlencode({**params, "token": api_key})
    url = f"{BASE_URL}/{path}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "EevaResearchAI/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15, context=SSL_CONTEXT) as resp:
            raw = resp.read()
        _last_request_at = time.monotonic()
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise FinnhubError(f"Request to {path} failed: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FinnhubError(f"Finnhub returned non-JSON for {path}: {exc}") from exc

    if isinstance(data, dict) and data.get("error"):
        raise FinnhubError(f"Finnhub API error: {data['error']}")
    return data


def get_quote(symbol: str, api_key: str) -> dict:
    return _get("quote", {"symbol": symbol.upper()}, api_key)


def get_basic_financials(symbol: str, api_key: str) -> dict:
    return _get("stock/metric", {"symbol": symbol.upper(), "metric": "all"}, api_key)
