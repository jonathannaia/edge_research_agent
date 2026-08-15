"""Tests for the live DART (Korea) provider. All network calls are mocked
— response shapes match DART's official API documentation
(opendart.fss.or.kr/guide), verified before live_dart.py was written."""
import io
import zipfile
from unittest.mock import patch

import pytest

from src.config.settings import Settings
from src.providers.dart_client import DartError
from src.providers.live_dart import (
    DartUnavailableError,
    LiveDartFilingsProvider,
    LiveDartFundamentalsProvider,
)

FAKE_LIST_RESPONSE = {
    "status": "000",
    "message": "정상",
    "list": [
        {
            "corp_name": "삼성전자",
            "corp_code": "00126380",
            "stock_code": "005930",
            "rcept_no": "20260814000123",
            "report_nm": "분기보고서",
            "rcept_dt": "20260814",
        }
    ],
}

FAKE_FINANCIALS_RESPONSE = {
    "status": "000",
    "message": "정상",
    "list": [
        {"sj_div": "IS", "account_nm": "매출액", "thstrm_amount": "80,000,000,000", "frmtrm_amount": "70,000,000,000"},
        {"sj_div": "IS", "account_nm": "매출총이익", "thstrm_amount": "20,000,000,000", "frmtrm_amount": "15,000,000,000"},
        {"sj_div": "IS", "account_nm": "영업이익", "thstrm_amount": "10,000,000,000", "frmtrm_amount": "8,000,000,000"},
        {"sj_div": "BS", "account_nm": "현금및현금성자산", "thstrm_amount": "5,000,000,000"},
        {"sj_div": "BS", "account_nm": "부채총계", "thstrm_amount": "30,000,000,000"},
    ],
}


