"""Radar Inbox page — fixture-driven render tests via AppTest, with
radar_inbox.get_settings monkeypatched to a tmp cache_dir seeded with
fixture data. Zero network calls, no real API key, and the real
data/cache/ (gitignored live pilot cache) is never touched."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src.config.settings import Settings
from src.data_access.dart import candidate_store, retry_policy
from src.models.models import (
    CandidateSignal,
    CandidateStatus,
    ExtractionState,
    FilingEvent,
    StateTransition,
    Translation,
    TranslationState,
)

_HARNESS = Path(__file__).parent / "apptest_pages" / "radar_inbox_page.py"


def _seed_corp_codes(cache_dir) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "005930": {"corp_code": "00126380", "corp_name": "삼성전자", "source": "OpenDART corpCode.xml", "retrieved_at": "2026-08-01T00:00:00+00:00"},
        "000660": {"corp_code": "00164779", "corp_name": "SK 하이닉스", "source": "OpenDART corpCode.xml", "retrieved_at": "2026-08-01T00:00:00+00:00"},
    }
    (cache_dir / "dart_corp_codes.json").write_text(json.dumps(payload))


def _filing(rcept_no: str, report_nm: str) -> FilingEvent:
    return FilingEvent(
        rcept_no=rcept_no, corp_code="00126380", corp_name="삼성전자", stock_code="005930",
        report_nm=report_nm, rcept_dt="20260812", flr_nm="삼성전자", theme_slug="memory",
        source_url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )


def _seed_filing_events(cache_dir, filings: list[FilingEvent]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    from dataclasses import asdict
    payload = {"seen_receipt_numbers": [f.rcept_no for f in filings], "filing_events": [asdict(f) for f in filings], "candidate_signals": []}
    (cache_dir / "dart_filing_events.json").write_text(json.dumps(payload, ensure_ascii=False))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _unconfigured_settings(cache_dir) -> Settings:
    # Every source-readiness field radar_inbox.py reads is explicitly
    # nulled here — this must represent "all sources unconfigured"
    # regardless of what the developer's own local .env holds. A field
    # left out of this call falls back to Settings' own
    # os.getenv-backed default_factory, which is exactly the isolation
    # gap that let a real local EDGE_EDINET_SUBSCRIPTION_KEY leak into
    # this fixture (see design/DECISIONS.md's Gate 5.1 entry).
    return Settings(
        dart_api_key=None, translation_api_key=None, edgar_user_agent=None,
        edinet_subscription_key=None, cache_dir=cache_dir,
    )


def test_radar_inbox_renders_missing_configuration_state(tmp_path):
    with patch("src.ui.pages.radar_inbox.get_settings", return_value=_unconfigured_settings(tmp_path)):
        at = AppTest.from_file(str(_HARNESS), default_timeout=10)
        at.run()

    assert not at.exception
    all_text = " ".join(m.value for m in at.markdown)
    assert "not configured" in all_text.lower()


def test_radar_inbox_edinet_scope_line_is_truthful_when_configured_but_unscanned(tmp_path):
    # Gate 7.1: the five real EDINET registry entries (tracked_companies.py)
    # are pre-resolved regardless of cache_dir, so a configured key alone
    # makes edinet_readiness.ready True — with zero live scans ever run,
    # this must say "configured; no live scan completed yet," never claim
    # calibration, active monitoring, currency, autonomy, or live signals.
    settings = Settings(
        dart_api_key=None, translation_api_key=None, edgar_user_agent=None,
        edinet_subscription_key="test-key", cache_dir=tmp_path,
    )
    with patch("src.ui.pages.radar_inbox.get_settings", return_value=settings):
        at = AppTest.from_file(str(_HARNESS), default_timeout=10)
        at.run()

    assert not at.exception
    all_text = " ".join(m.value for m in at.markdown).lower()
    assert "5 tracked companies configured" in all_text
    assert "no live scan completed yet" in all_text
    assert "filingevents: 0" in all_text
    assert "candidatesignals: 0" in all_text
    assert "last scan: none" in all_text
    for forbidden in ("calibrated", "actively monitored", "autonomous", "live signals"):
        assert forbidden not in all_text


def _seed_edinet_filing_events(cache_dir, filings: list[FilingEvent]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    from dataclasses import asdict
    payload = {"seen_keys": [f"EDINET:{f.corp_code}:{f.rcept_no}" for f in filings], "filing_events": [asdict(f) for f in filings], "candidate_signals": []}
    (cache_dir / "edinet_filing_events.json").write_text(json.dumps(payload, ensure_ascii=False))


def test_radar_inbox_shows_all_three_edinet_form_codes_for_a_softbank_shaped_event(tmp_path):
    # Gate 8.1 item 4/B: the real SoftBank Group annual-report triplet
    # (ordinanceCode="010", formCode="030000", docTypeCode="120") must be
    # visible in the rendered event, unconditioned by candidate presence
    # (an EDINET FilingEvent realistically has no candidate while the
    # category map stays empty).
    softbank_filing = FilingEvent(
        rcept_no="S100YGH5", corp_code="E02778", corp_name="SoftBank Group Corp.", stock_code="99840",
        report_nm="有価証券報告書－第46期(2025/04/01－2026/03/31)", rcept_dt="2026-06-22",
        flr_nm="ソフトバンクグループ株式会社", pblntf_ty="030000", pblntf_detail_ty="120", ordinance_code="010",
        theme_slug="ai-buildout", source_url="https://api.edinet-fsa.go.jp/api/v2/documents/S100YGH5",
        retrieved_at=datetime.now(timezone.utc).isoformat(), source_name="EDINET", original_language="Japanese",
    )
    _seed_edinet_filing_events(tmp_path, [softbank_filing])

    settings = Settings(
        dart_api_key=None, translation_api_key=None, edgar_user_agent=None,
        edinet_subscription_key="test-key", cache_dir=tmp_path,
    )
    with patch("src.ui.pages.radar_inbox.get_settings", return_value=settings):
        at = AppTest.from_file(str(_HARNESS), default_timeout=10)
        at.run()

    assert not at.exception
    all_text = " ".join(m.value for m in at.markdown)
    assert "Ordinance code" in all_text and "010" in all_text
    assert "Form code" in all_text and "030000" in all_text
    assert "Document type code" in all_text and "120" in all_text


def test_radar_inbox_missing_configuration_state_is_unaffected_by_local_env(tmp_path, monkeypatch):
    # Regression for the Gate 5 test-isolation defect: a real, locally
    # configured EDGE_EDINET_SUBSCRIPTION_KEY (or any other real
    # provider credential) must never be able to make this "everything
    # unconfigured" fixture report as configured. monkeypatch.setenv is
    # scoped to this test only and never touches the real .env file;
    # every field _unconfigured_settings() passes to Settings(...) is
    # explicit, so these env values are never actually read for this
    # assertion — that's the isolation property this test proves.
    monkeypatch.setenv("EDGE_EDINET_SUBSCRIPTION_KEY", "a-real-locally-configured-value")
    monkeypatch.setenv("EDGE_EDGAR_USER_AGENT", "EevaResearch test@example.com")
    monkeypatch.setenv("EDGE_DART_API_KEY", "a-real-dart-key")
    monkeypatch.setenv("EDGE_TRANSLATION_API_KEY", "a-real-translation-key")

    with patch("src.ui.pages.radar_inbox.get_settings", return_value=_unconfigured_settings(tmp_path)):
        at = AppTest.from_file(str(_HARNESS), default_timeout=10)
        at.run()

    assert not at.exception
    all_text = " ".join(m.value for m in at.markdown)
    assert "not configured" in all_text.lower()


def test_radar_inbox_renders_populated_list_with_expected_statuses(tmp_path):
    _seed_corp_codes(tmp_path)

    new_filing = _filing("20260812000001", "일반 공고")
    needs_review_filing = _filing("20260812000002", "신규시설투자등 결정")
    deferred_filing = _filing("20260812000003", "유상증자 결정")
    retry_exhausted_filing = _filing("20260812000004", "타법인주식및출자증권취득")
    _seed_filing_events(tmp_path, [new_filing, needs_review_filing, deferred_filing, retry_exhausted_filing])

    needs_review = CandidateSignal(
        id="cand-1", filing=needs_review_filing, matched_rules=["capex_or_facility_investment:facility_investment:신규시설투자"],
        confidence="Moderate", status=CandidateStatus.NEEDS_REVIEW, extraction_state=ExtractionState.EXTRACTED,
        translation_state=TranslationState.TRANSLATED, excerpt_original="신규시설투자등 관련 원문",
        title_translation=Translation(translated_text="New facility investment decision", provider="DeepL", source_lang="ko", target_lang="en", translated_at=_now_iso()),
        excerpt_translation=Translation(translated_text="New facility investment original text", provider="DeepL", source_lang="ko", target_lang="en", translated_at=_now_iso()),
        state_history=[StateTransition(status=CandidateStatus.NEEDS_REVIEW, at=_now_iso())],
    )
    deferred = CandidateSignal(
        id="cand-2", filing=deferred_filing, matched_rules=["financing:capital_raise_or_treasury_stock:유상증자"],
        confidence="Moderate", status=CandidateStatus.PROCESSING_DEFERRED,
        state_history=[StateTransition(status=CandidateStatus.PROCESSING_DEFERRED, at=_now_iso(), detail="Scan processing budget reached.")],
    )
    exhausted_attempts = [StateTransition(status=CandidateStatus.QUEUED_FOR_PROCESSING, at=_now_iso()) for _ in range(retry_policy.MAX_RETRY_ATTEMPTS)]
    retry_exhausted = CandidateSignal(
        id="cand-3", filing=retry_exhausted_filing, matched_rules=["equity_or_jv_investment:equity_stake_or_investment_decision:타법인주식및출자증권취득"],
        confidence="Moderate", status=CandidateStatus.RETRIEVAL_FAILED, state_history=exhausted_attempts,
    )
    candidate_store.save_candidates(tmp_path, {c.id: c for c in (needs_review, deferred, retry_exhausted)})

    settings = Settings(dart_api_key="dart-key", translation_api_key="deepl-key", cache_dir=tmp_path)
    with patch("src.ui.pages.radar_inbox.get_settings", return_value=settings):
        at = AppTest.from_file(str(_HARNESS), default_timeout=10)
        at.run()

    assert not at.exception
    all_text = " ".join(m.value for m in at.markdown)
    assert "New filing" in all_text
    assert "Needs review" in all_text
    assert "Processing deferred" in all_text
    assert "Retrieval failed" in all_text
    assert "New facility investment decision" in all_text  # English title translation
    assert "New facility investment original text" in all_text  # English excerpt translation
    assert "Machine translation" in all_text
    button_labels = {b.label for b in at.button}
    assert "Process now" in button_labels
    assert any("Retry limit reached" in label for label in button_labels)


def test_radar_inbox_shows_not_material_label_for_routine_ownership_candidate(tmp_path):
    _seed_corp_codes(tmp_path)
    ownership_filing = _filing("20260812000009", "주식등의대량보유상황보고서(일반)")
    _seed_filing_events(tmp_path, [ownership_filing])

    routine_candidate = CandidateSignal(
        id="cand-routine", filing=ownership_filing,
        matched_rules=["ownership_change:major_shareholder_change:대량보유상황보고서"],
        confidence="Moderate", status=CandidateStatus.NOT_MATERIAL, extraction_state=ExtractionState.EXTRACTED,
        excerpt_original="직전 보고서 1,000,000,000 19.69 이번 보고서 1,000,000,500 19.69",
        materiality_assessment="Not material · routine ownership update",
        state_history=[StateTransition(status=CandidateStatus.NOT_MATERIAL, at=_now_iso(), detail="Not material · routine ownership update")],
    )
    candidate_store.save_candidates(tmp_path, {routine_candidate.id: routine_candidate})

    settings = Settings(dart_api_key="dart-key", translation_api_key="deepl-key", cache_dir=tmp_path)
    with patch("src.ui.pages.radar_inbox.get_settings", return_value=settings):
        at = AppTest.from_file(str(_HARNESS), default_timeout=10)
        at.run()

    assert not at.exception
    all_text = " ".join(m.value for m in at.markdown)
    assert "Not material · routine ownership update" in all_text
    # Live/demo isolation: this page's own scope banner is present, and
    # nothing here claims a broader market-conviction/investment reading.
    assert "Live primary filings · Korea DART + SEC EDGAR pilots" in all_text
    assert "market conviction" not in all_text.lower()
    assert "investment confidence" not in all_text.lower()


def _seed_edgar_ciks(cache_dir) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "NVDA": {"cik": "0001045810", "company_name": "NVIDIA CORP", "source": "test", "retrieved_at": "2026-08-01T00:00:00+00:00"},
        "MU": {"cik": "0000723125", "company_name": "MICRON TECHNOLOGY INC", "source": "test", "retrieved_at": "2026-08-01T00:00:00+00:00"},
        "COHR": {"cik": "0000021510", "company_name": "COHERENT CORP", "source": "test", "retrieved_at": "2026-08-01T00:00:00+00:00"},
        "ROK": {"cik": "0001024478", "company_name": "ROCKWELL AUTOMATION INC", "source": "test", "retrieved_at": "2026-08-01T00:00:00+00:00"},
        "RKLB": {"cik": "0001819994", "company_name": "ROCKET LAB USA INC", "source": "test", "retrieved_at": "2026-08-01T00:00:00+00:00"},
    }
    (cache_dir / "edgar_ciks.json").write_text(json.dumps(payload))


def test_radar_inbox_edgar_only_configured_renders_edgar_candidates(tmp_path):
    _seed_edgar_ciks(tmp_path)

    edgar_filing = FilingEvent(
        rcept_no="0001045810-26-000001", corp_code="0001045810", corp_name="NVIDIA", stock_code="NVDA",
        report_nm="8-K filing", rcept_dt="2026-08-12", flr_nm="NVIDIA", pblntf_ty="8-K", theme_slug="ai-buildout",
        source_url="https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/",
        retrieved_at=_now_iso(), source_name="SEC EDGAR", original_language="English", primary_document="nvda-8k.htm",
    )
    payload = {
        "seen_keys": [f"SEC EDGAR:0001045810:{edgar_filing.rcept_no}"],
        "filing_events": [
            {
                "rcept_no": edgar_filing.rcept_no, "corp_code": edgar_filing.corp_code, "corp_name": edgar_filing.corp_name,
                "stock_code": edgar_filing.stock_code, "report_nm": edgar_filing.report_nm, "rcept_dt": edgar_filing.rcept_dt,
                "flr_nm": edgar_filing.flr_nm, "pblntf_ty": edgar_filing.pblntf_ty, "pblntf_detail_ty": "",
                "theme_slug": edgar_filing.theme_slug, "subtheme_slug": None, "source_url": edgar_filing.source_url,
                "retrieved_at": edgar_filing.retrieved_at, "source_name": edgar_filing.source_name,
                "original_language": edgar_filing.original_language, "is_demo": False,
                "primary_document": edgar_filing.primary_document,
            }
        ],
        "candidate_signals": [],
    }
    (tmp_path / "edgar_filing_events.json").write_text(json.dumps(payload))

    edgar_candidate = CandidateSignal(
        id="edgar-cand-0001045810-26-000001", filing=edgar_filing,
        matched_rules=["earnings_or_results:8-K item 2.02"], confidence="Moderate",
        status=CandidateStatus.NEEDS_REVIEW, extraction_state=ExtractionState.EXTRACTED,
        translation_state=TranslationState.NOT_REQUESTED, excerpt_original="Item 2.02 Results of Operations. Revenue increased.",
        state_history=[StateTransition(status=CandidateStatus.NEEDS_REVIEW, at=_now_iso())],
    )
    candidate_store.save_candidates(tmp_path, {edgar_candidate.id: edgar_candidate}, "edgar_candidates.json")

    settings = Settings(dart_api_key=None, translation_api_key=None, edgar_user_agent="EevaResearch test@example.com", cache_dir=tmp_path)
    with patch("src.ui.pages.radar_inbox.get_settings", return_value=settings):
        at = AppTest.from_file(str(_HARNESS), default_timeout=10)
        at.run()

    assert not at.exception
    all_text = " ".join(m.value for m in at.markdown)
    assert "SEC EDGAR" in all_text
    assert "NVIDIA" in all_text
    assert "Revenue increased" in all_text
    # No translation UI leaks in for an EDGAR (native-English) candidate.
    assert "Machine translation" not in all_text
    # DART is unconfigured here — its scope line must not render.
    assert "OpenDART / DART · Samsung" not in all_text
