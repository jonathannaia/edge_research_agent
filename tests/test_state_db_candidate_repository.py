"""state_db.candidate_repository — candidate/filing-event round-trip,
idempotent upsert, optimistic-locking review updates, and state-history
append semantics. Mirrors the intent of tests/test_candidate_store.py's
existing JSON-backed assertions against the SQLite backend — a separate
file rather than a shared parametrization, since the two backends have
different call signatures (a connection vs. a cache_dir) and refactoring
the existing JSON test file to share fixtures is out of this phase's
scope. In-memory SQLite only."""
from __future__ import annotations

from datetime import datetime, timezone

from src.data_access.state_db import candidate_repository, connection, schema
from src.models.models import CandidateSignal, CandidateStatus, FilingEvent, StateTransition, Translation


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conn():
    conn = connection.connect_in_memory()
    schema.migrate(conn)
    return conn


def _edgar_filing(rcept_no: str = "0001193125-26-354029", corp_code: str = "0000002488", **overrides) -> FilingEvent:
    defaults = dict(
        rcept_no=rcept_no, corp_code=corp_code, corp_name="Advanced Micro Devices", stock_code="AMD",
        report_nm="8-K", rcept_dt="2026-08-17", flr_nm="Advanced Micro Devices", pblntf_ty="8-K",
        theme_slug="ai-buildout", subtheme_slug="compute-accelerators",
        source_url=f"https://www.sec.gov/Archives/edgar/data/{corp_code}/{rcept_no}/",
        retrieved_at=_now(), source_name="SEC EDGAR", original_language="English",
        primary_document="ex99.htm",
    )
    defaults.update(overrides)
    return FilingEvent(**defaults)


def _dart_filing(rcept_no: str = "20260819000254", **overrides) -> FilingEvent:
    defaults = dict(
        rcept_no=rcept_no, corp_code="00164779", corp_name="SK Hynix", stock_code="000660",
        report_nm="주요사항보고서", rcept_dt="20260819", flr_nm="SK하이닉스",
        theme_slug="memory", source_url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
        retrieved_at=_now(), source_name="OpenDART / DART",
    )
    defaults.update(overrides)
    return FilingEvent(**defaults)


def _candidate(candidate_id: str, filing: FilingEvent, **overrides) -> CandidateSignal:
    defaults = dict(
        id=candidate_id, filing=filing, matched_rules=["material_agreement:8-K item 1.01"],
        confidence="Moderate", status=CandidateStatus.CANDIDATE_DETECTED,
        state_history=[StateTransition(status=CandidateStatus.CANDIDATE_DETECTED, at=_now())],
    )
    defaults.update(overrides)
    return CandidateSignal(**defaults)


# --- 4. Candidate insert/upsert idempotency by existing candidate ID ---

def test_upsert_new_candidates_inserts_once():
    conn = _conn()
    filing = _edgar_filing()
    candidate = _candidate("edgar-cand-0001193125-26-354029", filing)
    result = candidate_repository.upsert_new_candidates(conn, "SEC EDGAR", [candidate])
    assert list(result.keys()) == ["edgar-cand-0001193125-26-354029"]


def test_upsert_new_candidates_does_not_overwrite_existing_processing_state():
    conn = _conn()
    filing = _edgar_filing()
    candidate = _candidate("edgar-cand-0001193125-26-354029", filing)
    candidate_repository.upsert_new_candidates(conn, "SEC EDGAR", [candidate])

    # A later scan re-detects the "same" filing (e.g. a repeat scan) —
    # upserting it again must never touch the already-published status.
    version = candidate_repository.get_candidate_version(conn, candidate.id)
    published = _candidate(candidate.id, filing, status=CandidateStatus.PUBLISHED, reviewed_at=_now())
    candidate_repository.update_candidate(conn, published, expected_version=version)

    candidate_repository.upsert_new_candidates(conn, "SEC EDGAR", [candidate])  # same detected-state candidate again
    reloaded = candidate_repository.get_candidate(conn, candidate.id)
    assert reloaded.status == CandidateStatus.PUBLISHED  # untouched by the repeat upsert


