"""Cross-checks Radar's LLM-tagged US tickers against SEC EDGAR's free,
keyless ticker registry, so a plausible-sounding but wrong/hallucinated
ticker is visibly flagged rather than trusted outright.

Only covers US-jurisdiction tags — there's no equivalent free, keyless
registry wired up yet for Japan/Korea/China/Hong Kong tickers (see
src/providers/live_edgar.py's module docstring and README section 4 for
what's blocked there and why). A non-US tag is always reported unverified,
not because it's wrong, but because nothing currently confirms it either
way — see verify_ticker_tags() below.
"""
from __future__ import annotations

from src.config.settings import get_settings
from src.providers import edgar_client
from src.radar.models import TickerTag

US_JURISDICTION = "United States"


def is_verified_us_ticker(ticker: str) -> bool:
    settings = get_settings()
    try:
        registry = edgar_client.get_all_tickers(settings.sec_user_agent)
    except edgar_client.EdgarError:
        return False  # can't confirm right now -> don't claim verified
    return ticker.upper() in registry


def verify_ticker_tags(tags: list[TickerTag]) -> list[TickerTag]:
    """Returns the same tags with `verified` set. Never drops a tag —
    Radar surfaces unverified tags labeled as such rather than silently
    hiding a ticker the LLM may still have gotten right."""
    for tag in tags:
        if tag.jurisdiction == US_JURISDICTION:
            tag.verified = is_verified_us_ticker(tag.ticker)
        else:
            tag.verified = False
    return tags
