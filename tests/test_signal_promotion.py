"""Pure logic tests for src/logic/signal_promotion.py — no Streamlit
runtime, no I/O. Mirrors tests/test_analyst_view.py's fixture style since
both operate on the same CandidateSignal/FilingEvent shapes."""
from __future__ import annotations

from datetime import datetime, timezone

from src.logic.signal_promotion import candidate_to_signal, is_eligible_for_signal
from src.models.models import (
    CandidateSignal,
    CandidateStatus,
    Direction,
    ExtractionState,
    FilingEvent,
    Horizon,
    StateTransition,
    Strength,
    Translation,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _filing(**overrides) -> FilingEvent:
    defaults = dict(
        rcept_no="20260812000001", corp_code="00164779", corp_name="SK Hynix", stock_code="000660",
        report_nm="조회공시요구(풍문또는보도)에대한답변(미확정)", rcept_dt="20260812", flr_nm="SK 하이닉스",
        theme_slug="memory", source_url="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260812000001",
        retrieved_at=_now_iso(),
    )
    defaults.update(overrides)
    return FilingEvent(**defaults)


def _candidate(filing: FilingEvent, **overrides) -> CandidateSignal:
    defaults = dict(
        id="cand-1", filing=filing, matched_rules=["market_rumor_response:rumor_inquiry_or_response:풍문또는보도"],
        confidence="Moderate", status=CandidateStatus.NEEDS_REVIEW, extraction_state=ExtractionState.EXTRACTED,
        excerpt_original="한국거래소의조회공시요구에대한답변...",
        state_history=[StateTransition(status=CandidateStatus.NEEDS_REVIEW, at=_now_iso())],
    )
    defaults.update(overrides)
    return CandidateSignal(**defaults)


def test_is_eligible_for_signal_only_extracted_and_needs_review():
    filing = _filing()
    for status in (CandidateStatus.EXTRACTED, CandidateStatus.NEEDS_REVIEW):
        assert is_eligible_for_signal(_candidate(filing, status=status)) is True

    for status in (
        CandidateStatus.NEW_FILING_EVENT, CandidateStatus.CANDIDATE_DETECTED, CandidateStatus.QUEUED_FOR_PROCESSING,
        CandidateStatus.RETRIEVAL_IN_PROGRESS, CandidateStatus.EXTRACTION_PENDING, CandidateStatus.TRANSLATION_PENDING,
        CandidateStatus.TRANSLATED, CandidateStatus.PROCESSING_DEFERRED, CandidateStatus.PARSE_FAILED,
        CandidateStatus.RETRIEVAL_FAILED, CandidateStatus.TRANSLATION_UNAVAILABLE, CandidateStatus.PUBLISHED,
        CandidateStatus.DISMISSED, CandidateStatus.NOT_MATERIAL,
    ):
        assert is_eligible_for_signal(_candidate(filing, status=status)) is False


def test_candidate_to_signal_uses_fixed_deterministic_defaults():
    filing = _filing()
    candidate = _candidate(filing)
    signal = candidate_to_signal(candidate)

    assert signal.is_demo is False
    assert signal.direction == Direction.EMERGING
    assert signal.horizon == Horizon.MULTI_WEEK
    assert signal.contrary_evidence == "Not yet reviewed."
    assert signal.evidence_count == 1
    assert signal.id == "signal-cand-1"
    assert signal.theme_slug == "memory"
    assert signal.related_tickers == ["000660"]


def test_candidate_to_signal_dart_market_rumor_uses_exact_analyst_view_templates():
    filing = _filing(source_name="OpenDART / DART")
    candidate = _candidate(filing)
    signal = candidate_to_signal(candidate)

    assert signal.invalidation_criteria == (
        "This filing is a disclosure inquiry or response about reported information. "
        "It does not confirm that a transaction has occurred."
    )
    assert signal.validation_criteria == (
        "A formal company response or clarification; "
        "A subsequent filing that confirms or denies the reported matter; "
        "An amendment or related disclosure"
    )
    assert "matched keyword “풍문또는보도”" in signal.interpretation


def test_candidate_to_signal_unknown_category_uses_exact_fallback_templates():
    filing = _filing(source_name="OpenDART / DART")
    candidate = _candidate(filing, matched_rules=["capex_or_facility_investment:facility_investment:신규시설투자"])
    signal = candidate_to_signal(candidate)

    assert signal.invalidation_criteria == (
        "This filing type has no specific uncertainty template yet. "
        "Read the source excerpt directly before drawing conclusions."
    )
    assert signal.validation_criteria == "Review subsequent company filings or official statements related to this disclosure."


def test_candidate_to_signal_prefers_translated_title_but_falls_back_to_native():
    filing = _filing(report_nm="네이티브 제목")
    translated = _candidate(
        filing,
        title_translation=Translation(
            translated_text="Translated title", provider="DeepL", source_lang="ko", target_lang="en", translated_at=_now_iso(),
        ),
    )
    assert candidate_to_signal(translated).title == "Translated title"

    native_only = _candidate(filing, title_translation=None)
    assert candidate_to_signal(native_only).title == "네이티브 제목"


def test_candidate_to_signal_maps_confidence_to_strength():
    filing = _filing()
    assert candidate_to_signal(_candidate(filing, confidence="Low")).strength == Strength.WEAK
    assert candidate_to_signal(_candidate(filing, confidence="Moderate")).strength == Strength.MODERATE
    assert candidate_to_signal(_candidate(filing, confidence="High")).strength == Strength.STRONG


def test_candidate_to_signal_maps_issuer_source_url_and_excerpt_verbatim():
    filing = _filing(
        corp_name="Samsung Electronics", source_name="OpenDART / DART",
        source_url="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260812000001",
    )
    candidate = _candidate(filing, excerpt_original="원문 발췌 텍스트")
    signal = candidate_to_signal(candidate)

    assert signal.issuer == "Samsung Electronics"
    assert signal.source_name == "OpenDART / DART"
    assert signal.source_url == "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260812000001"
    assert signal.excerpt == "원문 발췌 텍스트"


def test_candidate_to_signal_excerpt_is_none_when_not_extracted():
    filing = _filing()
    candidate = _candidate(filing, excerpt_original=None)
    assert candidate_to_signal(candidate).excerpt is None


def test_candidate_to_signal_edgar_uses_direct_primary_document_url():
    filing = _filing(
        corp_code="0001045810", corp_name="NVIDIA", stock_code="NVDA", rcept_no="0001045810-26-000069",
        report_nm="8-K", source_name="SEC EDGAR", original_language="English",
        source_url="https://www.sec.gov/Archives/edgar/data/1045810/000104581026000069/",
        primary_document="nvda-20260817.htm",
    )
    candidate = _candidate(filing, matched_rules=["earnings_or_results:8-K item 2.02"], excerpt_original="Item 2.02 Results of Operations.")
    signal = candidate_to_signal(candidate)

    assert signal.source_url == "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000069/nvda-20260817.htm"


def test_candidate_to_signal_edgar_falls_back_to_accession_url_when_no_primary_document():
    filing = _filing(
        corp_code="0001045810", corp_name="NVIDIA", stock_code="NVDA", rcept_no="0001045810-26-000069",
        report_nm="8-K", source_name="SEC EDGAR", original_language="English",
        source_url="https://www.sec.gov/Archives/edgar/data/1045810/000104581026000069/",
        primary_document="",
    )
    candidate = _candidate(filing, matched_rules=["earnings_or_results:8-K item 2.02"])
    signal = candidate_to_signal(candidate)

    assert signal.source_url == "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000069/"


def test_candidate_to_signal_edgar_falls_back_when_source_url_has_unexpected_shape():
    """Defensive: never guess a URL join if source_url doesn't already
    have the expected trailing-slash directory shape."""
    filing = _filing(
        corp_code="0001045810", corp_name="NVIDIA", stock_code="NVDA", rcept_no="0001045810-26-000069",
        report_nm="8-K", source_name="SEC EDGAR", original_language="English",
        source_url="https://www.sec.gov/Archives/edgar/data/1045810/000104581026000069",  # no trailing slash
        primary_document="nvda-20260817.htm",
    )
    candidate = _candidate(filing, matched_rules=["earnings_or_results:8-K item 2.02"])
    signal = candidate_to_signal(candidate)

    assert signal.source_url == "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000069"


def test_candidate_to_signal_dart_and_edinet_source_url_unchanged():
    dart_filing = _filing(source_name="OpenDART / DART", source_url="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260812000001")
    assert candidate_to_signal(_candidate(dart_filing)).source_url == dart_filing.source_url

    edinet_filing = _filing(
        source_name="EDINET", source_url="https://api.edinet-fsa.go.jp/api/v2/documents/S100YTEST",
        original_language="Japanese",
    )
    edinet_candidate = _candidate(edinet_filing, matched_rules=["annual_securities_report:010:030000:120"])
    assert candidate_to_signal(edinet_candidate).source_url == edinet_filing.source_url


def test_candidate_to_signal_never_invents_amounts_or_counterparties():
    filing = _filing()
    signal = candidate_to_signal(_candidate(filing))
    combined = " ".join([
        signal.title, signal.interpretation, signal.contrary_evidence,
        signal.validation_criteria, signal.invalidation_criteria, signal.excerpt or "",
    ])
    assert "KRW" not in combined
    assert "China" not in combined
    assert "trillion" not in combined
