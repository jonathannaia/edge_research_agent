"""Tracked-company registry (Korea DART + SEC EDGAR + EDINET pilots) —
presence, correct identifiers/theme mapping, source filtering, and the
corp_code/CIK-merge helpers."""
from src.config.tracked_companies import (
    TrackedCompany,
    get_tracked_companies,
    get_tracked_companies_for_source,
    with_resolved_ciks,
    with_resolved_corp_codes,
)


def test_registry_contains_all_three_pilot_cohorts():
    companies = get_tracked_companies()
    names = {c.name for c in companies}
    assert names == {
        "Samsung Electronics", "SK Hynix",
        "NVIDIA", "Micron Technology", "Coherent Corp", "Rockwell Automation", "Rocket Lab",
        "SoftBank Group Corp.", "Kioxia Holdings Corporation", "Furukawa Electric Co., Ltd.",
        "FANUC CORPORATION", "ispace, inc.",
    }


def test_get_tracked_companies_for_source_filters_dart_only():
    dart_companies = get_tracked_companies_for_source("OpenDART / DART")
    names = {c.name for c in dart_companies}
    assert names == {"Samsung Electronics", "SK Hynix"}


def test_get_tracked_companies_for_source_filters_edgar_only():
    edgar_companies = get_tracked_companies_for_source("SEC EDGAR")
    names = {c.name for c in edgar_companies}
    assert names == {"NVIDIA", "Micron Technology", "Coherent Corp", "Rockwell Automation", "Rocket Lab"}


def test_edgar_cohort_identifiers_and_theme_mapping():
    companies = {c.name: c for c in get_tracked_companies_for_source("SEC EDGAR")}
    assert companies["NVIDIA"].krx_code == "NVDA"
    assert companies["NVIDIA"].themes[0] == "ai-buildout"
    assert companies["Micron Technology"].krx_code == "MU"
    assert companies["Micron Technology"].themes[0] == "memory"
    assert companies["Coherent Corp"].krx_code == "COHR"
    assert companies["Coherent Corp"].themes[0] == "photonics"
    assert companies["Rockwell Automation"].krx_code == "ROK"
    assert companies["Rockwell Automation"].themes[0] == "humanoids"
    assert companies["Rocket Lab"].krx_code == "RKLB"
    assert companies["Rocket Lab"].themes[0] == "space"
    for c in companies.values():
        assert c.corp_code is None  # never hardcoded — resolved separately (CIK)


def test_with_resolved_ciks_fills_in_matching_tickers_only():
    companies = get_tracked_companies_for_source("SEC EDGAR")
    resolved = with_resolved_ciks(companies, {"NVDA": "0001045810"})

    by_name = {c.name: c for c in resolved}
    assert by_name["NVIDIA"].corp_code == "0001045810"
    assert by_name["Micron Technology"].corp_code is None


def test_samsung_identifiers_and_theme_mapping():
    companies = {c.name: c for c in get_tracked_companies()}
    samsung = companies["Samsung Electronics"]
    assert samsung.exchange == "KRX"
    assert samsung.krx_code == "005930"
    assert samsung.source == "OpenDART / DART"
    assert samsung.themes[0] == "memory"
    assert "ai-buildout" in samsung.themes
    assert samsung.corp_code is None  # never hardcoded — resolved separately


def test_sk_hynix_identifiers_and_theme_mapping():
    companies = {c.name: c for c in get_tracked_companies()}
    hynix = companies["SK Hynix"]
    assert hynix.krx_code == "000660"
    assert hynix.themes[0] == "memory"
    assert hynix.corp_code is None


def test_get_tracked_companies_active_only_excludes_inactive():
    inactive = TrackedCompany(
        name="Inactive Co", exchange="KRX", krx_code="999999",
        source="OpenDART / DART", themes=("memory",), active=False,
    )
    all_companies = get_tracked_companies(active_only=False) + (inactive,)
    active_names = {c.name for c in all_companies if c.active}
    assert "Inactive Co" not in active_names


def test_with_resolved_corp_codes_fills_in_matching_krx_codes_only():
    companies = get_tracked_companies()
    resolved = with_resolved_corp_codes(companies, {"005930": "00126380"})

    by_name = {c.name: c for c in resolved}
    assert by_name["Samsung Electronics"].corp_code == "00126380"
    assert by_name["SK Hynix"].corp_code is None  # not in the mapping — passes through unresolved


def test_with_resolved_corp_codes_does_not_mutate_originals():
    # DART/EDGAR entries start at None; EDINET entries start already
    # hardcoded (Gate 7) — the invariant this test checks is "no
    # original value changed," not "every value is None."
    companies = get_tracked_companies()
    original_corp_codes = {c.name: c.corp_code for c in companies}
    with_resolved_corp_codes(companies, {"005930": "00126380"})
    assert {c.name: c.corp_code for c in companies} == original_corp_codes


