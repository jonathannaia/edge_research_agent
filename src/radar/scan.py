"""Radar scan orchestration — the one function the GitHub Actions workflow
calls (via scripts/run_radar_scan.py).

Pipeline, each stage bounded to keep this a cost-controlled batch job, not
an open-ended crawl (guardrail principle #10):

  fetch all feeds
    -> drop items already seen (by URL hash, zero cost)
    -> drop items that don't match their niche's keywords (zero cost)
    -> cap total candidates sent to the LLM this run
    -> Haiku: relevance + ticker tagging + cited summary (bounded $ cost)
    -> guardrail: reject any summary containing advice/recommendation
       language before it's ever saved (guardrail principle #7)
    -> persist findings + a full audit record of the run (principle #9)
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from src.config.settings import get_settings
from src.guardrails.language_filters import AdviceLanguageError, enforce_no_advice_language
from src.radar import feeds as feeds_module
from src.radar import notifier as notify
from src.radar import snapshots as snapshot_module
from src.radar import store
from src.radar.freshness import is_fresh
from src.radar.keyword_filter import is_plausibly_relevant
from src.radar.llm_tagger import TaggingError, tag_item
from src.radar.models import RadarFinding, ScanRunRecord
from src.radar.ticker_registry import verify_ticker_tags

UNITED_STATES = "United States"

DEFAULT_MAX_ITEMS_PER_RUN = 25


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run(max_items_per_run: int | None = None) -> ScanRunRecord:
    max_items_per_run = max_items_per_run or int(os.getenv("EDGE_RADAR_MAX_ITEMS_PER_RUN", DEFAULT_MAX_ITEMS_PER_RUN))
    started_at = _now_iso()
    errors: list[str] = []

    existing_findings = store.load_findings()
    seen_hashes = store.load_seen_hashes()
    existing_run_history = store.load_run_history()

    raw_items, fetch_errors = feeds_module.fetch_all()
    errors.extend(fetch_errors)

    # Freshness gate FIRST — never surface anything older than
    # EDGE_RADAR_MAX_AGE_HOURS (default 24h), regardless of how far back a
    # feed's own RSS history goes. Free (no LLM cost either way), so it runs
    # before dedup and the keyword filter.
    fresh_items = [
        (feed, entry) for feed, entry in raw_items
        if is_fresh(entry.get("published_epoch"))
    ]

    # Drop already-seen items (dedup by URL) before any further processing.
    unseen = []
    for feed, entry in fresh_items:
        link = entry.get("link", "")
        if not link:
            continue
        if store.url_hash(link) in seen_hashes:
            continue
        unseen.append((feed, entry))

    # Cheap keyword pre-filter — zero cost, run before touching the LLM.
    candidates = [
        (feed, entry) for feed, entry in unseen
        if is_plausibly_relevant(feed.niche, entry.get("title", ""), entry.get("summary", ""))
    ]

    # Bound LLM spend for this run regardless of how many candidates matched.
    candidates = candidates[:max_items_per_run]

    new_findings: list[RadarFinding] = []
    items_rejected_by_guardrail = 0

    for feed, entry in candidates:
        title = entry.get("title", "")
        snippet = entry.get("summary", "")
        link = entry.get("link", "")

        try:
            tagged = tag_item(feed.niche, title, snippet)
        except TaggingError as exc:
            errors.append(f"{feed.name} — {title[:60]!r}: {exc}")
            continue

        if not tagged.relevant or not tagged.summary:
            continue

        try:
            enforce_no_advice_language(tagged.summary, context="Radar finding summary")
        except AdviceLanguageError as exc:
            items_rejected_by_guardrail += 1
            errors.append(f"Guardrail rejected finding ({feed.name} — {title[:60]!r}): {exc}")
            continue

        retrieved_at = _now_iso()
        new_findings.append(
            RadarFinding(
                niche=feed.niche,
                headline=title,
                summary=tagged.summary,
                source_url=link,
                source_name=feed.name,
                source_type=feed.source_type,
                published_at=entry.get("published", ""),
                retrieved_at=retrieved_at,
                tickers=verify_ticker_tags(tagged.tickers),
                relevance_reason=tagged.relevance_reason,
                url_hash=store.url_hash(link),
                id=store.url_hash(link),
            )
        )

    finished_at = _now_iso()
    status = "ok" if not errors else ("error" if not new_findings and not candidates else "partial_error")

    run_record = ScanRunRecord(
        started_at=started_at,
        finished_at=finished_at,
        status=status,
        feeds_checked=len(feeds_module.FEEDS),
        items_seen=len(raw_items),
        items_after_freshness_filter=len(fresh_items),
        items_after_keyword_filter=len(candidates),
        items_sent_to_llm=len(candidates),
        items_saved=len(new_findings),
        items_rejected_by_guardrail=items_rejected_by_guardrail,
        errors=errors[:50],
    )

    store.save_scan_results(
        new_findings=new_findings,
        run_record=run_record,
        existing_findings=existing_findings,
        existing_seen_hashes=seen_hashes,
        existing_run_history=existing_run_history,
    )

    # Best-effort, after the run's own record is already final — a broken
    # webhook must never affect what got saved or the run's audit record.
    webhook_error = notify.send_webhook_notification(new_findings)
    if webhook_error:
        print(f"Radar webhook notification failed (non-fatal): {webhook_error}")

    # Automated per-ticker price/insider/news snapshots — separate from the
    # findings feed above. Covers verified US tickers this run just tagged,
    # plus anything in data/tracked_tickers.json (see snapshots.py module
    # docstring for why that file exists). Best-effort: a snapshot failure
    # never affects the findings/run-record already saved above.
    try:
        tagged_us_tickers = [
            t.ticker for f in new_findings for t in f.tickers
            if t.verified and t.jurisdiction == UNITED_STATES
        ]
        tracked_tickers = snapshot_module.load_tracked_tickers()
        snapshot_summary = snapshot_module.refresh_snapshots(
            tagged_us_tickers + tracked_tickers, get_settings()
        )
        print(f"Ticker snapshots: {snapshot_summary}")
    except Exception as exc:  # snapshots are additive — never fail the whole scan over this
        print(f"Ticker snapshot refresh failed (non-fatal): {exc}")

    return run_record
