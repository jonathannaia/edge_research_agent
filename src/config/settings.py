"""Central application configuration, loaded from environment variables.

All keys and tunables live here. Nothing in this module talks to the
network or the database — it only resolves configuration values.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - python-dotenv is a listed dependency
    pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_name: str = "Edge Research Agent"
    app_version: str = "0.1.0"

    data_mode: str = field(default_factory=lambda: os.getenv("EDGE_DATA_MODE", "mock").strip().lower())
    db_path: Path = field(
        default_factory=lambda: PROJECT_ROOT / os.getenv("EDGE_DB_PATH", "data/edge_research.db")
    )

    freshness_fresh_days: int = field(default_factory=lambda: _env_int("EDGE_FRESHNESS_FRESH_DAYS", 30))
    freshness_aging_days: int = field(default_factory=lambda: _env_int("EDGE_FRESHNESS_AGING_DAYS", 60))
    freshness_stale_days: int = field(default_factory=lambda: _env_int("EDGE_FRESHNESS_STALE_DAYS", 90))

    # Cost-control limits (guardrail principle #10). Deliberately conservative
    # so a brief generation is bounded work, not an open-ended crawl.
    max_sources_per_brief: int = field(default_factory=lambda: _env_int("EDGE_MAX_SOURCES_PER_BRIEF", 12))
    max_excerpts_per_source: int = field(default_factory=lambda: _env_int("EDGE_MAX_EXCERPTS_PER_SOURCE", 5))
    max_watchlist_size: int = 25

    sec_user_agent: str = field(
        default_factory=lambda: os.getenv("EDGE_SEC_USER_AGENT", "Edge Research Agent (unconfigured@example.com)")
    )

    def freshness_status(self, age_days: int) -> str:
        if age_days <= self.freshness_fresh_days:
            return "fresh"
        if age_days <= self.freshness_aging_days:
            return "aging"
        if age_days <= self.freshness_stale_days:
            return "stale"
        return "very_stale"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
