"""Seeds the database with the three mock demo tickers (COHR, AAOI, AXTI).

Idempotent: skips a ticker if it's already in the tickers table. Run via
`python -m src.database.seed` or automatically from app.py on first launch.
"""
from __future__ import annotations

import logging

from src.config.settings import get_settings
from src.database.db import get_connection, init_db
from src.providers.mock_providers import FIXTURE_FILES, get_watchlist_seed
from src.services import research_service, thesis_service, ticker_service, watchlist_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_demo_data() -> None:
    settings = get_settings()
    init_db(settings)

    with get_connection(settings) as conn:
        for ticker in FIXTURE_FILES:
            if ticker_service.get_ticker(conn, ticker):
                logger.info("Skipping %s — already seeded.", ticker)
                continue

            data = get_watchlist_seed(ticker)
            if not data:
                continue

            ticker_service.upsert_ticker(
                conn, ticker, data["company_name"], data["sector"], data["subtheme"],
                data["market_cap_category"], jurisdiction=data["jurisdiction"], is_mock=True,
            )

            seed = data["watchlist_seed"]
            watchlist_service.upsert_watchlist_record(
                conn, ticker=ticker, tier=seed["tier"], thesis_short=seed["thesis_short"],
                why_on_watchlist=seed["why_on_watchlist"], conviction_score=seed["conviction_score"],
                evidence_status=seed["evidence_status"], next_catalyst=seed["next_catalyst"],
                next_catalyst_date=seed["next_catalyst_date"],
                key_confirmation_metric=seed["key_confirmation_metric"],
                key_invalidation_metric=seed["key_invalidation_metric"],
                latest_material_change=seed["latest_material_change"], reason="Initial seed data",
            )

            thesis = data["thesis"]
            thesis_service.save_thesis(
                conn, ticker=ticker, theme=thesis["theme"], subtheme=data["subtheme"],
                why_on_watchlist=seed["why_on_watchlist"], inflection_thesis=thesis["inflection_thesis"],
                thesis_owner_notes="Seeded demo thesis — replace with your own notes.",
                evidence_supporting=[], evidence_contradicting=[],
                confirmation_conditions=thesis["confirmation_conditions"],
                invalidation_conditions=thesis["invalidation_conditions"], key_risks=thesis["key_risks"],
                next_catalyst=seed["next_catalyst"], next_catalyst_date=seed["next_catalyst_date"],
                tier=seed["tier"], score=float(seed["conviction_score"]), tags=thesis["tags"],
            )

            logger.info("Seeded %s, generating an initial research brief...", ticker)
            try:
                research_service.generate_research_brief(
                    conn, settings, ticker, question=f"Initial seed research brief for {ticker}."
                )
            except Exception as exc:  # pragma: no cover - seed should not crash app startup
                logger.warning("Could not generate seed brief for %s: %s", ticker, exc)

    logger.info("Seed complete.")


if __name__ == "__main__":
    seed_demo_data()
