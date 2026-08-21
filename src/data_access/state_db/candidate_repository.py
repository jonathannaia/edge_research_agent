"""SQLite-backed CandidateSignal storage — the transactional replacement
target for src/data_access/dart/candidate_store.py's whole-file JSON
read-modify-write. Narrow and source-agnostic, same shared-module
convention as the JSON store it mirrors.

Deliberate divergence from the JSON store's read behavior: functions
here never catch sqlite3 errors — a database failure propagates as a
real exception rather than becoming an empty result (see this package's
own __init__.py docstring for why)."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from src.data_access.state_db import filing_event_repository
from src.data_access.state_db.connection import transaction
from src.models.models import (
    CandidateSignal,
    CandidateStatus,
    ExcerptQuality,
    ExtractionState,
    StateTransition,
    Translation,
    TranslationState,
)


@dataclass(frozen=True)
class UpdateOutcome:
    """Result of an optimistic-locking update attempt — always returned,
    never raised, matching this codebase's existing "always return a
    result, never make the caller catch an exception for an expected
    outcome" convention (CikResolutionResult, DiscoveryScanResult, etc.).

    status is one of:
      "updated"   — the write succeeded; `current` is the new record.
      "conflict"  — `expected_version` didn't match the stored version;
                    the newer stored record is returned UNCHANGED in
                    `current` — the caller's update was never applied.
      "not_found" — no candidate with this id exists; `current` is None.
    """

    status: str
    current: CandidateSignal | None


def _translation_to_json(translation: Translation | None) -> str | None:
    return json.dumps(asdict(translation)) if translation is not None else None


def _translation_from_json(raw: str | None) -> Translation | None:
    return Translation(**json.loads(raw)) if raw else None


def _row_to_candidate(conn: sqlite3.Connection, row: sqlite3.Row) -> CandidateSignal:
    filing = filing_event_repository.get_filing_event(
        conn, row["source"], row["filing_corp_code"], row["filing_rcept_no"]
    )
    if filing is None:
        raise LookupError(
            f"candidate {row['id']!r} references a missing filing_events row "
            f"({row['source']!r}, {row['filing_corp_code']!r}, {row['filing_rcept_no']!r}) — "
            "this indicates a foreign-key/data-integrity problem, not an absent candidate."
        )
    history_rows = conn.execute(
        "SELECT status, at, detail FROM state_transitions WHERE candidate_id = ? ORDER BY id ASC",
        (row["id"],),
    ).fetchall()
    state_history = [
        StateTransition(status=CandidateStatus(h["status"]), at=h["at"], detail=h["detail"])
        for h in history_rows
    ]
    return CandidateSignal(
        id=row["id"],
        filing=filing,
        matched_rules=json.loads(row["matched_rules_json"]),
        confidence=row["confidence"],
        status=CandidateStatus(row["status"]),
        extraction_state=ExtractionState(row["extraction_state"]),
        translation_state=TranslationState(row["translation_state"]),
        excerpt_quality=ExcerptQuality(row["excerpt_quality"]),
        excerpt_original=row["excerpt_original"],
        title_translation=_translation_from_json(row["title_translation_json"]),
        excerpt_translation=_translation_from_json(row["excerpt_translation_json"]),
        reviewed_at=row["reviewed_at"],
        reviewed_note=row["reviewed_note"],
        state_history=state_history,
        materiality_assessment=row["materiality_assessment"],
    )


def get_candidate(conn: sqlite3.Connection, candidate_id: str) -> CandidateSignal | None:
    row = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
    return _row_to_candidate(conn, row) if row is not None else None


def get_candidate_version(conn: sqlite3.Connection, candidate_id: str) -> int | None:
    row = conn.execute("SELECT version FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
    return row["version"] if row is not None else None


def load_candidates(conn: sqlite3.Connection, source: str) -> dict[str, CandidateSignal]:
    rows = conn.execute("SELECT id FROM candidates WHERE source = ?", (source,)).fetchall()
    return {row["id"]: get_candidate(conn, row["id"]) for row in rows}


def _insert_candidate(conn: sqlite3.Connection, candidate: CandidateSignal, now: str) -> None:
    filing = candidate.filing
    conn.execute(
        """
        INSERT INTO candidates (
            id, source, filing_corp_code, filing_rcept_no, matched_rules_json, confidence, status,
            extraction_state, translation_state, excerpt_quality, excerpt_original,
            title_translation_json, excerpt_translation_json, reviewed_at, reviewed_note,
            materiality_assessment, version, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (
            candidate.id, filing.source_name, filing.corp_code, filing.rcept_no,
            json.dumps(list(candidate.matched_rules)), candidate.confidence, candidate.status.value,
            candidate.extraction_state.value, candidate.translation_state.value, candidate.excerpt_quality.value,
            candidate.excerpt_original, _translation_to_json(candidate.title_translation),
            _translation_to_json(candidate.excerpt_translation), candidate.reviewed_at, candidate.reviewed_note,
            candidate.materiality_assessment, now, now,
        ),
    )
    for transition in candidate.state_history:
        conn.execute(
            "INSERT INTO state_transitions (candidate_id, status, at, detail) VALUES (?, ?, ?, ?)",
            (candidate.id, transition.status.value, transition.at, transition.detail),
        )


