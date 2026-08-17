"""radar_service — the Radar Inbox wiring layer. Only radar_readiness and
get_radar_companies are tested here (pure config/cache reads, no
network); run_scan/process_candidate_now are thin wrappers already
exercised end-to-end via test_radar_pipeline.py's mocked-client tests."""
from __future__ import annotations

import json

from src.config.settings import Settings
from src.data_access.dart import radar_service


def _settings(cache_dir, dart_key=None, translation_key=None) -> Settings:
    return Settings(dart_api_key=dart_key, translation_api_key=translation_key, cache_dir=cache_dir)


def _seed_corp_codes(cache_dir, krx_codes: list[str]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        krx: {"corp_code": f"corp-{krx}", "corp_name": "Test Co", "source": "OpenDART corpCode.xml", "retrieved_at": "2026-08-10T00:00:00+00:00"}
        for krx in krx_codes
    }
    (cache_dir / "dart_corp_codes.json").write_text(json.dumps(payload))


def test_readiness_reports_missing_keys_and_unresolved_companies(tmp_path):
    readiness = radar_service.radar_readiness(_settings(tmp_path))

    assert not readiness.dart_key_configured
    assert not readiness.translation_key_configured
    assert set(readiness.unresolved_companies) == {"Samsung Electronics", "SK Hynix"}
    assert not readiness.ready


def test_readiness_ready_when_keys_present_and_all_companies_resolved(tmp_path):
    _seed_corp_codes(tmp_path, ["005930", "000660"])

    readiness = radar_service.radar_readiness(_settings(tmp_path, dart_key="dart-key", translation_key="deepl-key"))

    assert readiness.dart_key_configured
    assert readiness.translation_key_configured
    assert readiness.unresolved_companies == ()
    assert readiness.ready


def test_readiness_flags_partially_resolved_companies(tmp_path):
    _seed_corp_codes(tmp_path, ["005930"])  # SK Hynix (000660) left unresolved

    readiness = radar_service.radar_readiness(_settings(tmp_path, dart_key="dart-key", translation_key="deepl-key"))

    assert readiness.unresolved_companies == ("SK Hynix",)
    assert not readiness.ready


def test_get_radar_companies_fills_in_resolved_corp_codes(tmp_path):
    _seed_corp_codes(tmp_path, ["005930", "000660"])

    companies = radar_service.get_radar_companies(tmp_path)

    by_krx = {c.krx_code: c for c in companies}
    assert by_krx["005930"].corp_code == "corp-005930"
    assert by_krx["000660"].corp_code == "corp-000660"


def test_get_radar_companies_leaves_unresolved_companies_with_none_corp_code(tmp_path):
    companies = radar_service.get_radar_companies(tmp_path)
    assert all(c.corp_code is None for c in companies)