def _fake_corp_code_zip() -> bytes:
    xml = (
        b'<result><list><corp_code>00126380</corp_code><corp_name>\xec\x82\xbc\xec\x84\xb1\xec\xa0\x84\xec\x9e\x90'
        b'</corp_name><corp_eng_name>SAMSUNG ELECTRONICS CO,.LTD</corp_eng_name>'
        b'<stock_code>005930</stock_code><modify_date>20260101</modify_date></list></result>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("CORPCODE.xml", xml)
    return buf.getvalue()


# --- dart_client: corp code lookup ---

def test_get_corp_code_parses_real_zip_shape(tmp_path, monkeypatch):
    from src.providers import dart_client
    monkeypatch.setattr(dart_client, "_CORP_CODE_CACHE", tmp_path / "dart_corp_codes.json")

    with patch("src.providers.dart_client._get", return_value=_fake_corp_code_zip()):
        corp_code = dart_client.get_corp_code("005930", "fake-key")

    assert corp_code == "00126380"


def test_get_corp_code_returns_none_for_unknown_stock(tmp_path, monkeypatch):
    from src.providers import dart_client
    monkeypatch.setattr(dart_client, "_CORP_CODE_CACHE", tmp_path / "dart_corp_codes.json")

    with patch("src.providers.dart_client._get", return_value=_fake_corp_code_zip()):
        assert dart_client.get_corp_code("999999", "fake-key") is None


def test_get_json_raises_on_dart_error_status():
    from src.providers import dart_client

    error_response = b'{"status": "013", "message": "\xec\xa1\xb0\xed\x9a\x8c\xeb\x90\x9c \xea\xb2\xb0\xea\xb3\xbc\xea\xb0\x80 \xec\x97\x86\xec\x8a\xb5\xeb\x8b\x88\xeb\x8b\xa4."}'
    with patch("src.providers.dart_client._get", return_value=error_response):
        with pytest.raises(DartError):
            dart_client.get_json("list.json", {"crtfc_key": "fake"})


# --- LiveDartFilingsProvider ---

def test_live_dart_filings_parses_real_shape(tmp_path, monkeypatch):
    from src.providers import dart_client
    monkeypatch.setattr(dart_client, "_CORP_CODE_CACHE", tmp_path / "dart_corp_codes.json")

    settings = Settings(dart_api_key="fake-key")
    provider = LiveDartFilingsProvider(settings)
    with patch("src.providers.live_dart.dart_client.get_corp_code", return_value="00126380"):
        with patch("src.providers.live_dart.dart_client.get_json", return_value=FAKE_LIST_RESPONSE):
            filings = provider.get_recent_filings("005930", limit=5)

    assert len(filings) == 1
    assert "20260814000123" in filings[0].url_or_identifier
    assert filings[0].is_mock is False


def test_live_dart_filings_raises_without_api_key():
    settings = Settings(dart_api_key="")
    provider = LiveDartFilingsProvider(settings)
    with pytest.raises(DartUnavailableError):
        provider.get_recent_filings("005930")


def test_live_dart_filings_passes_explicit_date_range(tmp_path, monkeypatch):
    """Regression test: DART's list.json defaults bgn_de/end_de to *today*
    when omitted, not "all time" — a real live run against Samsung
    Electronics returned "no data found" until this was fixed. Confirms
    both params are always sent."""
    from src.providers import dart_client
    monkeypatch.setattr(dart_client, "_CORP_CODE_CACHE", tmp_path / "dart_corp_codes.json")

    settings = Settings(dart_api_key="fake-key")
    provider = LiveDartFilingsProvider(settings)
    captured_params = {}

    def fake_get_json(path, params):
        captured_params.update(params)
        return FAKE_LIST_RESPONSE

    with patch("src.providers.live_dart.dart_client.get_corp_code", return_value="00126380"):
        with patch("src.providers.live_dart.dart_client.get_json", side_effect=fake_get_json):
            provider.get_recent_filings("005930")

    assert "bgn_de" in captured_params and captured_params["bgn_de"]
    assert "end_de" in captured_params and captured_params["end_de"]
    assert len(captured_params["bgn_de"]) == 8  # YYYYMMDD
    # Also explicit, not left to documented defaults — same class of bug as bgn_de/end_de.
    assert captured_params["sort"] == "date"
    assert captured_params["sort_mth"] == "desc"


def test_live_dart_filings_raises_when_ticker_not_found():
    settings = Settings(dart_api_key="fake-key")
    provider = LiveDartFilingsProvider(settings)
    with patch("src.providers.live_dart.dart_client.get_corp_code", return_value=None):
        with pytest.raises(DartUnavailableError):
            provider.get_recent_filings("NOTREAL")


# --- LiveDartFundamentalsProvider ---

def test_live_dart_fundamentals_computes_margins_from_korean_account_names():
    settings = Settings(dart_api_key="fake-key")
    provider = LiveDartFundamentalsProvider(settings)
    with patch("src.providers.live_dart.dart_client.get_corp_code", return_value="00126380"):
        with patch("src.providers.live_dart.dart_client.get_json", return_value=FAKE_FINANCIALS_RESPONSE):
            snapshot = provider.get_fundamentals("005930")

    assert snapshot.revenue == 80_000_000_000
    assert snapshot.revenue_yoy_growth == pytest.approx((80e9 - 70e9) / 70e9)
    assert snapshot.gross_margin == pytest.approx(20e9 / 80e9)
    assert snapshot.operating_margin == pytest.approx(10e9 / 80e9)
    assert snapshot.cash_and_equivalents == 5_000_000_000
    assert snapshot.total_debt == 30_000_000_000
    assert snapshot.is_mock is False


def test_live_dart_fundamentals_raises_when_no_revenue_row():
    settings = Settings(dart_api_key="fake-key")
    provider = LiveDartFundamentalsProvider(settings)
    empty_response = {"status": "000", "list": [{"sj_div": "BS", "account_nm": "자본총계", "thstrm_amount": "1"}]}
    with patch("src.providers.live_dart.dart_client.get_corp_code", return_value="00126380"):
        with patch("src.providers.live_dart.dart_client.get_json", return_value=empty_response):
            with pytest.raises(DartUnavailableError):
                provider.get_fundamentals("005930")


def test_live_dart_fundamentals_computes_growth_for_semi_annual_report():
    """Regression test using the exact row shape from a real live DART
    response (Samsung Electronics, semi-annual report): no "frmtrm_amount"
    key at all, only "frmtrm_q_amount" (same-quarter-last-year, the
    correct comparison) and "frmtrm_add_amount" (prior cumulative YTD — a
    different metric, must NOT be used). Using the wrong key previously
    made yoy_growth silently come back as 0.0% for every non-annual
    Korean filing."""
    settings = Settings(dart_api_key="fake-key")
    provider = LiveDartFundamentalsProvider(settings)
    real_semi_annual_response = {
        "status": "000",
        "list": [
            {
                "sj_div": "IS", "account_nm": "매출액",
                "thstrm_amount": "171499470000000",
                "thstrm_add_amount": "305372914000000",
                "frmtrm_q_amount": "74566317000000",
                "frmtrm_add_amount": "153706820000000",
            },
        ],
    }
    with patch("src.providers.live_dart.dart_client.get_corp_code", return_value="00126380"):
        with patch("src.providers.live_dart.dart_client.get_json", return_value=real_semi_annual_response):
            snapshot = provider.get_fundamentals("005930")

    assert snapshot.revenue == 171_499_470_000_000
    # Must compare against frmtrm_q_amount (74.57T), never frmtrm_add_amount (153.7T)
    expected_growth = (171_499_470_000_000 - 74_566_317_000_000) / 74_566_317_000_000
    assert snapshot.revenue_yoy_growth == pytest.approx(expected_growth)
    assert snapshot.revenue_yoy_growth > 1.0  # this real case is >100% YoY growth


def test_live_dart_fundamentals_falls_back_through_report_chain():
    """The first three report-code attempts return no data; the fourth
    (prior-year annual) succeeds — proves the fallback chain actually
    tries multiple reports rather than giving up after the first miss."""
    settings = Settings(dart_api_key="fake-key")
    provider = LiveDartFundamentalsProvider(settings)

    call_count = {"n": 0}

    def fake_get_json(path, params):
        call_count["n"] += 1
        if call_count["n"] < 4:
            return {"status": "000", "list": []}
        return FAKE_FINANCIALS_RESPONSE

    with patch("src.providers.live_dart.dart_client.get_corp_code", return_value="00126380"):
        with patch("src.providers.live_dart.dart_client.get_json", side_effect=fake_get_json):
            snapshot = provider.get_fundamentals("005930")

    assert call_count["n"] == 4
    assert snapshot.revenue == 80_000_000_000
