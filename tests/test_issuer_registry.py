"""Issuer Registry — Phase A (design/ISSUER_REGISTRY_FOUNDATION.md).

Covers the eight invariants the Phase A approval required: lossless
seed-issuer coverage, compatibility-adapter equivalence, identifier/source
fidelity, stub exclusion from the compatibility path, unique issuer IDs,
ontology validity, and known-conflict metadata. (The eighth — "existing
EDGAR/DART/EDINET/review-actions/Signal-eligibility tests still pass
unchanged" — is a full-suite run, not a test in this file; see the Phase A
final report.)"""
from src.config.issuer_registry import (
    DISCOVERY_STUBS,
    SEED_ISSUERS,
    get_all_issuers,
    tracked_companies_from_issuer_registry,
)
from src.config.ontology import KNOWN_CATEGORY_CONFLICTS, is_valid_layer, is_valid_theme
from src.config.tracked_companies import get_tracked_companies
from src.models.issuer import CoverageState


# --- 1. Every existing TrackedCompany record has a corresponding active seed issuer ---

def test_every_tracked_company_has_a_corresponding_seed_issuer():
    tracked = get_tracked_companies(active_only=False)
    seed_by_key = {(i.primary_exchange, i.primary_ticker): i for i in SEED_ISSUERS}
    assert len(tracked) == len(SEED_ISSUERS)
    for tc in tracked:
        issuer = seed_by_key.get((tc.exchange, tc.krx_code))
        assert issuer is not None, f"no seed issuer for {tc.name} ({tc.source}/{tc.krx_code})"
        assert issuer.legal_name == tc.name
        assert issuer.coverage_state == (CoverageState.SEED if tc.active else CoverageState.REJECTED)


def test_seed_issuer_count_matches_current_tracked_companies_registry():
    # Not hardcoded to a specific number here — see the Phase A final
    # report for today's actual count and how it compares to the
    # approval message's assumed count.
    assert len(SEED_ISSUERS) == len(get_tracked_companies(active_only=False))


# --- 2. Compatibility adapter produces an equivalent tracked-company universe ---

def test_compatibility_adapter_equals_existing_registry_active_only():
    assert tracked_companies_from_issuer_registry(active_only=True) == get_tracked_companies(active_only=True)


def test_compatibility_adapter_equals_existing_registry_including_inactive():
    assert (
        tracked_companies_from_issuer_registry(active_only=False)
        == get_tracked_companies(active_only=False)
    )


# --- 3. Existing source identifiers and source assignments survive migration exactly ---

def test_edinet_identifiers_survive_migration_exactly():
    edinet_issuers = {i.legal_name: i for i in SEED_ISSUERS if "EDINET" in i.identifiers}
    assert edinet_issuers["SoftBank Group Corp."].identifiers["EDINET"] == "E02778"
    assert edinet_issuers["Kioxia Holdings Corporation"].identifiers["EDINET"] == "E35948"
    assert edinet_issuers["Furukawa Electric Co., Ltd."].identifiers["EDINET"] == "E01332"
    assert edinet_issuers["FANUC CORPORATION"].identifiers["EDINET"] == "E01946"
    assert edinet_issuers["ispace, inc."].identifiers["EDINET"] == "E37584"
    assert len(edinet_issuers) == 5


def test_dart_and_edgar_seed_issuers_have_no_invented_identifiers():
    # corp_code/CIK is None on every DART/EDGAR TrackedCompany entry today
    # (resolved lazily at runtime) — the migration must not invent one.
    for issuer in SEED_ISSUERS:
        if "EDINET" not in issuer.identifiers:
            assert issuer.identifiers == {}


def test_seed_issuer_source_assignment_matches_issuer_id_prefix():
    by_ticker = {(tc.source, tc.krx_code) for tc in get_tracked_companies(active_only=False)}
    for issuer in SEED_ISSUERS:
        prefix, ticker = issuer.issuer_id.split(":", 1)
        source = {"dart": "OpenDART / DART", "edgar": "SEC EDGAR", "edinet": "EDINET"}[prefix]
        assert (source, ticker) in by_ticker


def test_seed_issuer_themes_and_subthemes_survive_migration_exactly():
    tracked_by_key = {(tc.source, tc.krx_code): tc for tc in get_tracked_companies(active_only=False)}
    for issuer in SEED_ISSUERS:
        source = {"dart": "OpenDART / DART", "edgar": "SEC EDGAR", "edinet": "EDINET"}[
            issuer.issuer_id.split(":", 1)[0]
        ]
        tc = tracked_by_key[(source, issuer.primary_ticker)]
        assert issuer.themes == tc.themes
        assert issuer.subthemes == tc.subthemes


