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
    ("United States", "SEC EDGAR", "Free. Full-text search & submissions API, requires a compliant User-Agent header."),
    ("Japan", "EDINET", "Free. Financial Services Agency's disclosure system; API returns filings in Japanese."),
    ("South Korea", "DART", "Free with a registered API key from the Financial Supervisory Service; filings in Korean."),
    ("China", "CNINFO / SSE / SZSE", "Free public disclosure portals; filings in Simplified Chinese."),
    ("Hong Kong", "HKEXnews", "Free public disclosure portal for HKEX-listed issuers."),
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
        "it covers all of these — so a live `FilingsProvider` implementation should branch on the "
        "ticker's jurisdiction to call the right regulator's API. None of these are wired up in V1; "
        "all filings are mock data regardless of jurisdiction."
    )
    st.dataframe(
        [{"Jurisdiction": j, "Regulator / system": r, "Notes": n} for j, r, n in JURISDICTION_REGULATORS],
        width='stretch', hide_index=True,
    )
    st.caption(
        "Non-English filings (EDINET, DART, CNINFO) will need translation before they can feed the "
        "same excerpt-tagging pipeline as English-language SEC filings — that translation step isn't "
        "built in V1 and should preserve the original-language text alongside any translation for "
        "auditability (guardrail principle #9)."
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
