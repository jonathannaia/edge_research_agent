"""Shared low-level client for SEC EDGAR's free, keyless public JSON APIs.

Used by both live_edgar.py (research briefs) and src/radar/ticker_registry.py
(ticker verification) — one place that knows how to talk to EDGAR politely.

EDGAR asks for a descriptive User-Agent identifying the requester and
reasonable request rates (https://www.sec.gov/os/webmaster-faq#developers);
both are honored here via EDGE_SEC_USER_AGENT and simple request pacing.
Stdlib-only (urllib) — deliberately avoids adding a new HTTP dependency for
this.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from src.utils.ssl_context import SSL_CONTEXT

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CACHE_DIR = PROJECT_ROOT / ".cache"
_TICKER_MAP_CACHE = _CACHE_DIR / "sec_company_tickers.json"
_TICKER_MAP_TTL_SECONDS = 24 * 3600

_MIN_REQUEST_INTERVAL_SECONDS = 0.15  # stay comfortably under SEC's fair-access rate
_last_request_at = 0.0


class EdgarError(RuntimeError):
    pass


def _get(url: str, user_agent: str) -> dict:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < _MIN_REQUEST_INTERVAL_SECONDS:
        time.sleep(_MIN_REQUEST_INTERVAL_SECONDS - elapsed)

    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(req, timeout=15, context=SSL_CONTEXT) as resp:
            raw = resp.read()
        _last_request_at = time.monotonic()
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise EdgarError(f"Request to {url} failed: {exc}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EdgarError(f"SEC EDGAR returned non-JSON for {url}: {exc}") from exc


def _load_ticker_map(user_agent: str) -> dict[str, int]:
    if _TICKER_MAP_CACHE.exists():
        age = time.time() - _TICKER_MAP_CACHE.stat().st_mtime
        if age < _TICKER_MAP_TTL_SECONDS:
            try:
                raw = json.loads(_TICKER_MAP_CACHE.read_text())
                return {t: int(cik) for t, cik in raw.items()}
            except (json.JSONDecodeError, OSError, ValueError):
                pass  # fall through and refetch

    data = _get("https://www.sec.gov/files/company_tickers.json", user_agent)
    mapping = {row["ticker"].upper(): int(row["cik_str"]) for row in data.values()}

    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _TICKER_MAP_CACHE.write_text(json.dumps(mapping))
    except OSError:
        pass  # on-disk cache is an optimization, not required for correctness

    return mapping


def get_cik_for_ticker(ticker: str, user_agent: str) -> int | None:
    return _load_ticker_map(user_agent).get(ticker.upper())


def get_all_tickers(user_agent: str) -> dict[str, int]:
    """The full ticker -> CIK registry, for cross-checking tags against real
    US-listed companies (see src/radar/ticker_registry.py)."""
    return _load_ticker_map(user_agent)


def get_submissions(cik: int, user_agent: str) -> dict:
    return _get(f"https://data.sec.gov/submissions/CIK{str(cik).zfill(10)}.json", user_agent)


def get_company_facts(cik: int, user_agent: str) -> dict:
    return _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{str(cik).zfill(10)}.json", user_agent)


def full_text_search(query: str, user_agent: str, forms: str = "8-K", start_date: str = "", end_date: str = "") -> dict:
    """SEC EDGAR full-text search (efts.sec.gov) — free, keyless. Used by
    src/radar/feeds.py to surface real regulatory filings matching a query,
    rather than relying only on third-party RSS/news coverage of them.
    start_date/end_date are ISO dates (YYYY-MM-DD); omit for "any time"."""
    params = {"q": query, "forms": forms}
    if start_date and end_date:
        params.update({"dateRange": "custom", "startdt": start_date, "enddt": end_date})
    query_string = urllib.parse.urlencode(params)
    return _get(f"https://efts.sec.gov/LATEST/search-index?{query_string}", user_agent)


def filing_document_url(cik: int, accession_number: str, primary_document: str) -> str:
    accession_no_dashes = accession_number.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{primary_document}"


def filing_index_url(cik: int, accession_number: str) -> str:
    accession_no_dashes = accession_number.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{accession_number}-index.htm"