def test_upsert_new_candidates_is_source_scoped():
    conn = _conn()
    edgar_candidate = _candidate("edgar-cand-1", _edgar_filing("1"))
    dart_candidate = _candidate("cand-1", _dart_filing("1"))
    candidate_repository.upsert_new_candidates(conn, "SEC EDGAR", [edgar_candidate])
    candidate_repository.upsert_new_candidates(conn, "OpenDART / DART", [dart_candidate])
    assert set(candidate_repository.load_candidates(conn, "SEC EDGAR").keys()) == {"edgar-cand-1"}
    assert set(candidate_repository.load_candidates(conn, "OpenDART / DART").keys()) == {"cand-1"}


# --- 5. Filing-event source-aware dedup semantics (through the candidate path) ---

def test_two_candidates_same_accession_different_source_do_not_collide():
    # A pathological but real structural check: (corp_code, rcept_no)
    # alone must never be treated as globally unique — source_name is
    # part of the identity.
    conn = _conn()
    edgar_candidate = _candidate("edgar-cand-X", _edgar_filing(rcept_no="X", corp_code="0000000009", source_name="SEC EDGAR"))
    dart_candidate = _candidate("cand-X", _dart_filing(rcept_no="X", corp_code="0000000009"))
    candidate_repository.upsert_new_candidates(conn, "SEC EDGAR", [edgar_candidate])
    candidate_repository.upsert_new_candidates(conn, "OpenDART / DART", [dart_candidate])
    assert candidate_repository.get_candidate(conn, "edgar-cand-X").filing.source_name == "SEC EDGAR"
    assert candidate_repository.get_candidate(conn, "cand-X").filing.source_name == "OpenDART / DART"


# --- 7. Full round-trip, including translations, excerpts, and materiality ---

def test_round_trips_full_processing_state_including_translations_and_history():
    conn = _conn()
    filing = _dart_filing()
    candidate = _candidate(
        "cand-20260819000254", filing,
        confidence="High", status=CandidateStatus.PUBLISHED,
        excerpt_original="자기주식취득 결정...", reviewed_at=_now(), reviewed_note="Approved — real buyback.",
        title_translation=Translation(
            translated_text="Decision on treasury stock acquisition", provider="DeepL",
            source_lang="ko", target_lang="en", translated_at=_now(),
        ),
        excerpt_translation=Translation(
            translated_text="Decision to acquire treasury stock...", provider="DeepL",
            source_lang="ko", target_lang="en", translated_at=_now(), model="deepl-pro",
        ),
        materiality_assessment="Material — real, large buyback.",
        state_history=[
            StateTransition(status=CandidateStatus.CANDIDATE_DETECTED, at=_now()),
            StateTransition(status=CandidateStatus.EXTRACTED, at=_now(), detail="extraction ok"),
            StateTransition(status=CandidateStatus.PUBLISHED, at=_now(), detail="approved"),
        ],
    )
    candidate_repository.upsert_new_candidates(conn, "OpenDART / DART", [candidate])
    reloaded = candidate_repository.get_candidate(conn, candidate.id)

    assert reloaded.filing == filing
    assert reloaded.confidence == "High"
    assert reloaded.status == CandidateStatus.PUBLISHED
    assert reloaded.excerpt_original == candidate.excerpt_original
    assert reloaded.reviewed_note == candidate.reviewed_note
    assert reloaded.title_translation == candidate.title_translation
    assert reloaded.excerpt_translation == candidate.excerpt_translation
    assert reloaded.materiality_assessment == candidate.materiality_assessment
    assert [t.status for t in reloaded.state_history] == [
        CandidateStatus.CANDIDATE_DETECTED, CandidateStatus.EXTRACTED, CandidateStatus.PUBLISHED,
    ]


# --- 8. State transitions append and load in expected order ---

