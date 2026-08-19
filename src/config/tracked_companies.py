"""Tracked-company registry for live radar sourcing (Korea DART + SEC
EDGAR pilots).

Deliberately separate from src/models/models.py's Ticker — a
TrackedCompany is a source-configuration record ("which real company do
we scan, from which source, resolved how"), not a research/thesis
record. Shared across both pilots via the same `krx_code`/`corp_code`
field slots (reused, not renamed, per the milestone-8 decision to keep
DART's field names completely unchanged — see design/DECISIONS.md):

    source == "OpenDART / DART": krx_code = 6-digit KRX stock code,
        corp_code = DART's internal 8-digit issuer code
    source == "SEC EDGAR": krx_code = ticker, corp_code = normalized
        10-digit SEC CIK

corp_code/cik are intentionally NOT hardcoded here for DART or EDGAR —
DART's internal corp_code and SEC's CIK both need resolving against each
source's own official bulk lookup, and guessing either from memory would
break the same verify-against-real-data discipline the rest of this app
follows. DART's corp_code is resolved via
src/data_access/dart/corp_code_resolver.py; SEC's CIK is resolved via
src/data_access/edgar/cik_resolver.py (which additionally cross-checks
the resolved CIK against real submissions metadata before accepting it —
see that module's own docstring). Both cache to data/cache/ (gitignored,
never committed) — this module only defines what's known without a live
call.

EDINET pilot (Gate 7) deliberately breaks that "never hardcode" pattern
for its five entries below, and only because each value was already
independently live-verified across two separate prior gates before this
one — not guessed, not carried forward from a single source:
`corp_code` (EDINET code) and `krx_code` (here holding EDINET's own
5-character source-native securities code, e.g. "99840" — NOT the bare
4-character TSE code, and NOT the same meaning `krx_code` carries for
DART/EDGAR) both came from the real EDINET code-list artifact (Gate 2,
2026-08-17); the SoftBank Group entry's exact identifiers were further
independently confirmed against a live EDINET document-list record
(Gate 6, docID S100YGH5). No EDINET resolver cache is consulted at
runtime for these five entries — they need none.
"""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class TrackedCompany:
    name: str
    exchange: str  # e.g. "KRX", "NASDAQ", "NYSE", "TSE"
    krx_code: str  # KRX stock code (DART), ticker (EDGAR), or 5-char EDINET securities code (EDINET) — see module docstring
    source: str  # "OpenDART / DART", "SEC EDGAR", or "EDINET"
    themes: tuple[str, ...]  # theme slugs (src/data_access side), primary first
    subthemes: tuple[str, ...] = ()
    active: bool = True
    notes: str = ""
    # Populated separately at runtime from each source's own resolver
    # cache — see module docstring — EXCEPT the five EDINET entries
    # below, which are hardcoded because they were already live-verified
    # (see module docstring). None means "not yet resolved."
    corp_code: str | None = None  # DART corp_code, SEC CIK (EDGAR), or EDINET code (EDINET)
    # Source-native legal name, preserved verbatim — distinct from `name`
    # (a curated display label, which may or may not itself be sourced
    # from the same place; see each EDINET entry's own `notes` for which
    # is which). Empty for DART/EDGAR, which have never needed this
    # distinction. Additive, default-preserving field (Gate 7) — no
    # existing entry or caller needed to change.
    native_name: str = ""


