"""edinet_pipeline — the bounded, idempotent orchestration entry point
connecting scan_service, document_service, and the translation lifecycle
seam (no provider call — see module docstring). Fully mocked
EdinetClient, zero network, no Subscription-Key required."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.config.tracked_companies import TrackedCompany
from src.data_access.dart import candidate_store
from src.data_access.edinet import edinet_pipeline
from src.data_access.edinet.errors import EdinetNotFoundError
from src.models.models import CandidateStatus, ExtractionState, TranslationState

_TEST_MAP = {"010:030": "earnings_or_results"}

_ACME = TrackedCompany(
    name="Acme Test Co", exchange="TSE", krx_code="1234", source="EDINET",
    themes=("ai-buildout",), corp_code="E00001",
)
_SAMPLE = TrackedCompany(
    name="Sample Electric", exchange="TSE", krx_code="5678", source="EDINET",
    themes=("memory",), corp_code="E00002",
)


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _result(doc_id, edinet_code, sec_code, ordinance="010", form="030", submit_date_time="2026-08-17 09:00"):
    return {
        "docID": doc_id, "docTypeCode": "120", "ordinanceCode": ordinance, "formCode": form,
        "filerName": "Test Filer", "docDescription": "Test Filing", "edinetCode": edinet_code, "secCode": sec_code,
        "submitDateTime": submit_date_time,
    }


def _envelope(results, count=None, status="200", message="OK"):
    count = len(results) if count is None else count
    return {"metadata": {"status": status, "message": message, "resultset": {"count": count}}, "results": results}


def _make_client(results_by_date_and_company: dict, document_by_doc_id: dict | None = None):
    document_by_doc_id = document_by_doc_id or {}
    client = MagicMock()

    def _get_document_list(date_str, type_=2):
        return results_by_date_and_company.get(date_str, _envelope([]))

    def _fetch_document(doc_id, type_):
        result = document_by_doc_id.get(doc_id)
        if isinstance(result, Exception):
            raise result
        return result if result is not None else b"<html><body><p>generic filing content</p></body></html>"

    client.get_document_list.side_effect = _get_document_list
    client.fetch_document.side_effect = _fetch_document
    return client


def _run_pipeline_with_map(client, companies, cache_dir, **kwargs):
    """edinet_pipeline.run_pipeline doesn't thread code_category_map
    through (see scan_service.py's docstring — it's a scan()-level test
    knob, empty by default in real use). Tests that need a candidate to
    exist call scan_service.scan directly with the test map first, then
    exercise the pipeline's own candidate_store/process_candidate logic
    from there."""
    from src.data_access.edinet import scan_service
    scan_result = scan_service.scan(client, companies, cache_dir, code_category_map=_TEST_MAP)
    candidate_store.upsert_new_candidates(cache_dir, list(scan_result.new_candidate_signals), edinet_pipeline.CANDIDATE_STORE_FILENAME)
    return scan_result


def test_process_candidate_extracts_and_reaches_needs_review(tmp_path):
    client = _make_client(
        {_today(): _envelope([_result("S100A", "E00001", "1234")])},
        {"S100A": b"<html><body><p>Disclosure content.</p></body></html>"},
    )
    _run_pipeline_with_map(client, [_ACME], tmp_path)
    candidate_id = next(iter(candidate_store.load_candidates(tmp_path, edinet_pipeline.CANDIDATE_STORE_FILENAME)))

    result = edinet_pipeline.process_single_candidate(client, candidate_id, tmp_path)

    assert result.status == CandidateStatus.NEEDS_REVIEW
    assert result.extraction_state == ExtractionState.EXTRACTED
    assert "Disclosure content" in result.excerpt_original


def test_successful_extraction_sets_translation_state_to_pending_not_translated(tmp_path):
    # Translation lifecycle seam is exercised (PENDING), but no provider
    # call ever happens this gate (see module docstring).
    client = _make_client(
        {_today(): _envelope([_result("S100A", "E00001", "1234")])},
        {"S100A": b"<html><body><p>Disclosure content.</p></body></html>"},
    )
    _run_pipeline_with_map(client, [_ACME], tmp_path)
    candidate_id = next(iter(candidate_store.load_candidates(tmp_path, edinet_pipeline.CANDIDATE_STORE_FILENAME)))

    result = edinet_pipeline.process_single_candidate(client, candidate_id, tmp_path)

    assert result.translation_state == TranslationState.PENDING
    assert result.title_translation is None
    assert result.excerpt_translation is None


def test_no_ownership_materiality_gate_applied(tmp_path):
    client = _make_client(
        {_today(): _envelope([_result("S100OWN", "E00001", "1234", ordinance="010", form="040")])},
        {"S100OWN": b"<html><body><p>Large shareholding report.</p></body></html>"},
    )
    scan_map = {"010:040": "ownership_or_large_shareholding"}
    from src.data_access.edinet import scan_service
    scan_result = scan_service.scan(client, [_ACME], tmp_path, code_category_map=scan_map)
    candidate_store.upsert_new_candidates(tmp_path, list(scan_result.new_candidate_signals), edinet_pipeline.CANDIDATE_STORE_FILENAME)
    candidate_id = next(iter(candidate_store.load_candidates(tmp_path, edinet_pipeline.CANDIDATE_STORE_FILENAME)))

    result = edinet_pipeline.process_single_candidate(client, candidate_id, tmp_path)

    assert result.status == CandidateStatus.NEEDS_REVIEW
    assert result.materiality_assessment == "Not assessed"


def test_retrieval_failure_reaches_retrieval_failed_status(tmp_path):
    client = _make_client(
        {_today(): _envelope([_result("S100FAIL", "E00001", "1234")])},
        {"S100FAIL": EdinetNotFoundError(404, "not found")},
    )
    _run_pipeline_with_map(client, [_ACME], tmp_path)
    candidate_id = next(iter(candidate_store.load_candidates(tmp_path, edinet_pipeline.CANDIDATE_STORE_FILENAME)))

    result = edinet_pipeline.process_single_candidate(client, candidate_id, tmp_path)

    assert result.status == CandidateStatus.RETRIEVAL_FAILED


def test_binary_document_reaches_parse_failed_status(tmp_path):
    client = _make_client(
        {_today(): _envelope([_result("S100BIN", "E00001", "1234")])},
        {"S100BIN": b"\x50\x4b\x03\x04" + bytes(range(200))},
    )
    _run_pipeline_with_map(client, [_ACME], tmp_path)
    candidate_id = next(iter(candidate_store.load_candidates(tmp_path, edinet_pipeline.CANDIDATE_STORE_FILENAME)))

    result = edinet_pipeline.process_single_candidate(client, candidate_id, tmp_path)

    assert result.status == CandidateStatus.PARSE_FAILED


def test_process_single_candidate_returns_none_for_unknown_id(tmp_path):
    client = MagicMock()
    assert edinet_pipeline.process_single_candidate(client, "edinet-cand-does-not-exist", tmp_path) is None


def test_clamp_max_candidates():
    assert edinet_pipeline.clamp_max_candidates(9999) == edinet_pipeline.MAX_CANDIDATES_PER_SCAN_CEILING
    assert edinet_pipeline.clamp_max_candidates(0) == 1


def test_run_pipeline_with_zero_tracked_companies_reports_zero_everything(tmp_path):
    # The real Gate 1 shape: no EDINET company is tracked yet.
    client = MagicMock()
    client.get_document_list.return_value = _envelope([])

    report = edinet_pipeline.run_pipeline(client, [], tmp_path)

    assert report.new_filing_events == 0
    assert report.candidates_detected == 0
    assert report.candidates_processed == 0
    assert report.source == "EDINET"


def test_run_pipeline_processes_detected_candidates_within_budget(tmp_path):
    client = _make_client(
        {_today(): _envelope([_result("S100A", "E00001", "1234", ordinance="010", form="030")])},
        {"S100A": b"<html><body><p>Disclosure content.</p></body></html>"},
    )
    # run_pipeline itself uses scan_service.scan with the real (empty)
    # default map, so it detects zero candidates here — this test proves
    # run_pipeline's own end-to-end wiring (scan -> store -> process
    # loop) runs cleanly with zero eligible candidates, without needing
    # the test-only code_category_map override.
    report = edinet_pipeline.run_pipeline(client, [_ACME], tmp_path)

    assert report.new_filing_events == 1
    assert report.candidates_detected == 0
    assert report.candidates_processed == 0


def test_pipeline_is_idempotent_across_repeated_process_single_candidate_calls(tmp_path):
    client = _make_client(
        {_today(): _envelope([_result("S100A", "E00001", "1234")])},
        {"S100A": b"<html><body><p>Disclosure content.</p></body></html>"},
    )
    _run_pipeline_with_map(client, [_ACME], tmp_path)
    candidate_id = next(iter(candidate_store.load_candidates(tmp_path, edinet_pipeline.CANDIDATE_STORE_FILENAME)))

    first = edinet_pipeline.process_single_candidate(client, candidate_id, tmp_path)
    second = edinet_pipeline.process_single_candidate(client, candidate_id, tmp_path)

    assert first.status == second.status == CandidateStatus.NEEDS_REVIEW
    store = candidate_store.load_candidates(tmp_path, edinet_pipeline.CANDIDATE_STORE_FILENAME)
    assert len(store) == 1  # no duplicate CandidateSignal
    from src.data_access.edinet import scan_service
    assert len(scan_service.load_filing_events(tmp_path)) == 1  # no duplicate FilingEvent


def test_partial_failure_on_one_company_does_not_block_the_other(tmp_path):
    client = MagicMock()

    def _get_document_list(date_str, type_=2):
        return _envelope([_result("S100A", "E00001", "1234"), _result("S100B", "E00002", "5678")])

    client.get_document_list.side_effect = _get_document_list
    client.fetch_document.return_value = b"<html><body><p>content</p></body></html>"

    from src.data_access.edinet import scan_service
    scan_result = scan_service.scan(client, [_ACME, _SAMPLE], tmp_path, code_category_map=_TEST_MAP)

    assert len(scan_result.new_filing_events) == 2