def test_state_transitions_load_in_append_order():
    conn = _conn()
    filing = _edgar_filing()
    candidate = _candidate(
        "edgar-cand-order-test", filing,
        state_history=[
            StateTransition(status=CandidateStatus.CANDIDATE_DETECTED, at="2026-08-17T00:00:00+00:00"),
            StateTransition(status=CandidateStatus.EXTRACTED, at="2026-08-17T01:00:00+00:00"),
        ],
    )
    candidate_repository.upsert_new_candidates(conn, "SEC EDGAR", [candidate])
    version = candidate_repository.get_candidate_version(conn, candidate.id)

    updated = _candidate(
        candidate.id, filing, status=CandidateStatus.PUBLISHED,
        state_history=candidate.state_history + [
            StateTransition(status=CandidateStatus.PUBLISHED, at="2026-08-17T02:00:00+00:00", detail="published"),
        ],
    )
    outcome = candidate_repository.update_candidate(conn, updated, expected_version=version)
    assert outcome.status == "updated"
    history = outcome.current.state_history
    assert [t.at for t in history] == ["2026-08-17T00:00:00+00:00", "2026-08-17T01:00:00+00:00", "2026-08-17T02:00:00+00:00"]


def test_updating_a_candidate_never_duplicates_already_stored_transitions():
    conn = _conn()
    filing = _edgar_filing()
    candidate = _candidate("edgar-cand-no-dup", filing)
    candidate_repository.upsert_new_candidates(conn, "SEC EDGAR", [candidate])
    version = candidate_repository.get_candidate_version(conn, candidate.id)

    # Caller resubmits the SAME state_history it already had, unchanged.
    same_history_update = _candidate(candidate.id, filing, status=CandidateStatus.CANDIDATE_DETECTED, state_history=candidate.state_history)
    outcome = candidate_repository.update_candidate(conn, same_history_update, expected_version=version)
    assert len(outcome.current.state_history) == 1  # not duplicated


# --- 11. Optimistic-lock conflict rejects the stale update, preserves the newer record ---

def test_stale_expected_version_is_rejected_and_newer_record_preserved():
    conn = _conn()
    filing = _edgar_filing()
    candidate = _candidate("edgar-cand-race", filing)
    candidate_repository.upsert_new_candidates(conn, "SEC EDGAR", [candidate])
    v1 = candidate_repository.get_candidate_version(conn, candidate.id)

    # First reviewer publishes.
    published = _candidate(candidate.id, filing, status=CandidateStatus.PUBLISHED, reviewed_note="First reviewer")
    first = candidate_repository.update_candidate(conn, published, expected_version=v1)
    assert first.status == "updated"

    # A second writer, still holding the STALE v1 it read before the
    # first update landed, tries to write a conflicting decision.
    stale_dismiss = _candidate(candidate.id, filing, status=CandidateStatus.DISMISSED, reviewed_note="Second reviewer — stale")
    second = candidate_repository.update_candidate(conn, stale_dismiss, expected_version=v1)

    assert second.status == "conflict"
    assert second.current.status == CandidateStatus.PUBLISHED  # the first reviewer's decision, untouched
    assert second.current.reviewed_note == "First reviewer"

    on_disk = candidate_repository.get_candidate(conn, candidate.id)
    assert on_disk.status == CandidateStatus.PUBLISHED
    assert on_disk.reviewed_note == "First reviewer"


def test_update_of_a_nonexistent_candidate_is_reported_not_found():
    conn = _conn()
    ghost = _candidate("edgar-cand-ghost", _edgar_filing(rcept_no="ghost", corp_code="0000000099"))
    outcome = candidate_repository.update_candidate(conn, ghost, expected_version=1)
    assert outcome.status == "not_found"
    assert outcome.current is None


def test_correct_version_update_succeeds_and_increments_version():
    conn = _conn()
    filing = _edgar_filing()
    candidate = _candidate("edgar-cand-v", filing)
    candidate_repository.upsert_new_candidates(conn, "SEC EDGAR", [candidate])
    v1 = candidate_repository.get_candidate_version(conn, candidate.id)
    assert v1 == 1

    published = _candidate(candidate.id, filing, status=CandidateStatus.PUBLISHED)
    outcome = candidate_repository.update_candidate(conn, published, expected_version=v1)
    assert outcome.status == "updated"
    assert candidate_repository.get_candidate_version(conn, candidate.id) == 2
