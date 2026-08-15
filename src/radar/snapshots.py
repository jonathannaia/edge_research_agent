"""Automated per-ticker price/insider-transaction/news snapshots —
separate from Radar's own niche-scoped findings feed. Refreshed each scan
run for two ticker sets:

  1. Verified US tickers newly tagged by this run's Radar findings.
  2. Tickers in data/tracked_tickers.json — a small, manually-maintained
     list for Watchlist tickers you want auto-tracked even if Radar's own
     four niches never happen to mention them. This exists because the
     scan job runs in GitHub Actions, which has no access to your local/
     deployed Watchlist database (gitignored, never committed) — see
     README "Radar" section for the full explanation of why, and what the
     alternative (granting the app git-push access) would have meant.

US-only for now: price (Finnhub), insider transactions and news (SEC
EDGAR) are all US-only live domains as of this writing — see each
provider's own module for why. Filings/fundamentals aren't duplicated
here — those are already available on-demand for any watchlist ticker via
"Generate Research Brief" in the app itself, which doesn't have the
GitHub-Actions-can't-see-the-Watchlist constraint (it runs synchronously
inside the app, not in CI), so there's no gap to fill there.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from src.config.settings import Settings
from src.providers.edgar_client import EdgarError
from src.providers.finnhub_client import FinnhubError
from src.providers.live_edgar import (
    EdgarUnavailableError,
    LiveInsiderProvider,
    LiveNewsProvider,
)
from src.providers.live_price import LivePriceProvider, PriceUnavailableError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRACKED_TICKERS_PATH = PROJECT_ROOT / "data" / "tracked_tickers.json"
SNAPSHOTS_PATH = PROJECT_ROOT / "data" / "ticker_snapshots.json"

DEFAULT_MAX_TICKERS_PER_RUN = 40  # headroom above the initial ~31-ticker tracked list


def load_tracked_tickers() -> list[str]:
    if not TRACKED_TICKERS_PATH.exists():
        return []
    try:
        data = json.loads(TRACKED_TICKERS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return [t.upper() for t in data.get("tickers", [])]


def load_snapshots() -> dict:
    if not SNAPSHOTS_PATH.exists():
        return {}
    try:
        return json.loads(SNAPSHOTS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _snapshot_one_ticker(ticker: str, settings: Settings) -> dict:
    """Best-effort per-domain: one domain failing (e.g. no Finnhub key set)
    doesn't block the others — each is independently try/excepted."""
    result: dict = {"ticker": ticker, "jurisdiction": "United States", "retrieved_at": _now_iso(), "errors": []}

    price_provider = LivePriceProvider(settings)
    try:
        price = price_provider.get_price_context(ticker)
        result["price"] = asdict(price) if price else None
    except (PriceUnavailableError, FinnhubError) as exc:
        result["price"] = None
        result["errors"].append(f"price: {exc}")

    try:
        valuation = price_provider.get_valuation_context(ticker)
        result["valuation"] = asdict(valuation) if valuation else None
    except (PriceUnavailableError, FinnhubError) as exc:
        result["valuation"] = None
        result["errors"].append(f"valuation: {exc}")

    insider_provider = LiveInsiderProvider(settings)
    try:
        txns = insider_provider.get_insider_transactions(ticker, limit=5)
        result["insider_transactions"] = [asdict(t) for t in txns]
    except (EdgarUnavailableError, EdgarError) as exc:
        result["insider_transactions"] = []
        result["errors"].append(f"insiders: {exc}")

    news_provider = LiveNewsProvider(settings)
    try:
        news = news_provider.get_recent_news(ticker, limit=5)
        result["news"] = [asdict(n) for n in news]
    except (EdgarUnavailableError, EdgarError) as exc:
        result["news"] = []
        result["errors"].append(f"news: {exc}")

    return result


def refresh_snapshots(tickers: list[str], settings: Settings, max_tickers: int | None = None) -> dict:
    """Refreshes snapshots for up to max_tickers of the given tickers
    (bounded — cost/time-controlled batch job, not open-ended), merges
    into the existing store, and writes it back. Returns a small summary
    dict (not part of Radar's own ScanRunRecord — kept separate to avoid
    another schema-migration ripple through that dataclass)."""
    max_tickers = max_tickers if max_tickers is not None else int(
        os.getenv("EDGE_RADAR_MAX_SNAPSHOT_TICKERS_PER_RUN", DEFAULT_MAX_TICKERS_PER_RUN)
    )
    unique_tickers = sorted({t.upper() for t in tickers if t})[:max_tickers]

    existing = load_snapshots()
    refreshed, failed = 0, 0
    for ticker in unique_tickers:
        snap = _snapshot_one_ticker(ticker, settings)
        if snap.get("price") or snap.get("insider_transactions") or snap.get("news"):
            refreshed += 1
        else:
            failed += 1
        existing[ticker] = snap

    SNAPSHOTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SNAPSHOTS_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return {"tickers_considered": len(tickers), "tickers_attempted": len(unique_tickers), "tickers_refreshed": refreshed, "tickers_failed": failed}
