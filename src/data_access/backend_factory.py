"""Durable-State Phase 2A — the one composition seam that decides
JSON-backed vs. SQLite-backed collaborators, based on `Settings.db_backend`.
No source service (a pipeline, a resolver, a UI page) imports `sqlite3`
or picks its own storage here — this module is the single place that
does, matching the existing `container.py` composition-root pattern
exactly (its own docstring: "Phase 2 swaps in real implementations here
only, without touching any page or component code").

**Only `get_signal_repository()` is actually wired into the running
app** (via `container.py`'s `get_repositories()`) — it's the one place
in the whole codebase that already has a real interface seam
(`SignalRepository`, already implemented by both `RadarSignalRepository`
and Phase 1's `SqliteSignalRepository`). `get_candidate_repository()`,
`get_filing_event_repository()`, and `get_identifier_repository()` below
exist and are fully tested for cross-backend behavioral equivalence, but
have **no real application call site yet** — every existing pipeline
(`edgar_pipeline.py`, `radar_pipeline.py`, `edinet_pipeline.py`,
`radar_inbox.py`, `review_actions.py`, `cik_resolver.py`,
`corp_code_resolver.py`) still calls `candidate_store.py`/
`scan_service.py`/the resolver caches directly — rewiring those call
sites would mean touching source-adapter/business-rule files, which is
explicitly out of this phase's scope. See design/DECISIONS.md's
"smallest viable wiring seam" note for the full inspection this was
based on.

"json" (the default, whenever `EDGE_DB_BACKEND` is unset/blank/
unrecognized) always returns exactly today's existing collaborators,
completely unchanged. "sqlite" requires an explicit, non-empty
`EDGE_STATE_DB_PATH` — selecting sqlite without one raises
`BackendConfigurationError` rather than silently falling back to JSON.
`EDGE_STATE_DB_URL` is never read, parsed, or connected to here."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from src.config.settings import Settings
from src.data_access.dart import candidate_store
from src.data_access.dart import corp_code_resolver
from src.data_access.dart import scan_service as dart_scan_service
from src.data_access.edgar import cik_resolver
from src.data_access.edgar import edgar_pipeline
from src.data_access.edgar import scan_service as edgar_scan_service
from src.data_access.edinet import edinet_pipeline
from src.data_access.edinet import scan_service as edinet_scan_service
from src.data_access.interfaces import SignalRepository
from src.data_access.live.radar_signal_repository import RadarSignalRepository
from src.data_access.state_db import candidate_repository as sqlite_candidates
from src.data_access.state_db import connection as state_db_connection
from src.data_access.state_db import filing_event_repository as sqlite_filing_events
from src.data_access.state_db import identifier_repository as sqlite_identifiers
from src.data_access.state_db import schema as state_db_schema
from src.data_access.state_db.identifier_repository import ResolvedIdentifierRecord
from src.data_access.state_db.signal_repository import SqliteSignalRepository
from src.models.models import CandidateSignal, FilingEvent

_CANDIDATE_FILENAME_BY_SOURCE = {
    "OpenDART / DART": "dart_candidates.json",
    "SEC EDGAR": edgar_pipeline.CANDIDATE_STORE_FILENAME,
    "EDINET": edinet_pipeline.CANDIDATE_STORE_FILENAME,
}
_FILING_EVENTS_LOADER_BY_SOURCE = {
    "OpenDART / DART": dart_scan_service.load_filing_events,
    "SEC EDGAR": edgar_scan_service.load_filing_events,
    "EDINET": edinet_scan_service.load_filing_events,
}


class BackendConfigurationError(Exception):
    """Raised when db_backend="sqlite" is explicitly selected but the
    configuration needed to use it is missing or invalid — never a
    silent fallback to JSON. Raised before any database is opened."""


def _normalized_backend(settings: Settings) -> str:
    return (settings.db_backend or "json").strip().lower()


def _require_sqlite_connection(settings: Settings) -> sqlite3.Connection:
    path_value = settings.state_db_path
    if not path_value or not str(path_value).strip():
        raise BackendConfigurationError(
            "EDGE_DB_BACKEND=sqlite requires an explicit, non-empty EDGE_STATE_DB_PATH — "
            "none was configured. Refusing to silently use the JSON backend instead."
        )
    conn = state_db_connection.connect(Path(path_value))
    state_db_schema.migrate(conn)
    return conn


# --- Signal repository — the one factory actually wired into container.py ---

def get_signal_repository(settings: Settings) -> SignalRepository:
    backend = _normalized_backend(settings)
    if backend == "sqlite":
        return SqliteSignalRepository(_require_sqlite_connection(settings))
    return RadarSignalRepository(settings)


# --- Candidate repository — factory exists and is tested; not yet wired into any pipeline ---

@dataclass(frozen=True)
class UpdateOutcome:
    status: str  # "updated" | "conflict" | "not_found" — see each adapter's own docstring
    current: CandidateSignal | None


class CandidateRepositoryProtocol(Protocol):
    def load_candidates(self) -> dict[str, CandidateSignal]: ...
    def get_candidate(self, candidate_id: str) -> CandidateSignal | None: ...
    def upsert_new_candidates(self, new_candidates: list[CandidateSignal]) -> dict[str, CandidateSignal]: ...
    def update_candidate(self, candidate: CandidateSignal, expected_version: int | None = None) -> UpdateOutcome: ...


@dataclass(frozen=True)
class JsonCandidateRepository:
    """Wraps candidate_store.py exactly as-is — no new write path, no
    format change. update_candidate() always succeeds (JSON has no
    optimistic-concurrency concept — see candidate_store.update_candidate's
    own docstring on why that's an accepted, documented pilot-scale
    assumption); `expected_version` is accepted for Protocol compatibility
    and ignored, matching that real behavior honestly rather than faking
    a lock JSON doesn't have."""

    cache_dir: Path
    filename: str

    def load_candidates(self) -> dict[str, CandidateSignal]:
        return candidate_store.load_candidates(self.cache_dir, self.filename)

    def get_candidate(self, candidate_id: str) -> CandidateSignal | None:
        return self.load_candidates().get(candidate_id)

    def upsert_new_candidates(self, new_candidates: list[CandidateSignal]) -> dict[str, CandidateSignal]:
        return candidate_store.upsert_new_candidates(self.cache_dir, new_candidates, self.filename)

    def update_candidate(self, candidate: CandidateSignal, expected_version: int | None = None) -> UpdateOutcome:
        candidate_store.update_candidate(self.cache_dir, candidate, self.filename)
        return UpdateOutcome(status="updated", current=candidate)