# --- 4. Unverified discovery stubs cannot appear in the compatibility output ---

def test_discovery_stubs_never_appear_in_compatibility_output():
    stub_tickers = {i.primary_ticker for i in DISCOVERY_STUBS}
    compat_tickers = {c.krx_code for c in tracked_companies_from_issuer_registry(active_only=False)}
    assert stub_tickers.isdisjoint(compat_tickers)


def test_discovery_stubs_are_all_coverage_state_discovered():
    for issuer in DISCOVERY_STUBS:
        assert issuer.coverage_state == CoverageState.DISCOVERED


def test_discovery_stubs_have_no_identifiers():
    for issuer in DISCOVERY_STUBS:
        assert issuer.identifiers == {}, f"{issuer.issuer_id} must not carry an invented identifier"


def test_discovery_stubs_all_have_a_non_empty_normalization_status():
    for issuer in DISCOVERY_STUBS:
        assert issuer.normalization_status.strip() != ""


def test_get_tracked_companies_for_source_is_untouched_by_discovery_stubs():
    # tracked_companies.py itself imports nothing from this module — this
    # test exists to make that invariant explicit and regression-checked,
    # not because there's any code path that could plausibly break it.
    from src.config.tracked_companies import get_tracked_companies_for_source

    for source in ("OpenDART / DART", "SEC EDGAR", "EDINET"):
        names = {c.name for c in get_tracked_companies_for_source(source)}
        stub_names = {i.legal_name for i in DISCOVERY_STUBS}
        assert names.isdisjoint(stub_names)


# --- 5. No duplicate stable issuer IDs ---

def test_no_duplicate_issuer_ids_across_seed_and_stubs():
    all_ids = [issuer.issuer_id for issuer in get_all_issuers()]
    assert len(all_ids) == len(set(all_ids))


def test_seed_and_stub_issuer_id_namespaces_never_collide():
    seed_ids = {i.issuer_id for i in SEED_ISSUERS}
    stub_ids = {i.issuer_id for i in DISCOVERY_STUBS}
    assert seed_ids.isdisjoint(stub_ids)
    assert all(i.startswith("stub:") for i in stub_ids)
    assert all(i.startswith(("dart:", "edgar:", "edinet:")) for i in seed_ids)


# --- 6. Every registered theme/layer value is valid per the new ontology ---

def test_every_seed_issuer_theme_is_a_valid_primary_theme():
    for issuer in SEED_ISSUERS:
        for theme in issuer.themes:
            assert is_valid_theme(theme), f"{issuer.issuer_id} has invalid theme {theme!r}"


def test_every_stub_issuer_theme_and_layer_is_valid():
    for issuer in DISCOVERY_STUBS:
        for theme in issuer.themes:
            assert is_valid_theme(theme), f"{issuer.issuer_id} has invalid theme {theme!r}"
        for layer in issuer.supply_chain_layers:
            assert is_valid_layer(layer), f"{issuer.issuer_id} has invalid layer {layer!r}"
        assert len(issuer.supply_chain_layers) >= 1  # every stub carries its seed-list category as a layer


# --- 7. Known category conflicts are explicit unresolved metadata ---

def test_known_category_conflicts_cover_the_four_required_items():
    subjects = " ".join(c.subject for c in KNOWN_CATEGORY_CONFLICTS)
    assert "MRVL" in subjects
    assert "TSEM" in subjects
    assert "networking-interconnect" in subjects or "interconnect-switching" in subjects
    assert "Kioxia" in subjects and "285A" in subjects


def test_known_category_conflicts_are_all_marked_unresolved():
    for conflict in KNOWN_CATEGORY_CONFLICTS:
        assert conflict.status.startswith("Unresolved")


def test_mrvl_and_tsem_registry_themes_are_unchanged_by_ontology_module():
    # The conflict is documented, not silently fixed — MRVL/TSEM keep
    # their existing tracked_companies.py themes exactly.
    by_ticker = {i.primary_ticker: i for i in SEED_ISSUERS}
    assert by_ticker["MRVL"].themes == ("photonics",)
    assert by_ticker["TSEM"].themes == ("ai-buildout",)
