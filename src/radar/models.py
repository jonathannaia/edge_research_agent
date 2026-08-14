"""Data model for the Radar autonomous scanner.

Deliberately separate from src/models/models.py and the SQLite schema: Radar
findings are written by a GitHub Actions job and read by the Streamlit app —
two processes that don't share a filesystem — so they're persisted as a JSON
file committed to the repo rather than in the app's local SQLite database.
See src/radar/store.py for the read/write layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Niche(str, Enum):
    """The four scan scopes Radar is allowed to operate in. Deliberately
    fixed and small — Radar must never expand into topics the user didn't
    name."""

    AI_BUILDOUT = "AI Buildout"
    HUMANOIDS = "Humanoids"
    SPACE = "Space"
    MACRO = "Macro / Rates / Policy"


@dataclass
class TickerTag:
    ticker: str
    company_name: str
    jurisdiction: str  # matches src.models.models.Jurisdiction values


@dataclass
class RadarFinding:
    """One autonomously-surfaced, cited item. Every field that could carry a
    claim is tied to source_url — there is no free-floating text field, so a
    finding is structurally citable by construction (guardrail principle #1
    applied to Radar)."""

    niche: str  # Niche value
    headline: str
    summary: str  # 1-2 sentence, cited-to-source, no buy/sell/hold language
    source_url: str
    source_name: str
    source_type: str  # "Press Release" | "Reputable Financial News" | "Regulatory/Gov Release"
    published_at: str  # ISO 8601, from the feed item when available
    retrieved_at: str  # ISO 8601, when Radar fetched it
    tickers: list[TickerTag] = field(default_factory=list)
    relevance_reason: str = ""  # why the LLM judged this in-scope
    url_hash: str = ""  # dedup key, set by store.py
    id: str = ""  # set by store.py


@dataclass
class ScanRunRecord:
    """One row of Radar's own audit trail (guardrail principle #9, applied
    to an unattended job with no human approving each run)."""

    started_at: str
    finished_at: str
    status: str  # "ok" | "partial_error" | "error"
    feeds_checked: int
    items_seen: int
    items_after_freshness_filter: int  # items within EDGE_RADAR_MAX_AGE_HOURS (default 24h)
    items_after_keyword_filter: int
    items_sent_to_llm: int
    items_saved: int
    items_rejected_by_guardrail: int
    errors: list[str] = field(default_factory=list)
