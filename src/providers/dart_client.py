"""Shared low-level client for Korea's DART (OpenDART) API.

Unlike SEC EDGAR, DART requires a free API key (EDGE_DART_API_KEY) — see
README "Filings beyond the US" for how to register one. Every endpoint
this module calls was verified against DART's official API documentation
(opendart.fss.or.kr/guide) before being implemented — see live_dart.py's
module docstring for exactly what is and isn't verified against a real
live response (no key was available while writing this).
"""
from __future__ import annotations

import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from src.utils.ssl_context import SSL_CONTEXT

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CACHE_DIR = PROJECT_ROOT / ".cache"
_CORP_CODE_CACHE = _CACHE_DIR / "dart_corp_codes.json"
_CORP_CODE_TTL_SECONDS = 24 * 3600

_MIN_REQUEST_INTERVAL_SECONDS = 0.2
_last_request_at = 0.0

BASE_URL = "https://opendart.fss.or.kr/api"


class DartError(RuntimeError):
    pass


def _throttle() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < _MIN_REQUEST_INTERVAL_SECONDS:
        time.sleep(_MIN_REQUEST_INTERVAL_SECONDS - elapsed)


def _get(path: str, params: dict) -> bytes:
    _throttle()
    url = f"{BASE_URL}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "EevaResearchAI/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20, context=SSL_CONTEXT) as resp:
            raw = resp.read()
        global _last_request_at
        _last_request_at = time.monotonic()
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise DartError(f"Request to {path} failed: {exc}") from exc
    return raw


def get_json(path: str, params: dict) -> dict:
    raw = _get(path, params)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DartError(f"DART returned non-JSON for {path}: {exc}") from exc
    status = data.get("status")
    # DART reports app-level errors (bad key, no data, rate limit) inside a
    # 200 response via its own status code — "000" is the only success value.
    if status and status != "000":
        raise DartError(f"DART API error {status}: {data.get('message')}")
    return data


def _load_corp_code_map(api_key: str) -> dict[str, str]:
    """stock_code (Korea's 6-digit exchange code, e.g. "005930" for Samsung
    Electronics) -> corp_code (DART's own 8-digit internal id, required by
    every other endpoint). Cached on disk for 24h — this is a multi-MB
    download of every DART-registered company, not something to refetch
    per call."""
    if _CORP_CODE_CACHE.exists():
        age = time.time() - _CORP_CODE_CACHE.stat().st_mtime
        if age < _CORP_CODE_TTL_SECONDS:
            try:
                return json.loads(_CORP_CODE_CACHE.read_text())
            except (json.JSONDecodeError, OSError):
                pass

    raw_zip = _get("corpCode.xml", {"crtfc_key": api_key})
    try:
        with zipfile.ZipFile(io.BytesIO(raw_zip)) as zf:
            xml_bytes = zf.read(zf.namelist()[0])
    except zipfile.BadZipFile as exc:
        raise DartError(f"corpCode.xml wasn't a valid zip (a bad/unapproved API key returns an XML error instead): {exc}") from exc

    root = ET.fromstring(xml_bytes)
    mapping: dict[str, str] = {}
    for item in root.findall("list"):
        stock_code = (item.findtext("stock_code") or "").strip()
        corp_code = (item.findtext("corp_code") or "").strip()
        if stock_code:  # unlisted companies have an empty stock_code — no ticker to match against
            mapping[stock_code] = corp_code

    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _CORP_CODE_CACHE.write_text(json.dumps(mapping))
    except OSError:
        pass  # on-disk cache is an optimization, not required for correctness

    return mapping


def get_corp_code(stock_code: str, api_key: str) -> str | None:
    return _load_corp_code_map(api_key).get(stock_code.strip())
