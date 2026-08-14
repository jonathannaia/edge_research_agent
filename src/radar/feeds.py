"""Free, no-API-key RSS sources Radar is allowed to read from.

Every feed is hand-picked and scoped to one of the four Radar niches. This
list is the entire crawl surface — Radar never follows links off these feeds
or discovers new sources on its own (cost-bounded, no open-ended crawling;
see EDGE_MAX_SOURCES_PER_BRIEF for the same principle applied to the manual
research pipeline).
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from src.config.settings import get_settings
from src.providers import edgar_client
from src.radar.models import Niche

# Caps how many SEC EDGAR full-text search hits feed into a scan run —
# full-text search on a broad term returns hundreds of matches, and this
# is one source among several sharing the same overall per-run LLM budget
# (EDGE_RADAR_MAX_ITEMS_PER_RUN), so it must not crowd the others out.
EDGAR_SEARCH_MAX_RESULTS = 8
EDGAR_SEARCH_LOOKBACK_DAYS = 2  # freshness.py still enforces the real 24h cutoff downstream


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
    Feed("Data Center Knowledge", "https://www.datacenterknowledge.com/rss.xml", Niche.AI_BUILDOUT.value, "Reputable Financial News"),
    Feed("TechCrunch — AI", "https://techcrunch.com/category/artificial-intelligence/feed/", Niche.AI_BUILDOUT.value, "Reputable Financial News"),
    Feed("IEEE Spectrum — AI", "https://spectrum.ieee.org/feeds/topic/artificial-intelligence.rss", Niche.AI_BUILDOUT.value, "Reputable Financial News"),
    # --- Humanoids ---
    Feed("IEEE Spectrum — Robotics", "https://spectrum.ieee.org/feeds/topic/robotics.rss", Niche.HUMANOIDS.value, "Reputable Financial News"),
    Feed("The Robot Report", "https://www.therobotreport.com/feed/", Niche.HUMANOIDS.value, "Reputable Financial News"),
    # --- Space ---
    Feed("NASA News Releases", "https://www.nasa.gov/news-release/feed/", Niche.SPACE.value, "Regulatory/Gov Release"),
    Feed("SpaceNews", "https://spacenews.com/feed/", Niche.SPACE.value, "Reputable Financial News"),
    Feed("Ars Technica — Space", "https://arstechnica.com/tag/space/feed/", Niche.SPACE.value, "Reputable Financial News"),
    Feed("Space.com", "https://www.space.com/feeds.xml", Niche.SPACE.value, "Reputable Financial News"),
    # --- Macro / Rates / Policy ---
    Feed("Federal Reserve — Press Releases", "https://www.federalreserve.gov/feeds/press_all.xml", Niche.MACRO.value, "Regulatory/Gov Release"),
    Feed("European Central Bank — Press", "https://www.ecb.europa.eu/rss/press.html", Niche.MACRO.value, "Regulatory/Gov Release"),
    Feed("Bank of Japan — Press (English)", "https://www.boj.or.jp/en/rss/whatsnew.xml", Niche.MACRO.value, "Regulatory/Gov Release"),
    Feed("Bank of England — News", "https://www.bankofengland.co.uk/rss/news", Niche.MACRO.value, "Regulatory/Gov Release"),
]


def fetch_feed(feed: Feed, timeout: int = 15) -> tuple[list[dict], str | None]:
    """Fetches and parses one feed. Returns (entries, error_message).

    entries is a list of plain dicts (title, link, summary, published) so
    callers don't depend on feedparser's FeedParserDict shape. Never raises
    — a broken/unreachable feed is reported as an error and skipped, not a
    fatal failure for the whole scan run.
    """
    import urllib.request

    import feedparser

    from src.utils.ssl_context import SSL_CONTEXT

    # feedparser does its own HTTPS fetch under the hood, with its own
    # default SSL context — passing an explicit HTTPSHandler here is what
    # makes it use certifi's CA bundle too (see src/utils/ssl_context.py's
    # docstring for why this matters on some Python installs).
    handlers = [urllib.request.HTTPSHandler(context=SSL_CONTEXT)] if SSL_CONTEXT else []

    try:
        parsed = feedparser.parse(
            feed.url, request_headers={"User-Agent": "EevaResearchAI-Radar/1.0"}, handlers=handlers
        )
    except Exception as exc:  # pragma: no cover - network failure path
        return [], f"{feed.name}: fetch failed ({exc})"

    if getattr(parsed, "bozo", False) and not parsed.entries:
        return [], f"{feed.name}: unparseable feed ({getattr(parsed, 'bozo_exception', 'unknown error')})"

    entries = []
    for e in parsed.entries:
        # feedparser normalizes whatever date format the feed uses into a
        # UTC time.struct_time on *_parsed — far more reliable than trying
        # to parse the raw "published" string ourselves. This is what the
        # freshness gate in scan.py filters on.
        date_struct = e.get("published_parsed") or e.get("updated_parsed")
        published_epoch = calendar.timegm(date_struct) if date_struct else None

        entries.append(
            {
                "title": (e.get("title") or "").strip(),
                "link": (e.get("link") or "").strip(),
                "summary": (e.get("summary") or e.get("description") or "").strip(),
                "published": e.get("published") or e.get("updated") or "",
                "published_epoch": published_epoch,
            }
        )
    return entries, None


EDGAR_SEARCH_FEED = Feed(
    "SEC EDGAR Full-Text Search — 8-K capex filings",
    "https://www.sec.gov/edgar/search/",
    Niche.AI_BUILDOUT.value,
    "Regulatory Filing",
)


def fetch_edgar_search_entries(query: str = "data center capital expenditure") -> tuple[list[dict], str | None]:
    """A 'virtual feed' backed by SEC EDGAR's full-text search, not RSS —
    surfaces real 8-K filings mentioning the query, with a confirmed filer
    from the filing itself rather than an LLM's guess at who a news story
    is about. Uses the same free, keyless API verified for
    src/providers/live_edgar.py. Capped to the top EDGAR_SEARCH_MAX_RESULTS
    (already relevance-sorted) so one broad-matching source can't crowd out
    every other feed's share of the per-run LLM budget."""
    settings = get_settings()
    start = (date.today() - timedelta(days=EDGAR_SEARCH_LOOKBACK_DAYS)).isoformat()
    end = date.today().isoformat()

    try:
        data = edgar_client.full_text_search(query, settings.sec_user_agent, forms="8-K", start_date=start, end_date=end)
    except edgar_client.EdgarError as exc:
        return [], f"{EDGAR_SEARCH_FEED.name}: {exc}"

    entries = []
    for hit in data.get("hits", {}).get("hits", [])[:EDGAR_SEARCH_MAX_RESULTS]:
        src = hit.get("_source", {})
        display_names = ", ".join(src.get("display_names", [])) or "Unknown filer"
        form = src.get("form", "8-K")
        file_date = src.get("file_date", "")
        cik = (src.get("ciks") or [None])[0]
        accession, _, filename = hit.get("_id", "").partition(":")

        link = (
            edgar_client.filing_document_url(int(cik), accession, filename)
            if cik and accession and filename
            else "https://www.sec.gov/cgi-bin/browse-edgar"
        )
        try:
            published_epoch = int(datetime.fromisoformat(file_date).replace(tzinfo=timezone.utc).timestamp()) if file_date else None
        except ValueError:
            published_epoch = None

        entries.append(
            {
                "title": f"{form} filed by {display_names}",
                "link": link,
                # Naming the confirmed filer directly in the snippet gives the LLM
                # real grounding for ticker tagging, instead of guessing from a
                # bare headline the way it has to for ordinary news feed items.
                "summary": f"SEC EDGAR {form} filing by {display_names}, filed {file_date}. Matched search term: {query!r}.",
                "published": file_date,
                "published_epoch": published_epoch,
            }
        )
    return entries, None


def fetch_all(feeds: list[Feed] | None = None) -> tuple[list[tuple[Feed, dict]], list[str]]:
    """Fetches every configured feed plus the SEC EDGAR full-text-search
    virtual feed. Returns (items, errors) where items is a flat list of
    (feed, entry) pairs across all sources."""
    feeds = feeds if feeds is not None else FEEDS
    items: list[tuple[Feed, dict]] = []
    errors: list[str] = []
    for feed in feeds:
        entries, err = fetch_feed(feed)
        if err:
            errors.append(err)
        for entry in entries:
            items.append((feed, entry))

    edgar_entries, edgar_err = fetch_edgar_search_entries()
    if edgar_err:
        errors.append(edgar_err)
    for entry in edgar_entries:
        items.append((EDGAR_SEARCH_FEED, entry))

    return items, errors
