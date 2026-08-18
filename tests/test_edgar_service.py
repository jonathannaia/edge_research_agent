"""edgar_service — the SEC EDGAR pilot's wiring layer. Only
edgar_readiness and get_edgar_companies are tested here (pure config/
cache reads, no network); run_scan/process_candidate_now are thin
wrappers already exercised end-to-end via test_edgar_pipeline.py's
mocked-client tests."""
from __future__ import annotations

import json

from src.config.settings import Settings
from src.data_access.edgar import edgar_service


def _settings(cache_dir, user_agent=None) -> Settings:
    return Settings(edgar_user_agent=user_agent, cache_dir=cache_dir)


def _seed_ciks(cache_dir, tickers: list[str]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        t: {"cik": f"000{i}045810", "company_name": "Test Co", "source": "test", "retrieved_at": "2026-08-17T00:00:00+00:00"}
        for i, t in enumerate(tickers)
    }
    (cache_dir / "edgar_ciks.json").write_text(json.dumps(payload), encoding="utf-8")


def test_readiness_reports_missing_user_agent_and_unresolved_companies(tmp_path):
    readiness = edgar_service.edgar_readiness(_settings(tmp_path))

    assert not readiness.user_agent_configured
    assert set(readiness.unresolved_companies) == {"NVIDIA", "Micron Technology", "Coherent Corp", "Rockwell Automation", "Rocket Lab"}
    assert not readiness.ready


def test_readiness_ready_when_user_agent_present_and_all_companies_resolved(tmp_path):
    _seed_ciks(tmp_path, ["NVDA", "MU", "COHR", "ROK", "RKLB"])

    readiness = edgar_service.edgar_readiness(_settings(tmp_path, user_agent="EevaResearch test@example.com"))

    assert readiness.user_agent_configured
    assert readiness.unresolved_companies == ()
    assert readiness.ready


def test_readiness_flags_partially_resolved_companies(tmp_path):
    _seed_ciks(tmp_path, ["NVDA"])

    readiness = edgar_service.edgar_readiness(_settings(tmp_path, user_agent="EevaResearch test@example.com"))

    assert "NVIDIA" not in readiness.unresolved_companies
    assert "Micron Technology" in readiness.unresolved_companies
    assert not readiness.ready


def test_get_edgar_companies_fills_in_resolved_ciks(tmp_path):
    _seed_ciks(tmp_path, ["NVDA"])

    companies = edgar_service.get_edgar_companies(tmp_path)

    by_ticker = {c.krx_code: c for c in companies}
    assert by_ticker["NVDA"].corp_code == "0000045810"
    assert by_ticker["MU"].corp_code is None


def test_get_edgar_companies_only_returns_edgar_source_companies(tmp_path):
    companies = edgar_service.get_edgar_companies(tmp_path)
    names = {c.name for c in companies}
    assert names == {"NVIDIA", "Micron Technology", "Coherent Corp", "Rockwell Automation", "Rocket Lab"}
    assert "Samsung Electronics" not in names
