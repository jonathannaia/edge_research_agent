from __future__ import annotations

import streamlit as st

from src.config.settings import Settings

PROVIDER_DOMAINS = [
    # (Domain, Typical live source, Env var(s), Status)
    ("Fundamentals (US)", "SEC EDGAR XBRL company facts API (free).", "EDGE_SEC_USER_AGENT", "LIVE"),
    ("Filings (US)", "SEC EDGAR submissions API (free, requires a compliant User-Agent).", "EDGE_SEC_USER_AGENT", "LIVE"),
    ("Earnings transcripts", "A transcript vendor (e.g. a paid API) or manually pasted excerpts via the Sources page.", "—", "Mock only"),
    ("Insider transactions", "SEC EDGAR Form 4 filings (free).", "EDGE_SEC_USER_AGENT", "Mock only"),
    ("Ownership data", "SEC 13F aggregation or a data vendor.", "—", "Mock only"),
    ("Price & volume", "A market data vendor (free tier or paid).", "EDGE_MARKET_DATA_API_KEY", "Mock only"),
    ("Earnings calendar", "A market data vendor or company IR page.", "EDGE_MARKET_DATA_API_KEY", "Mock only"),
    ("News & press releases", "A news API or official company RSS/press feeds.", "EDGE_NEWS_API_KEY", "Mock only"),
]

JURISDICTION_REGULATORS = [
    # (Jurisdiction, Regulator, Notes, Status)
    (
        "United States", "SEC EDGAR",
        "Free, keyless — just a compliant User-Agent header.",
        "LIVE (see src/providers/live_edgar.py)",
    ),
    (
        "Japan", "EDINET",
        "Free official API (v2). Requires registering an account at "
        "api.edinet-fsa.go.jp with phone number verification to get an API key. "
        "Filings are in Japanese — no translation step built yet.",
        "Blocked on account signup (needs your phone number — can't be done on your behalf)",
    ),
    (
        "South Korea", "DART (OpenDART)",
        "Free official API. Requires registering an account at opendart.fss.or.kr "
        "with email verification to get a 40-char API key. Filings are in Korean — "
        "no translation step built yet.",
        "Blocked on account signup (needs your email verification — can't be done on your behalf)",
    ),
    (
        "China", "CNINFO / SSE / SZSE",
        "No official public API exists. Only options are scraping undocumented "
        "endpoints or a paid third-party vendor.",
        "Blocked — scraping would violate the app's own ToS-compliance guardrail",
    ),
    (
        "Hong Kong", "HKEXnews",
        "Public and login-free to browse, but its search is a stateful Java web "
        "form (session/viewstate-based), not a documented API — confirmed by "
        "direct inspection, not assumed.",
        "Blocked — no stable programmatic access without reverse-engineering a fragile, unsupported endpoint",
    ),
]


def render(settings: Settings) -> None:
    st.metric("Current data mode", settings.data_mode)
    if settings.data_mode == "live":
        st.success(
            "Live mode is on. US fundamentals and filings pull real data from SEC EDGAR "
            "(`src/providers/live_edgar.py`). Every other domain below is still mock, and a ticker "
            "EDGAR has no data for falls back to mock automatically — always check the `is_mock` "
            "badge on what you're looking at, never assume live mode means everything is real."
        )
    else:
        st.write(
            "Set `EDGE_DATA_MODE=live` in `.env` to turn on live SEC EDGAR fundamentals and filings for "
            "US tickers — no API key needed, just a compliant `EDGE_SEC_USER_AGENT`. Every other domain "
            "below is still mock-only; implement its interface in `src/providers/` and wire it into "
            "`src/providers/registry.py` to go live, one domain at a time."
        )

    st.subheader("Provider domains")
    st.dataframe(
        [{"Domain": d, "Typical live source": s, "Env var(s)": e, "Status": st_} for d, s, e, st_ in PROVIDER_DOMAINS],
        width='stretch', hide_index=True,
    )

    st.subheader("Filings by jurisdiction")
    st.write(
        "Each ticker carries a `jurisdiction` field (set when you add it on the Watchlist page) that "
        "identifies its primary regulator. `SourceType.Regulatory Filing` is deliberately generic — "
        "it covers all of these — so a live `FilingsProvider` implementation branches on the ticker's "
        "jurisdiction to call the right regulator's API. Only US filings are live so far; the other "
        "three are genuinely blocked right now, each for a different documented reason (see Status "
        "below) — not just unimplemented."
    )
    st.dataframe(
        [{"Jurisdiction": j, "Regulator / system": r, "Notes": n, "Status": s} for j, r, n, s in JURISDICTION_REGULATORS],
        width='stretch', hide_index=True,
    )
    st.caption(
        "Non-English filings (EDINET, DART) will need translation before they can feed the same "
        "excerpt-tagging pipeline as English-language SEC filings — that translation step isn't built "
        "yet either, and should preserve the original-language text alongside any translation for "
        "auditability (guardrail principle #9) once it is."
    )

    st.subheader("Cost-control limits (apply in both mock and live mode)")
    st.write(
        f"- Max sources fetched per brief: **{settings.max_sources_per_brief}**\n"
        f"- Max excerpts kept per source: **{settings.max_excerpts_per_source}**\n"
        f"- Max watchlist size (MVP soft limit): **{settings.max_watchlist_size}**\n\n"
        "Edit these via `.env` (`EDGE_MAX_SOURCES_PER_BRIEF`, `EDGE_MAX_EXCERPTS_PER_SOURCE`)."
    )

    st.info(
        "See the README's 'Data Provider Integration Guide' for exact steps, endpoints, and compliance notes "
        "(e.g. SEC EDGAR's fair-access rules) for moving each domain from mock to live."
    )
