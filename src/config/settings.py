"""App-wide configuration for the foundation build.

Phase 1 needs no environment variables to run — everything is demo data
read from data/seed/. The settings that exist are here so Phase 2 has a
single, already-wired place to add real configuration (data mode, provider
keys) without touching UI code.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

APP_VERSION = "0.1.0-foundation"
APP_NAME = "EevaResearch AI"


@dataclass(frozen=True)
class Settings:
    app_version: str = APP_VERSION
    app_name: str = APP_NAME
    # Always "demo" in this phase — no live data mode exists yet. Kept as a
    # field (not a hardcoded string in the UI) so Phase 2 can introduce a
    # real "live" mode without a UI rewrite.
    data_mode: str = field(default_factory=lambda: os.getenv("EDGE_DATA_MODE", "demo"))
    seed_data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "seed")


def get_settings() -> Settings:
    return Settings()


def demo_last_updated_label() -> str:
    """A clearly-labeled mock 'last updated' value for the global status
    banner — never a real data-refresh timestamp in this phase."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d (demo session)")