# --- EDINET pilot cohort (Gate 7) ---

def test_get_tracked_companies_for_source_filters_edinet_only():
    edinet_companies = get_tracked_companies_for_source("EDINET")
    names = {c.name for c in edinet_companies}
    assert names == {
        "SoftBank Group Corp.", "Kioxia Holdings Corporation", "Furukawa Electric Co., Ltd.",
        "FANUC CORPORATION", "ispace, inc.",
    }


def test_edinet_cohort_has_exactly_five_entries():
    assert len(get_tracked_companies_for_source("EDINET")) == 5


def test_edinet_cohort_direct_edinet_code_mapping():
    companies = {c.name: c for c in get_tracked_companies_for_source("EDINET")}
    assert companies["SoftBank Group Corp."].corp_code == "E02778"
    assert companies["Kioxia Holdings Corporation"].corp_code == "E35948"
    assert companies["Furukawa Electric Co., Ltd."].corp_code == "E01332"
    assert companies["FANUC CORPORATION"].corp_code == "E01946"
    assert companies["ispace, inc."].corp_code == "E37584"


def test_edinet_cohort_preserves_source_native_five_character_securities_codes():
    companies = {c.name: c for c in get_tracked_companies_for_source("EDINET")}
    # Real EDINET securities codes are 5 characters (4-char TSE code +
    # trailing "0", confirmed live Gate 2) — never the bare 4-char code.
    assert companies["SoftBank Group Corp."].krx_code == "99840"
    assert companies["Kioxia Holdings Corporation"].krx_code == "285A0"  # alphanumeric preserved exactly
    assert companies["Furukawa Electric Co., Ltd."].krx_code == "58010"
    assert companies["FANUC CORPORATION"].krx_code == "69540"
    assert companies["ispace, inc."].krx_code == "93480"
    for c in companies.values():
        assert len(c.krx_code) == 5


def test_edinet_cohort_theme_mapping():
    companies = {c.name: c for c in get_tracked_companies_for_source("EDINET")}
    assert companies["SoftBank Group Corp."].themes[0] == "ai-buildout"
    assert companies["Kioxia Holdings Corporation"].themes[0] == "memory"
    assert companies["Furukawa Electric Co., Ltd."].themes[0] == "photonics"
    assert companies["FANUC CORPORATION"].themes[0] == "humanoids"
    assert companies["ispace, inc."].themes[0] == "space"
    for c in companies.values():
        assert c.subthemes == ()  # no secondary themes added, per Gate 7 scope


def test_edinet_cohort_preserves_japanese_legal_names_exactly():
    companies = {c.name: c for c in get_tracked_companies_for_source("EDINET")}
    assert companies["SoftBank Group Corp."].native_name == "ソフトバンクグループ株式会社"
    assert companies["Kioxia Holdings Corporation"].native_name == "キオクシアホールディングス株式会社"
    assert companies["Furukawa Electric Co., Ltd."].native_name == "古河電気工業株式会社"
    assert companies["FANUC CORPORATION"].native_name == "ファナック株式会社"
    assert companies["ispace, inc."].native_name == "株式会社ｉｓｐａｃｅ"


def test_edinet_cohort_corp_code_is_hardcoded_not_none():
    # Unlike DART/EDGAR (never hardcoded, always runtime-resolved), the
    # EDINET cohort's identifiers were already independently live-verified
    # (Gate 2/Gate 6) — see tracked_companies.py's own module docstring.
    for c in get_tracked_companies_for_source("EDINET"):
        assert c.corp_code is not None


def test_ispace_english_name_is_curated_not_claimed_as_source_evidence():
    # The real EDINET code list's English-name field for ispace was
    # observed blank (Gate 2/Gate 6) — `name` here must not be presented
    # as if it came from that source; only `native_name` is source
    # evidence for this entry.
    ispace = next(c for c in get_tracked_companies_for_source("EDINET") if c.corp_code == "E37584")
    assert ispace.name == "ispace, inc."
    assert "curated" in ispace.notes.lower()
    assert ispace.native_name == "株式会社ｉｓｐａｃｅ"


def test_edinet_cohort_exchange_is_tse():
    for c in get_tracked_companies_for_source("EDINET"):
        assert c.exchange == "TSE"


def test_native_name_defaults_to_empty_for_non_edinet_entries():
    for c in get_tracked_companies_for_source("SEC EDGAR") + get_tracked_companies_for_source("OpenDART / DART"):
        assert c.native_name == ""
