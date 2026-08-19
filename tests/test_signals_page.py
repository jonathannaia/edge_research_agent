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

        # Card-level: real issuer, source name, date, source link, excerpt.
        assert filing.corp_name in all_text
        assert filing.source_name in all_text
        assert "View source document" in all_text
        assert filing.source_url in all_text
        assert candidate.excerpt_original in all_text

        # Open the drawer ("Review evidence") and confirm the same
        # discipline holds there — no demo language, real excerpt, working
        # source link. The click-triggered rerun must stay inside this
        # `with patch(...)` block: get_settings() is re-resolved on every
        # rerun, so a rerun outside the patch would silently fall back to
        # the real production cache_dir instead of tmp_path.
        drawer_buttons = [b for b in at.button if (b.key or "").startswith("open-drawer-")]
        assert len(drawer_buttons) == 1
        drawer_buttons[0].click().run()
        assert not at.exception

        drawer_text = " ".join(m.value for m in at.markdown)
        assert "EevaResearch Demo Data" not in drawer_text
        assert "sample evidence item" not in drawer_text
        assert "No live filing connected in this phase" not in drawer_text
        assert filing.corp_name in drawer_text
        assert filing.source_name in drawer_text
        assert candidate.excerpt_original in drawer_text

        link_buttons = at.get("link_button")
        assert len(link_buttons) == 1
        assert link_buttons[0].proto.url == filing.source_url
        assert link_buttons[0].proto.label == "Open filing"


def test_signals_page_shows_real_edgar_signal_with_direct_document_link(tmp_path):
    filing = FilingEvent(
        rcept_no="0001045810-26-000069", corp_code="0001045810", corp_name="NVIDIA", stock_code="NVDA",
        report_nm="8-K", rcept_dt="2026-08-17", flr_nm="NVIDIA", pblntf_ty="8-K", theme_slug="ai-buildout",
        source_url="https://www.sec.gov/Archives/edgar/data/1045810/000104581026000069/",
        retrieved_at=_now_iso(), source_name="SEC EDGAR", original_language="English",
        primary_document="nvda-20260817.htm",
    )
    candidate = CandidateSignal(
        id="edgar-cand-0001045810-26-000069", filing=filing, matched_rules=["earnings_or_results:8-K item 2.02"],
        confidence="High", status=CandidateStatus.NEEDS_REVIEW, extraction_state=ExtractionState.EXTRACTED,
        excerpt_original="Item 2.02 Results of Operations and Financial Condition.",
        state_history=[StateTransition(status=CandidateStatus.NEEDS_REVIEW, at=_now_iso())],
    )
    candidate_store.save_candidates(tmp_path, {candidate.id: candidate}, "edgar_candidates.json")

    direct_document_url = "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000069/nvda-20260817.htm"

    settings = Settings(cache_dir=tmp_path)
    with patch("src.data_access.container.get_settings", return_value=settings):
        at = AppTest.from_file(str(_HARNESS), default_timeout=10)
        at.run()

        assert not at.exception
        all_text = " ".join(m.value for m in at.markdown)
        assert filing.corp_name in all_text
        assert filing.source_name in all_text
        assert ":gray-badge[Sample]" not in all_text
        assert "demo data in this phase" not in all_text
        # The card's clickable source link must be the direct document
        # URL, not the bare accession-directory URL.
        assert direct_document_url in all_text
        assert candidate.excerpt_original in all_text

        drawer_buttons = [b for b in at.button if (b.key or "").startswith("open-drawer-")]
        assert len(drawer_buttons) == 1
        drawer_buttons[0].click().run()
        assert not at.exception

        drawer_text = " ".join(m.value for m in at.markdown)
        assert "EevaResearch Demo Data" not in drawer_text
        assert "sample evidence item" not in drawer_text
        assert "No live filing connected in this phase" not in drawer_text
        assert filing.corp_name in drawer_text
        assert candidate.excerpt_original in drawer_text

        link_buttons = at.get("link_button")
        assert len(link_buttons) == 1
        assert link_buttons[0].proto.url == direct_document_url


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


_DEMO_SIGNAL_CARD_SCRIPT = """
from src.config.settings import get_settings
from src.data_access.demo.signal_repository import DemoSignalRepository
from src.data_access.demo.evidence_repository import DemoEvidenceRepository
from src.ui.components.cards import signal_card

settings = get_settings()
signal = DemoSignalRepository(settings).get_all_signals()[0]
evidence_repository = DemoEvidenceRepository(settings)
signal_card(signal, evidence_repository=evidence_repository)
"""


def test_demo_signal_still_shows_sample_badge_and_demo_drawer_text():
    """Regression check: is_demo=True signals must keep their existing
    demo presentation exactly as before — only real (is_demo=False)
    signals lose the "Sample"/"EevaResearch Demo Data" language."""
    at = AppTest.from_string(_DEMO_SIGNAL_CARD_SCRIPT, default_timeout=10)
    at.run()
    assert not at.exception

    all_text = " ".join(m.value for m in at.markdown)
    assert ":gray-badge[Sample]" in all_text

    drawer_buttons = [b for b in at.button if (b.key or "").startswith("open-drawer-")]
    assert len(drawer_buttons) == 1
    drawer_buttons[0].click().run()
    assert not at.exception

    drawer_text = " ".join(m.value for m in at.markdown)
    assert "EevaResearch Demo Data" in drawer_text
