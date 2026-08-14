"""Free, no-API-key RSS sources Radar is allowed to read from.

Every feed is hand-picked and scoped to one of the four Radar niches. This
list is the entire crawl surface — Radar never follows links off these feeds
or discovers new sources on its own (cost-bounded, no open-ended crawling;
see EDGE_MAX_SOURCES_PER_BRIEF for the same principle applied to the manual
research pipeline).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.radar.models import Niche


@dataclass(frozen=True)
class Feed:
    name: str
    url: str
    niche: str  # Niche value
    source_type: str  # RadarFinding.source_type


FEEDS: list[Feed] = [
    # --- AI Buildout ---
    Feed("Data Center Dynamics", "https://www.datacenterdynamics.com/en/rss/", Niche.AI_BUILDOUT.value, "Reputable Financial News"),
    Feed("Semiconductor Engineering", "https://semiengineering.com/feed/", Niche.AI_BUILDOUT.value, "Reputable Financial News"),
    Feed("NVIDIA Newsroom", "https://nvidianews.nvidia.com/releases.xml", Niche.AI_BUILDOUT.value, "Press Release"),
    # --- Humanoids ---
    Feed("IEEE Spectrum — Robotics", "https://spectrum.ieee.org/feeds/topic/robotics.rss", Niche.HUMANOIDS.value, "Reputable Financial News"),
    Feed("The Robot Report", "https://www.therobotreport.com/feed/", Niche.HUMANOIDS.value, "Reputable Financial News"),
    # --- Space ---
    Feed("NASA News Releases", "https://www.nasa.gov/news-release/feed/", Niche.SPACE.value, "Regulatory/Gov Release"),
    Feed("SpaceNews", "https://spacenews.com/feed/", Niche.SPACE.value, "Reputable Financial News"),
    # --- Macro / Rates / Policy ---
    Feed("Federal Reserve — Press Releases", "https://www.federalreserve.gov/feeds/press_all.xml", Niche.MACRO.value, "Regulatory/Gov Release"),
    Feed("European Central Bank — Press", "https://www.ecb.europa.eu/rss/press.html", Niche.MACRO.value, "Regulatory/Gov Release"),
]


def fetch_feed(feed: Feed, timeout: int = 15) -> tuple[list[dict], str | None]:
    """Fetches and parses one feed. Returns (entries, error_message).

    entries is a list of plain dicts (title, link, summary, published) so
    callers don't depend on feedparser's FeedParserDict shape. Never raises
    — a broken/unreachable feed is reported as an error and skipped, not a
    fatal failure for the whole scan run.
    """
    import feedparser

    try:
        parsed = feedparser.parse(feed.url, request_headers={"User-Agent": "EevaResearchAI-Radar/1.0"})
    except Exception as exc:  # pragma: no cover - network failure path
        return [], f"{feed.name}: fetch failed ({exc})"

    if getattr(parsed, "bozo", False) and not parsed.entries:
        return [], f"{feed.name}: unparseable feed ({getattr(parsed, 'bozo_exception', 'unknown error')})"

    entries = []
    for e in parsed.entries:
        entries.append(
            {
                "title": (e.get("title") or "").strip(),
                "link": (e.get("link") or "").strip(),
                "summary": (e.get("summary") or e.get("description") or "").strip(),
                "published": e.get("published") or e.get("updated") or "",
            }
        )
    return entries, None


def fetch_all(feeds: list[Feed] | None = None) -> tuple[list[tuple[Feed, dict]], list[str]]:
    """Fetches every configured feed. Returns (items, errors) where items is
    a flat list of (feed, entry) pairs across all feeds."""
    feeds = feeds if feeds is not None else FEEDS
    items: list[tuple[Feed, dict]] = []
    errors: list[str] = []
    for feed in feeds:
        entries, err = fetch_feed(feed)
        if err:
            errors.append(err)
        for entry in entries:
            items.append((feed, entry))
    return items, errors