TRACKED_COMPANIES: tuple[TrackedCompany, ...] = (
    TrackedCompany(
        name="Samsung Electronics",
        exchange="KRX",
        krx_code="005930",
        source="OpenDART / DART",
        themes=("memory", "ai-buildout"),
        subthemes=("dram", "hbm", "compute-accelerators"),
        notes="Korea Memory / AI Buildout radar pilot cohort.",
    ),
    TrackedCompany(
        name="SK Hynix",
        exchange="KRX",
        krx_code="000660",
        source="OpenDART / DART",
        themes=("memory", "ai-buildout"),
        subthemes=("dram", "hbm"),
        notes="Korea Memory / AI Buildout radar pilot cohort.",
    ),
    # SEC EDGAR pilot cohort (milestone 8) — one company per theme,
    # approved by the user, bounded to exactly these five. `exchange`
    # here is a display label only (never used for any API call — CIK
    # resolution goes by ticker against SEC's own official mapping file),
    # based on current public listing knowledge, not independently
    # verified against a live source the way corp_code/CIK resolution is.
    TrackedCompany(
        name="NVIDIA",
        exchange="NASDAQ",
        krx_code="NVDA",
        source="SEC EDGAR",
        themes=("ai-buildout",),
        subthemes=("compute-accelerators",),
        notes="SEC EDGAR pilot cohort — AI Buildout.",
    ),
    TrackedCompany(
        name="Micron Technology",
        exchange="NASDAQ",
        krx_code="MU",
        source="SEC EDGAR",
        themes=("memory",),
        subthemes=("dram", "hbm"),
        notes="SEC EDGAR pilot cohort — Memory.",
    ),
    TrackedCompany(
        name="Coherent Corp",
        exchange="NYSE",
        krx_code="COHR",
        source="SEC EDGAR",
        themes=("photonics",),
        subthemes=("optical-components", "interconnect"),
        notes="SEC EDGAR pilot cohort — Photonics.",
    ),
    TrackedCompany(
        name="Rockwell Automation",
        exchange="NYSE",
        krx_code="ROK",
        source="SEC EDGAR",
        themes=("humanoids",),
        subthemes=("industrial-automation",),
        notes="SEC EDGAR pilot cohort — Humanoids / industrial automation.",
    ),
    TrackedCompany(
        name="Rocket Lab",
        exchange="NASDAQ",
        krx_code="RKLB",
        source="SEC EDGAR",
        themes=("space",),
        subthemes=("launch",),
        notes="SEC EDGAR pilot cohort — Space.",
    ),
    # Radar expansion, Phase 1 (registry-only) — three companies added
    # after a controlled, explicitly-approved live cik_resolver.py
    # validation (2026-08-19), not a hardcoded guess. corp_code is left
    # unset here, same as every other EDGAR entry above — the CIK is
    # already resolved into data/cache/edgar_ciks.json and will populate
    # automatically via with_resolved_ciks() the next time EDGAR
    # companies are loaded, exactly like NVIDIA/Micron/Coherent/Rockwell/
    # Rocket Lab already do.
    TrackedCompany(
        name="Advanced Micro Devices",
        exchange="NASDAQ",
        krx_code="AMD",
        source="SEC EDGAR",
        themes=("ai-buildout",),
        subthemes=("compute-accelerators",),
        notes=(
            "SEC EDGAR pilot cohort — AI Buildout. CIK verified via a "
            "controlled cik_resolver.resolve_and_cache() validation, "
            "2026-08-19 (ticker cross-checked against SEC's own "
            "submissions metadata; cached CIK 0000002488)."
        ),
    ),
    TrackedCompany(
        name="SanDisk Corp",
        exchange="NASDAQ",
        krx_code="SNDK",
        source="SEC EDGAR",
        themes=("memory",),
        notes=(
            "SEC EDGAR pilot cohort — Memory. CIK verified via a "
            "controlled cik_resolver.resolve_and_cache() validation, "
            "2026-08-19 (ticker cross-checked against SEC's own "
            "submissions metadata; cached CIK 0002023554)."
        ),
    ),
    TrackedCompany(
        name="Lumentum Holdings Inc.",
        exchange="NASDAQ",
        krx_code="LITE",
        source="SEC EDGAR",
        themes=("photonics",),
        notes=(
            "SEC EDGAR pilot cohort — Photonics. CIK verified via a "
            "controlled cik_resolver.resolve_and_cache() validation, "
            "2026-08-19 (ticker cross-checked against SEC's own "
            "submissions metadata; cached CIK 0001633978)."
        ),
    ),
    # Radar expansion, Phase 1 (registry-only), second batch — four
    # companies added after a controlled, explicitly-approved live
    # cik_resolver.py validation (2026-08-19). corp_code left unset,
    # same as every other EDGAR entry above — resolves automatically via
    # with_resolved_ciks() from the already-cached CIK.
    TrackedCompany(
        name="Intel Corp.",
        exchange="NASDAQ",
        krx_code="INTC",
        source="SEC EDGAR",
        themes=("ai-buildout",),
        subthemes=("compute-accelerators",),
        notes=(
            "SEC EDGAR pilot cohort — AI Buildout. CIK verified via a "
            "controlled cik_resolver.resolve_and_cache() validation, "
            "2026-08-19 (ticker cross-checked against SEC's own "
            "submissions metadata; cached CIK 0000050863)."
        ),
    ),
    TrackedCompany(
        name="Arm Holdings plc",
        exchange="NASDAQ",
        krx_code="ARM",
        source="SEC EDGAR",
        themes=("ai-buildout",),
        subthemes=("compute-accelerators",),
        notes=(
            "SEC EDGAR pilot cohort — AI Buildout. CIK verified via a "
            "controlled cik_resolver.resolve_and_cache() validation, "
            "2026-08-19 (ticker cross-checked against SEC's own "
            "submissions metadata; cached CIK 0001973239). SEC-registered "
            "as \"ARM HOLDINGS PLC /UK\" — a UK-domiciled foreign private "
            "issuer; cross-check passed against its real submissions "
            "metadata regardless."
        ),
    ),
    TrackedCompany(
        name="Applied Optoelectronics, Inc.",
        exchange="NASDAQ",
        krx_code="AAOI",
        source="SEC EDGAR",
        themes=("photonics",),
        notes=(
            "SEC EDGAR pilot cohort — Photonics. CIK verified via a "
            "controlled cik_resolver.resolve_and_cache() validation, "
            "2026-08-19 (ticker cross-checked against SEC's own "
            "submissions metadata; cached CIK 0001158114)."
        ),
    ),
    TrackedCompany(
        name="Corning Inc.",
        exchange="NYSE",
        krx_code="GLW",
        source="SEC EDGAR",
        themes=("photonics",),
        notes=(
            "SEC EDGAR pilot cohort — Photonics. CIK verified via a "
            "controlled cik_resolver.resolve_and_cache() validation, "
            "2026-08-19 (ticker cross-checked against SEC's own "
            "submissions metadata; cached CIK 0000024741)."
        ),
    ),
    # EDINET (Japan) pilot cohort (Gate 7) — one company per theme,
    # `krx_code`/`corp_code` hardcoded rather than left for runtime
    # resolution because both were already independently live-verified
    # (see module docstring). `name` is a curated English display label;
    # `native_name` is the exact Japanese legal name from the real
    # EDINET code-list artifact (Gate 2, 2026-08-17) — for four of the
    # five, `name` itself is ALSO that same code list's own English
    # filer-name field (real source evidence, not a curated guess); only
    # ispace's `name` is curated, since its code-list English-name field
    # was observed blank (confirmed live, Gate 2/Gate 6) — see its own
    # note below.
    TrackedCompany(
        name="SoftBank Group Corp.",
        native_name="ソフトバンクグループ株式会社",
        exchange="TSE",
        krx_code="99840",
        source="EDINET",
        themes=("ai-buildout",),
        corp_code="E02778",
        notes=(
            "EDINET pilot cohort — AI Buildout. `name` is the EDINET code "
            "list's own English filer name (Gate 2), not curated. "
            "corp_code/krx_code confirmed live twice: Gate 2 code-list "
            "resolution and Gate 6 document-list observation (docID S100YGH5)."
        ),
    ),
    TrackedCompany(
        name="Kioxia Holdings Corporation",
        native_name="キオクシアホールディングス株式会社",
        exchange="TSE",
        krx_code="285A0",
        source="EDINET",
        themes=("memory",),
        corp_code="E35948",
        notes=(
            "EDINET pilot cohort — Memory. `name` is the EDINET code "
            "list's own English filer name (Gate 2), not curated. "
            "corp_code/krx_code confirmed live via Gate 2 code-list resolution."
        ),
    ),
    TrackedCompany(
        name="Furukawa Electric Co., Ltd.",
        native_name="古河電気工業株式会社",
        exchange="TSE",
        krx_code="58010",
        source="EDINET",
        themes=("photonics",),
        corp_code="E01332",
        notes=(
            "EDINET pilot cohort — Photonics. `name` is the EDINET code "
            "list's own English filer name (Gate 2), not curated. "
            "corp_code/krx_code confirmed live via Gate 2 code-list resolution."
        ),
    ),
    TrackedCompany(
        name="FANUC CORPORATION",
        native_name="ファナック株式会社",
        exchange="TSE",
        krx_code="69540",
        source="EDINET",
        themes=("humanoids",),
        corp_code="E01946",
        notes=(
            "EDINET pilot cohort — Humanoids / industrial automation. `name` "
            "is the EDINET code list's own English filer name (Gate 2), not "
            "curated. corp_code/krx_code confirmed live via Gate 2 code-list "
            "resolution."
        ),
    ),
    TrackedCompany(
        name="ispace, inc.",
        native_name="株式会社ｉｓｐａｃｅ",
        exchange="TSE",
        krx_code="93480",
        source="EDINET",
        themes=("space",),
        corp_code="E37584",
        notes=(
            "EDINET pilot cohort — Space. Unlike the other four EDINET "
            "entries, `name` here is a CURATED display label, not sourced "
            "from the EDINET code list — that list's English-name field for "
            "this filer was observed blank (confirmed live, Gate 2/Gate 6); "
            "`native_name` (the Japanese legal name) IS real source "
            "evidence. corp_code/krx_code confirmed live via Gate 2 "
            "code-list resolution."
        ),
    ),
)


