"""Human-review decision recording (Stage 2A) — a single, source-agnostic
seam a future Radar Inbox UI action calls into. Pure orchestration over
the existing candidate_store API; no source-specific logic, mirroring
signal_promotion.py's own separation of concerns.

Reuses the two currently-unused CandidateSignal fields identified in the
Stage 1 audit — `reviewed_at`/`reviewed_note` — finally writing them.
Every decision is additive: a new StateTransition is appended, never
replacing prior history, so a candidate's full review trail (including
any earlier reviewer decision this function itself recorded) stays
intact — changing a decision later is expected, not prevented."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.data_access.dart import candidate_store
from src.models.models import CandidateSignal, CandidateStatus, StateTransition

# The only statuses a human reviewer may set through this function. Any
# other CandidateStatus (pipeline-internal states, or the automated
# NOT_MATERIAL gate) is rejected before anything is loaded or written —
# fail closed, never guess which status was intended.
_PERMITTED_REVIEWER_STATUSES = frozenset({
    CandidateStatus.PUBLISHED, CandidateStatus.MONITORING, CandidateStatus.DISMISSED,
})


def record_review_decision(
    cache_dir: Path,
    candidate_id: str,
    filename: str,
    status: CandidateStatus,
    note: str = "",
) -> CandidateSignal | None:
    """Records one human reviewer decision for one already-persisted
    candidate. `filename` is the caller's responsibility (same routing
    the existing "Prepare analyst view" action already does by candidate
    ID prefix — see radar_inbox.py) — this function has no source
    awareness of its own, matching candidate_store.py's own design.

    Returns the updated CandidateSignal, or None if `candidate_id` isn't
    found in the store at `cache_dir`/`filename` — no write occurs in
    that case. Raises ValueError, before any load or write, if `status`
    isn't one of the three permitted reviewer outcomes."""
    if status not in _PERMITTED_REVIEWER_STATUSES:
        raise ValueError(
            "record_review_decision only accepts a reviewer outcome of "
            "PUBLISHED, MONITORING, or DISMISSED — got "
            f"{status!r}."
        )

    store = candidate_store.load_candidates(cache_dir, filename)
    candidate = store.get(candidate_id)
    if candidate is None:
        return None

    now = datetime.now(timezone.utc).isoformat()
    detail = note if note else f"Reviewer decision: {status.value}"

    candidate.status = status
    candidate.reviewed_at = now
    candidate.reviewed_note = note
    candidate.state_history.append(StateTransition(status=status, at=now, detail=detail))

    candidate_store.update_candidate(cache_dir, candidate, filename)
    return candidate
