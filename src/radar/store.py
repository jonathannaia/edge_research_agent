"""JSON-file persistence for Radar.

Two files, both under data/ and committed to the repo by the scan workflow:

  data/radar_findings.json  — the findings feed the UI reads. Bounded to the
                               most recent MAX_FINDINGS so the file (and the
                               repo) don't grow unbounded.
  data/radar_state.json     — dedup index (seen url_hash -> retrieved_at) and
                               the scan-run audit trail (guardrail principle
                               #9), bounded to MAX_RUN_HISTORY entries.

Deliberately not SQLite: the scanner runs in GitHub Actions and the app runs
on Streamlit Cloud — two processes with no shared filesystem or database.
Plain JSON committed to git is the simplest thing that lets the GH Actions
job "push" data the app can "pull" on its next deploy/reboot, with zero new
infrastructure (no hosted DB, no extra account signup).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from src.radar.models import RadarFinding, ScanRunRecord, TickerTag

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FINDINGS_PATH = PROJECT_ROOT / "data" / "radar_findings.json"
STATE_PATH = PROJECT_ROOT / "data" / "radar_state.json"

MAX_FINDINGS = 500
MAX_RUN_HISTORY = 200


def url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()[:16]


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_findings() -> list[RadarFinding]:
    raw = _read_json(FINDINGS_PATH, [])
    findings = []
    for item in raw:
        tickers = [TickerTag(**t) for t in item.get("tickers", [])]
        item = {**item, "tickers": tickers}
        findings.append(RadarFinding(**item))
    return findings


def load_seen_hashes() -> set[str]:
    state = _read_json(STATE_PATH, {})
    return set(state.get("seen_url_hashes", []))


def load_run_history() -> list[ScanRunRecord]:
    state = _read_json(STATE_PATH, {})
    return [ScanRunRecord(**r) for r in state.get("run_history", [])]


def save_scan_results(
    new_findings: list[RadarFinding],
    run_record: ScanRunRecord,
    existing_findings: list[RadarFinding] | None = None,
    existing_seen_hashes: set[str] | None = None,
    existing_run_history: list[ScanRunRecord] | None = None,
) -> None:
    """Merges new findings/run-record into the existing store and writes
    both files. Findings are newest-first; both lists are truncated to their
    max length so the repo stays bounded."""
    existing_findings = existing_findings if existing_findings is not None else load_findings()
    existing_seen_hashes = existing_seen_hashes if existing_seen_hashes is not None else load_seen_hashes()
    existing_run_history = existing_run_history if existing_run_history is not None else load_run_history()

    for f in new_findings:
        if not f.url_hash:
            f.url_hash = url_hash(f.source_url)
        if not f.id:
            f.id = f.url_hash

    all_findings = new_findings + existing_findings
    all_findings.sort(key=lambda f: f.retrieved_at, reverse=True)
    all_findings = all_findings[:MAX_FINDINGS]

    seen = existing_seen_hashes | {f.url_hash for f in new_findings}

    run_history = ([run_record] + existing_run_history)[:MAX_RUN_HISTORY]

    _write_json(FINDINGS_PATH, [_finding_to_dict(f) for f in all_findings])
    _write_json(
        STATE_PATH,
        {
            "seen_url_hashes": sorted(seen),
            "run_history": [asdict(r) for r in run_history],
        },
    )


def _finding_to_dict(f: RadarFinding) -> dict:
    d = asdict(f)
    return d
