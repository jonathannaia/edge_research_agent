"""edinet_service — the EDINET pilot's wiring layer. Only
edinet_readiness and get_edinet_companies are tested here (pure config/
cache reads, no network); run_scan/process_candidate_now are thin
wrappers already exercised end-to-end via test_edinet_pipeline.py's
mocked-client tests. Gate 7 note: get_edinet_companies now returns the
five live-verified EDINET cohort entries (see tracked_companies.py) —
all pre-resolved (corp_code hardcoded, not runtime-resolved, per that
module's docstring), so unresolved_companies stays trivially empty
either way."""
from __future__ import annotations

from src.config.settings import Settings
from src.data_access.edinet import edinet_service


def _settings(cache_dir, subscription_key=None) -> Settings:
    return Settings(edinet_subscription_key=subscription_key, cache_dir=cache_dir)


def test_readiness_reports_missing_subscription_key(tmp_path):
    readiness = edinet_service.edinet_readiness(_settings(tmp_path))

    assert not readiness.subscription_key_configured
    assert not readiness.ready


def test_readiness_ready_when_key_present_and_cohort_already_resolved(tmp_path):
    # The five EDINET cohort entries are hardcoded/pre-resolved (Gate 7),
    # so unresolved_companies is empty and readiness is driven entirely
    # by the key — same readiness shape DART/EDGAR reach once their own
    # companies are resolved.
    readiness = edinet_service.edinet_readiness(_settings(tmp_path, subscription_key="test-key"))

    assert readiness.subscription_key_configured
    assert readiness.unresolved_companies == ()
    assert readiness.ready


def test_get_edinet_companies_returns_the_five_live_verified_cohort_entries(tmp_path):
    companies = edinet_service.get_edinet_companies(tmp_path)
    names = {c.name for c in companies}
    assert names == {
        "SoftBank Group Corp.", "Kioxia Holdings Corporation", "Furukawa Electric Co., Ltd.",
        "FANUC CORPORATION", "ispace, inc.",
    }
    assert all(c.corp_code is not None for c in companies)


def test_get_edinet_companies_is_unaffected_by_cache_dir_contents(tmp_path):
    # No EDINET resolver cache is consulted at runtime for this cohort —
    # cache_dir has no bearing on which companies come back.
    companies_a = edinet_service.get_edinet_companies(tmp_path)
    companies_b = edinet_service.get_edinet_companies(tmp_path / "does-not-exist")
    assert companies_a == companies_b


def test_readiness_never_raises_without_a_configured_key(tmp_path):
    # Never makes a network call and never reads/validates the real
    # credential value — only checks presence (see errors.py's
    # EdinetConfigError docstring and the Settings field's own docstring).
    readiness = edinet_service.edinet_readiness(_settings(tmp_path, subscription_key=""))
    assert not readiness.subscription_key_configured
