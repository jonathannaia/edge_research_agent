"""Signals page — AppTest-level checks that real DART/EDINET candidates
render as Signal cards with no demo/sample badge, and that a truthful
empty state appears when no real candidate currently qualifies. Patches
src.data_access.container.get_settings (not
src.ui.pages.signals.get_settings — the page never imports get_settings
directly; it goes through get_repositories(), which resolves settings
inside container.py) to point the real RadarSignalRepository at an
isolated tmp_path cache dir instead of the real one."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src.config.settings import Settings
from src.data_access.dart import candidate_store
from src.models.models import CandidateSignal, CandidateStatus, ExtractionState, FilingEvent, StateTransition

_HARNESS = Path(__file__).parent / "apptest_pages" / "signals_page.py"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dart_filing() -> FilingEvent:
    return FilingEvent(
        rcept_no="20260812000200", corp_code="00164779", corp_name="SK Hynix", stock_code="000660",
        report_nm="조회공시요구(풍문또는보도)에대한답변(미확정)", rcept_dt="20260812", flr_nm="SK 하이닉스",
        theme_slug="memory", source_url="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260812000200",
        retrieved_at=_now_iso(), source_name="OpenDART / DART",
    )


def test_signals_page_shows_real_dart_signal_with_no_sample_badge(tmp_path):
    filing = _dart_filing()
    candidate = CandidateSignal(
        id="cand-signals-page-1", filing=filing, matched_rules=["market_rumor_response:rumor_inquiry_or_response:풍문또는보도"],
        confidence="Moderate", status=CandidateStatus.NEEDS_REVIEW, extraction_state=ExtractionState.EXTRACTED,
        excerpt_original="한국거래소의조회공시요구에대한답변...",
        state_history=[StateTransition(status=CandidateStatus.NEEDS_REVIEW, at=_now_iso())],
    )
    candidate_store.save_candidates(tmp_path, {candidate.id: candidate}, "dart_candidates.json")

    settings = Settings(cache_dir=tmp_path)
    with patch("src.data_access.container.get_settings", return_value=settings):
        at = AppTest.from_file(str(_HARNESS), default_timeout=10)
        at.run()

    assert not at.exception
    all_text = " ".join(m.value for m in at.markdown)
    assert filing.report_nm in all_text
    assert ":gray-badge[Sample]" not in all_text  # signal_card() only shows this for is_demo candidates
    assert "demo data in this phase" not in all_text


def test_signals_page_shows_truthful_empty_state_when_no_eligible_candidates(tmp_path):
    deferred_filing = FilingEvent(
        rcept_no="20260812000201", corp_code="00164779", corp_name="SK Hynix", stock_code="000660",
        report_nm="유상증자 결정", rcept_dt="20260812", flr_nm="SK 하이닉스", theme_slug="memory",
        source_url="https://dart.fss.or.kr/x", retrieved_at=_now_iso(), source_name="OpenDART / DART",
    )
    deferred = CandidateSignal(
        id="cand-signals-page-deferred", filing=deferred_filing, matched_rules=["financing:capital_raise_or_treasury_stock:유상증자"],
        confidence="Moderate", status=CandidateStatus.PROCESSING_DEFERRED,
        state_history=[StateTransition(status=CandidateStatus.PROCESSING_DEFERRED, at=_now_iso())],
    )
    not_material_filing = FilingEvent(
        rcept_no="20260812000202", corp_code="00164779", corp_name="SK Hynix", stock_code="000660",
        report_nm="실적 발표", rcept_dt="20260812", flr_nm="SK 하이닉스", theme_slug="memory",
        source_url="https://dart.fss.or.kr/x", retrieved_at=_now_iso(), source_name="OpenDART / DART",
    )
    not_material = CandidateSignal(
        id="cand-signals-page-notmat", filing=not_material_filing, matched_rules=["earnings:earnings_or_results_report:실적"],
        confidence="Moderate", status=CandidateStatus.NOT_MATERIAL,
        state_history=[StateTransition(status=CandidateStatus.NOT_MATERIAL, at=_now_iso())],
    )
    candidate_store.save_candidates(
        tmp_path, {deferred.id: deferred, not_material.id: not_material}, "dart_candidates.json",
    )

    settings = Settings(cache_dir=tmp_path)
    with patch("src.data_access.container.get_settings", return_value=settings):
        at = AppTest.from_file(str(_HARNESS), default_timeout=10)
        at.run()

    assert not at.exception
    all_text = " ".join(m.value for m in at.markdown)
    assert "No eligible filings yet." in all_text
    assert ":gray-badge[Sample]" not in all_text
    # The old fabricated empty-state copy must be gone.
    assert "TDnet" not in all_text
    assert "CNINFO" not in all_text
    assert "HKEX" not in all_text
    assert deferred_filing.report_nm not in all_text
    assert not_material_filing.report_nm not in all_text


def test_signals_page_empty_state_when_no_cache_files_exist(tmp_path):
    settings = Settings(cache_dir=tmp_path)
    with patch("src.data_access.container.get_settings", return_value=settings):
        at = AppTest.from_file(str(_HARNESS), default_timeout=10)
        at.run()

    assert not at.exception
    all_text = " ".join(m.value for m in at.markdown)
    assert "No eligible filings yet." in all_text
    assert ":gray-badge[Sample]" not in all_text