def get_tracked_companies(active_only: bool = True) -> tuple[TrackedCompany, ...]:
    if not active_only:
        return TRACKED_COMPANIES
    return tuple(c for c in TRACKED_COMPANIES if c.active)


def get_tracked_companies_for_source(source: str, active_only: bool = True) -> tuple[TrackedCompany, ...]:
    return tuple(c for c in get_tracked_companies(active_only) if c.source == source)


def with_resolved_corp_codes(
    companies: tuple[TrackedCompany, ...], resolved: dict[str, str],
) -> tuple[TrackedCompany, ...]:
    """Returns a new tuple with corp_code filled in from a
    {krx_code: corp_code} mapping (typically loaded from the on-disk
    resolver cache) — frozen dataclasses can't be mutated in place, so
    unresolved entries pass through unchanged rather than erroring."""
    return tuple(
        replace(c, corp_code=resolved[c.krx_code]) if c.krx_code in resolved else c
        for c in companies
    )


def with_resolved_ciks(
    companies: tuple[TrackedCompany, ...], resolved: dict[str, str],
) -> tuple[TrackedCompany, ...]:
    """SEC EDGAR equivalent of with_resolved_corp_codes — fills in
    `corp_code` (holding a CIK for EDGAR entries, see module docstring)
    from a {ticker: cik} mapping. Same reused-field-slot approach, same
    pass-through-unresolved behavior."""
    return tuple(
        replace(c, corp_code=resolved[c.krx_code]) if c.krx_code in resolved else c
        for c in companies
    )