@dataclass(frozen=True)
class SqliteCandidateRepository:
    conn: sqlite3.Connection
    source: str

    def load_candidates(self) -> dict[str, CandidateSignal]:
        return sqlite_candidates.load_candidates(self.conn, self.source)

    def get_candidate(self, candidate_id: str) -> CandidateSignal | None:
        return sqlite_candidates.get_candidate(self.conn, candidate_id)

    def upsert_new_candidates(self, new_candidates: list[CandidateSignal]) -> dict[str, CandidateSignal]:
        return sqlite_candidates.upsert_new_candidates(self.conn, self.source, new_candidates)

    def update_candidate(self, candidate: CandidateSignal, expected_version: int | None = None) -> UpdateOutcome:
        if expected_version is None:
            expected_version = sqlite_candidates.get_candidate_version(self.conn, candidate.id) or 1
        outcome = sqlite_candidates.update_candidate(self.conn, candidate, expected_version)
        return UpdateOutcome(status=outcome.status, current=outcome.current)


def get_candidate_repository(settings: Settings, source: str) -> CandidateRepositoryProtocol:
    """`source` is one of "OpenDART / DART" / "SEC EDGAR" / "EDINET" —
    the same source_name strings used throughout this codebase."""
    backend = _normalized_backend(settings)
    if backend == "sqlite":
        return SqliteCandidateRepository(conn=_require_sqlite_connection(settings), source=source)
    return JsonCandidateRepository(cache_dir=settings.cache_dir, filename=_CANDIDATE_FILENAME_BY_SOURCE[source])


