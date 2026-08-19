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

# Private-beta access foundation, Phase 1 (configuration + gating only — see
# design/DECISIONS.md; no Google/OIDC login is implemented yet). Defaults
# preserve today's fully-open local-dev behavior: absent, blank, or an
# unrecognized value always resolves to disabled/empty, never enabled.
_PRIVATE_BETA_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _parse_beta_auth_enabled(var_name: str) -> bool:
    return (os.getenv(var_name) or "").strip().lower() in _PRIVATE_BETA_TRUE_VALUES


def _parse_beta_allowed_emails(var_name: str) -> frozenset[str]:
    raw = os.getenv(var_name) or ""
    return frozenset(email for email in (part.strip().lower() for part in raw.split(",")) if email)


@dataclass(frozen=True)
class Settings:
    app_version: str = APP_VERSION
    app_name: str = APP_NAME
    # Always "demo" in this phase — no live data mode exists yet. Kept as a
    # field (not a hardcoded string in the UI) so Phase 2 can introduce a
    # real "live" mode without a UI rewrite.
    data_mode: str = field(default_factory=lambda: os.getenv("EDGE_DATA_MODE", "demo"))
    seed_data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "seed")
    # Korea DART radar pilot — narrowly scoped, not a general "live mode"
    # switch (see design/DECISIONS.md). None means unconfigured; callers
    # must show a clear missing-key state rather than guessing or crashing.
    dart_api_key: str | None = field(default_factory=lambda: os.getenv("EDGE_DART_API_KEY") or None)
    translation_api_key: str | None = field(default_factory=lambda: os.getenv("EDGE_TRANSLATION_API_KEY") or None)
    # SEC EDGAR radar pilot — not a secret (EDGAR needs no API key at all),
    # but still a required, non-empty identifying contact string per SEC's
    # own access policy. None means unconfigured; callers must fail closed
    # with a typed config error rather than sending an unidentified request
    # EDGAR would reject anyway. Never logged/printed/exposed — only ever
    # checked for presence (see edgar_service.edgar_readiness).
    edgar_user_agent: str | None = field(default_factory=lambda: os.getenv("EDGE_EDGAR_USER_AGENT") or None)
    # EDINET (Japan) radar pilot — planning Gate 1, fixture-only. This
    # gate never reads/validates the real value beyond presence-checking
    # (see edinet_service.edinet_readiness); no live request uses it yet.
    # Exactly one env var, no competing aliases, per the Gate 1 brief.
    edinet_subscription_key: str | None = field(default_factory=lambda: os.getenv("EDGE_EDINET_SUBSCRIPTION_KEY") or None)
    cache_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "cache")
    # Private-beta access foundation, Phase 1 — disabled by default so every
    # existing page keeps working with no configuration at all. The
    # allowlist alone is authorization, not authentication (see
    # src/ui/beta_gate.py); no identity/sign-in exists yet this phase.
    private_beta_auth_enabled: bool = field(default_factory=lambda: _parse_beta_auth_enabled("EDGE_PRIVATE_BETA_AUTH_ENABLED"))
    private_beta_allowed_emails: frozenset[str] = field(default_factory=lambda: _parse_beta_allowed_emails("EDGE_PRIVATE_BETA_ALLOWED_EMAILS"))
    # R2 remote-cache sync (dormant infrastructure — see
    # src/data_access/remote_cache/ — nothing in the app reads/writes
    # through these yet). Disabled by default so every existing page and
    # pipeline keeps working with no configuration at all. None means
    # unconfigured for each individual field; remote_cache_available()
    # requires r2_endpoint/r2_access_key_id/r2_secret_access_key/r2_bucket
    # to all be present (r2_account_id is optional metadata only — see
    # r2_client.py's r2_settings_complete()), never a partial config of
    # the four required fields. Never logged/printed/exposed — only ever
    # checked for presence, same discipline as dart_api_key/edgar_user_agent above.
    remote_cache_enabled: bool = field(default_factory=lambda: _parse_beta_auth_enabled("EDGE_REMOTE_CACHE_ENABLED"))
    r2_account_id: str | None = field(default_factory=lambda: os.getenv("EDGE_R2_ACCOUNT_ID") or None)
    r2_access_key_id: str | None = field(default_factory=lambda: os.getenv("EDGE_R2_ACCESS_KEY_ID") or None)
    r2_secret_access_key: str | None = field(default_factory=lambda: os.getenv("EDGE_R2_SECRET_ACCESS_KEY") or None)
    r2_bucket: str | None = field(default_factory=lambda: os.getenv("EDGE_R2_BUCKET") or None)
    r2_endpoint: str | None = field(default_factory=lambda: os.getenv("EDGE_R2_ENDPOINT") or None)


def get_settings() -> Settings:
    return Settings()


def demo_last_updated_label() -> str:
    """A clearly-labeled mock 'last updated' value for the global status
    banner — never a real data-refresh timestamp in this phase."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d (demo session)")
