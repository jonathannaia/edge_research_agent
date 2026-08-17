"""SEC EDGAR pilot's wiring layer — mirrors
src/data_access/dart/radar_service.py's shape and reasoning exactly
(kept as a separate module from the DART one, not merged, so each
source has its own independent readiness check and client/provider
construction — see that module's own docstring for why).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.config.settings import Settings
from src.config.tracked_companies import TrackedCompany, get_tracked_companies_for_source, with_resolved_ciks
from src.data_access.edgar import cik_resolver, edgar_pipeline, scan_service
from src.data_access.edgar.client import EdgarClient
from src.models.models import CandidateSignal

_EDGAR_SOURCE = "SEC EDGAR"


@dataclass(frozen=True)
class EdgarReadiness:
    user_agent_configured: bool
    unresolved_companies: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return self.user_agent_configured and not self.unresolved_companies


def get_edgar_companies(cache_dir: Path) -> tuple[TrackedCompany, ...]:
    resolved = {ticker: record.cik for ticker, record in cik_resolver.load_cached_ciks(cache_dir).items()}
    return with_resolved_ciks(get_tracked_companies_for_source(_EDGAR_SOURCE), resolved)


def edgar_readiness(settings: Settings) -> EdgarReadiness:
    """Never raises and never makes a network call — a page-load-time
    check only, so a missing User-Agent or an unresolved company shows a
    clear empty state instead of a crash or a silent demo fallback."""
    companies = get_edgar_companies(settings.cache_dir)
    unresolved = tuple(c.name for c in companies if not c.corp_code)
    return EdgarReadiness(
        user_agent_configured=bool(settings.edgar_user_agent),
        unresolved_companies=unresolved,
    )


def _client(settings: Settings) -> EdgarClient:
    return EdgarClient(settings.edgar_user_agent)


def run_scan(
    settings: Settings,
    lookback_days: int = scan_service.DEFAULT_LOOKBACK_DAYS,
    max_candidates: int = edgar_pipeline.DEFAULT_MAX_CANDIDATES_PER_SCAN,
) -> edgar_pipeline.ScanReport:
    companies = get_edgar_companies(settings.cache_dir)
    return edgar_pipeline.run_pipeline(
        _client(settings), list(companies), settings.cache_dir,
        lookback_days=lookback_days, max_candidates_to_process=max_candidates,
    )


def process_candidate_now(settings: Settings, candidate_id: str) -> CandidateSignal | None:
    return edgar_pipeline.process_single_candidate(_client(settings), candidate_id, settings.cache_dir)