# --- Filing-event repository — read-only in both backends (see module docstring) ---
#
# Neither backend exposes a standalone, non-network "write one filing
# event" path in production: the JSON stores only ever write inside
# scan_service.scan() (a live-network-calling function, correctly out of
# scope this phase); the SQLite store's own upsert_filing_event() exists
# but has no real caller yet either (see candidate_repository above for
# the same "factory exists, not yet wired" posture). This adapter is
# read-only for both, matching what's actually safe/legitimate to expose
# without a scan.

class FilingEventRepositoryProtocol(Protocol):
    def load_filing_events(self) -> tuple[FilingEvent, ...]: ...
    def exists(self, corp_code: str, rcept_no: str) -> bool: ...


@dataclass(frozen=True)
class JsonFilingEventRepository:
    cache_dir: Path
    source: str

    def load_filing_events(self) -> tuple[FilingEvent, ...]:
        loader = _FILING_EVENTS_LOADER_BY_SOURCE[self.source]
        return loader(self.cache_dir)

    def exists(self, corp_code: str, rcept_no: str) -> bool:
        return any(f.corp_code == corp_code and f.rcept_no == rcept_no for f in self.load_filing_events())


@dataclass(frozen=True)
class SqliteFilingEventRepository:
    conn: sqlite3.Connection
    source: str

    def load_filing_events(self) -> tuple[FilingEvent, ...]:
        return sqlite_filing_events.load_filing_events(self.conn, self.source)

    def exists(self, corp_code: str, rcept_no: str) -> bool:
        return sqlite_filing_events.filing_event_exists(self.conn, self.source, corp_code, rcept_no)


def get_filing_event_repository(settings: Settings, source: str) -> FilingEventRepositoryProtocol:
    backend = _normalized_backend(settings)
    if backend == "sqlite":
        return SqliteFilingEventRepository(conn=_require_sqlite_connection(settings), source=source)
    return JsonFilingEventRepository(cache_dir=settings.cache_dir, source=source)


# --- Identifier repository — read-only in both backends, same reasoning as filing events ---
#
# resolve_and_cache() (both EDGAR's and DART's) bundles writing inside a
# live-network-calling function too — out of scope this phase. Read-only
# here for the same honesty-over-convenience reason as filing events.

class IdentifierRepositoryProtocol(Protocol):
    def load_identifiers(self) -> dict[str, ResolvedIdentifierRecord]: ...
    def get_identifier(self, lookup_key: str) -> ResolvedIdentifierRecord | None: ...


@dataclass(frozen=True)
class JsonIdentifierRepository:
    cache_dir: Path
    source: str  # "SEC EDGAR" | "OpenDART / DART"

    def load_identifiers(self) -> dict[str, ResolvedIdentifierRecord]:
        if self.source == "SEC EDGAR":
            cached = cik_resolver.load_cached_ciks(self.cache_dir)
            return {
                ticker: ResolvedIdentifierRecord(
                    identifier=r.cik, display_name=r.company_name,
                    resolution_method=r.source, retrieved_at=r.retrieved_at,
                )
                for ticker, r in cached.items()
            }
        cached = corp_code_resolver.load_cached_corp_codes(self.cache_dir)
        return {
            krx: ResolvedIdentifierRecord(
                identifier=r.corp_code, display_name=r.corp_name,
                resolution_method=r.source, retrieved_at=r.retrieved_at,
            )
            for krx, r in cached.items()
        }

    def get_identifier(self, lookup_key: str) -> ResolvedIdentifierRecord | None:
        return self.load_identifiers().get(lookup_key)


@dataclass(frozen=True)
class SqliteIdentifierRepository:
    conn: sqlite3.Connection
    source: str

    def load_identifiers(self) -> dict[str, ResolvedIdentifierRecord]:
        return sqlite_identifiers.load_resolved_identifiers(self.conn, self.source)

    def get_identifier(self, lookup_key: str) -> ResolvedIdentifierRecord | None:
        return sqlite_identifiers.get_resolved_identifier(self.conn, self.source, lookup_key)


def get_identifier_repository(settings: Settings, source: str) -> IdentifierRepositoryProtocol:
    backend = _normalized_backend(settings)
    if backend == "sqlite":
        return SqliteIdentifierRepository(conn=_require_sqlite_connection(settings), source=source)
    return JsonIdentifierRepository(cache_dir=settings.cache_dir, source=source)