def upsert_new_candidates(
    conn: sqlite3.Connection, source: str, new_candidates: list[CandidateSignal],
) -> dict[str, CandidateSignal]:
    """Adds any candidate ID not already present (inserting its parent
    filing_events row first, idempotently, via
    filing_event_repository.upsert_filing_event); leaves an existing
    entry's processing state untouched — same semantics as
    candidate_store.upsert_new_candidates. Returns the full, current
    store for `source` after the operation."""
    now = datetime.now(timezone.utc).isoformat()
    with transaction(conn):
        for candidate in new_candidates:
            exists = conn.execute("SELECT 1 FROM candidates WHERE id = ?", (candidate.id,)).fetchone()
            if exists is not None:
                continue
            filing_event_repository.upsert_filing_event(conn, candidate.filing)
            _insert_candidate(conn, candidate, now)
    return load_candidates(conn, source)


def update_candidate(
    conn: sqlite3.Connection, candidate: CandidateSignal, expected_version: int,
) -> UpdateOutcome:
    """Optimistic-locking update of one candidate's processing/review
    state. Succeeds only if `expected_version` matches the version
    currently stored — the caller must have read that version from a
    prior get_candidate()/get_candidate_version() call. A stale
    `expected_version` (someone else updated the candidate since this
    caller last read it) returns status="conflict" with the CURRENT,
    newer record — this caller's change is never applied and never
    silently overwrites the newer one. Appends any new StateTransition
    entries (state_history entries not already in the stored history,
    by (status, at, detail) — matching this codebase's "transitions are
    appended, never overwritten or replaced" rule) as new rows rather
    than rewriting history."""
    now = datetime.now(timezone.utc).isoformat()
    with transaction(conn):
        current_row = conn.execute("SELECT version FROM candidates WHERE id = ?", (candidate.id,)).fetchone()
        if current_row is None:
            return UpdateOutcome(status="not_found", current=None)

        cursor = conn.execute(
            """
            UPDATE candidates SET
                matched_rules_json = ?, confidence = ?, status = ?, extraction_state = ?,
                translation_state = ?, excerpt_quality = ?, excerpt_original = ?,
                title_translation_json = ?, excerpt_translation_json = ?, reviewed_at = ?,
                reviewed_note = ?, materiality_assessment = ?, version = version + 1, updated_at = ?
            WHERE id = ? AND version = ?
            """,
            (
                json.dumps(list(candidate.matched_rules)), candidate.confidence, candidate.status.value,
                candidate.extraction_state.value, candidate.translation_state.value,
                candidate.excerpt_quality.value, candidate.excerpt_original,
                _translation_to_json(candidate.title_translation),
                _translation_to_json(candidate.excerpt_translation), candidate.reviewed_at,
                candidate.reviewed_note, candidate.materiality_assessment, now,
                candidate.id, expected_version,
            ),
        )
        if cursor.rowcount == 0:
            # id existed (checked above) but the version didn't match —
            # a genuine conflict, not a missing row. Roll back to undo
            # nothing (no row was touched) and return the current record.
            conflict_current = get_candidate(conn, candidate.id)
            return UpdateOutcome(status="conflict", current=conflict_current)

        existing_history = conn.execute(
            "SELECT status, at, detail FROM state_transitions WHERE candidate_id = ?", (candidate.id,)
        ).fetchall()
        existing_keys = {(h["status"], h["at"], h["detail"]) for h in existing_history}
        for transition in candidate.state_history:
            key = (transition.status.value, transition.at, transition.detail)
            if key not in existing_keys:
                conn.execute(
                    "INSERT INTO state_transitions (candidate_id, status, at, detail) VALUES (?, ?, ?, ?)",
                    (candidate.id, transition.status.value, transition.at, transition.detail),
                )

        return UpdateOutcome(status="updated", current=get_candidate(conn, candidate.id))
