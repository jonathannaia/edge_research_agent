"""Live DART (Korea) provider — requires a free API key (EDGE_DART_API_KEY),
unlike SEC EDGAR which needs no key. Register at opendart.fss.or.kr — see
README "Filings beyond the US" for the signup steps.

Verification note, in the same spirit as live_edgar.py: the endpoint URLs,
request parameters, and response field names below were confirmed against
DART's official API documentation (opendart.fss.or.kr/guide) before this
was written — not guessed. This was then verified live (scripts/
dart_smoke_test.py against real Samsung Electronics data), which caught
two real bugs the docs alone didn't make obvious:

1. bgn_de/end_de default to *today* when omitted from the filings list
   call, not "all time" — omitting them returned "no data found" for a
   company that files constantly. Fixed by always passing an explicit
   1-year window.
2. Annual reports use "frmtrm_amount" for the prior-year comparison
   figure, but quarterly/semi-annual reports don't have that key at all —
   they use "frmtrm_q_amount" instead (see _prior_amount()'s docstring).
   Using the wrong key silently produced 0.0% growth for every non-annual
   Korean filing rather than an error, so it wasn't obvious without
   inspecting a real raw response.

Both are fixed and reverified against live data. Fundamentals otherwise
matched correctly on the first attempt (revenue, gross margin, operating
margin, cash, and total debt all came back sensible for a real company) —
the Korean account-name candidates below are confirmed correct against
real data, not just plausible-looking guesses.

Korean "tickers" are DART's 6-digit exchange stock codes (e.g. "005930"
for Samsung Electronics), not letter symbols — that's what to enter as the
ticker for a South Korea-jurisdiction watchlist entry.
"""
from __future__ import annotations

from datetime import date, timedelta

from src.config.settings import Settings
from src.providers import dart_client
from src.providers.base import (
    FilingHighlight,
    FilingsProvider,
    FundamentalsProvider,
    FundamentalsSnapshot,
)

# DART pblntf_ty codes: A=periodic disclosure (annual/quarterly reports,
# the 10-K/10-Q equivalent), B=major event report (the 8-K equivalent).
FILING_TYPES_OF_INTEREST = {"A", "B"}

_REVENUE_NAMES = ["매출액", "수익(매출액)", "영업수익"]
_GROSS_PROFIT_NAMES = ["매출총이익", "매출총이익(손실)"]
_OPERATING_INCOME_NAMES = ["영업이익", "영업이익(손실)"]
_TOTAL_LIABILITIES_NAMES = ["부채총계"]
_CASH_NAMES = ["현금및현금성자산"]

# Fallback chain of (bsns_year offset, reprt_code) tried in order, newest
# first — DART needs an exact report to query, there's no "most recent"
# endpoint. 11014=Q3, 11012=semi-annual(Q2), 11013=Q1, 11011=annual.
_REPORT_FALLBACK_CHAIN = [(0, "11014"), (0, "11012"), (0, "11013"), (-1, "11011")]


class DartUnavailableError(RuntimeError):
    """Raised when DART has no corp_code/usable data for a ticker — callers
    should fall back to mock rather than crash the research pipeline."""


def _corp_code_or_raise(ticker: str, api_key: str) -> str:
    if not api_key:
        raise DartUnavailableError("EDGE_DART_API_KEY is not set — cannot call DART.")
    try:
        corp_code = dart_client.get_corp_code(ticker, api_key)
    except dart_client.DartError as exc:
        raise DartUnavailableError(str(exc)) from exc
    if corp_code is None:
        raise DartUnavailableError(
            f"No DART corp_code found for {ticker!r} — Korean tickers are 6-digit exchange codes "
            "(e.g. '005930' for Samsung Electronics), not letter symbols."
        )
    return corp_code


class LiveDartFilingsProvider(FilingsProvider):
    def __init__(self, settings: Settings):
        self._settings = settings

    def get_recent_filings(self, ticker: str, limit: int = 5) -> list[FilingHighlight]:
        api_key = self._settings.dart_api_key
        corp_code = _corp_code_or_raise(ticker, api_key)

        # bgn_de/end_de must be passed explicitly — DART's docs say they
        # default to "today" when omitted, not "all time" (confirmed the
        # hard way: omitting them returned "no data found" for a company
        # that files constantly). A 1-year window is a reasonable "recent"
        # cutoff, well inside the freshness/relevance the research pipeline
        # actually needs.
        end_de = date.today()
        bgn_de = end_de - timedelta(days=365)
        try:
            data = dart_client.get_json(
                "list.json",
                {
                    "crtfc_key": api_key, "corp_code": corp_code, "page_count": str(min(limit, 100)),
                    "bgn_de": bgn_de.strftime("%Y%m%d"), "end_de": end_de.strftime("%Y%m%d"),
                    # Explicit, not relying on documented defaults — the
                    # bgn_de/end_de bug above was exactly that mistake once
                    # already. Newest-first is what "recent filings" means.
                    "sort": "date", "sort_mth": "desc",
                },
            )
        except dart_client.DartError as exc:
            raise DartUnavailableError(str(exc)) from exc

        results = []
        for item in data.get("list", []):
            rcept_no = item.get("rcept_no", "")
            report_nm = item.get("report_nm", "Filing")
            corp_name = item.get("corp_name", "")
            url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
            results.append(
                FilingHighlight(
                    ticker=ticker,
                    filing_type=report_nm,
                    title=f"{report_nm} — {corp_name}",
                    url_or_identifier=url,
                    filing_date=item.get("rcept_dt", ""),
                    highlights=[
                        (
                            f"DART filing '{report_nm}' by {corp_name}, received {item.get('rcept_dt', '')} "
                            f"(receipt no. {rcept_no}). This is filing metadata only — full-document "
                            "excerpt extraction isn't built yet, and the source document is in Korean.",
                            "neutral",
                        )
                    ],
                    is_mock=False,
                )
            )
            if len(results) >= limit:
                break
        return results


def _find_account(rows: list[dict], candidate_names: list[str], sj_div: str | None = None) -> dict | None:
    for name in candidate_names:
        for row in rows:
            if row.get("account_nm", "").strip() == name and (sj_div is None or row.get("sj_div") == sj_div):
                return row
    return None


def _amount(row: dict | None, key: str = "thstrm_amount") -> float:
    if not row:
        return 0.0
    raw = (row.get(key) or "0").replace(",", "").strip()
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _prior_amount(row: dict | None) -> float:
    """The same-period-prior-year comparison figure. Confirmed against a
    real DART response (a semi-annual report) that this is NOT always
    "frmtrm_amount": annual reports (reprt_code=11011) use that key, but
    quarterly/semi-annual reports (11012/11013/11014) don't have it at
    all — they use "frmtrm_q_amount" for the same-quarter-last-year figure
    instead. Those reports also carry a "frmtrm_add_amount" (prior
    cumulative year-to-date), which looks similar but is a different
    metric than "thstrm_amount" (this period only) and must not be used
    here — that mismatch was the actual cause of yoy_growth silently
    coming back as 0.0% for every non-annual Korean filing."""
    if not row:
        return 0.0
    if row.get("frmtrm_amount") is not None:
        return _amount(row, "frmtrm_amount")
    return _amount(row, "frmtrm_q_amount")


class LiveDartFundamentalsProvider(FundamentalsProvider):
    def __init__(self, settings: Settings):
        self._settings = settings

    def get_fundamentals(self, ticker: str) -> FundamentalsSnapshot:
        api_key = self._settings.dart_api_key
        corp_code = _corp_code_or_raise(ticker, api_key)

        this_year = date.today().year
        data, used_year, used_report = None, None, None
        for year_offset, reprt_code in _REPORT_FALLBACK_CHAIN:
            year = str(this_year + year_offset)
            try:
                candidate = dart_client.get_json(
                    "fnlttSinglAcntAll.json",
                    {"crtfc_key": api_key, "corp_code": corp_code, "bsns_year": year,
                     "reprt_code": reprt_code, "fs_div": "CFS"},
                )
            except dart_client.DartError:
                continue
            if candidate.get("list"):
                data, used_year, used_report = candidate, year, reprt_code
                break

        if data is None:
            raise DartUnavailableError(f"No DART financial statement data found for {ticker}.")

        rows = data["list"]
        revenue_row = _find_account(rows, _REVENUE_NAMES, sj_div="IS")
        if revenue_row is None:
            raise DartUnavailableError(f"No revenue line item found in DART financials for {ticker}.")

        revenue = _amount(revenue_row)
        prior_revenue = _prior_amount(revenue_row)
        revenue_yoy_growth = (revenue - prior_revenue) / prior_revenue if prior_revenue else 0.0

        gross_profit_row = _find_account(rows, _GROSS_PROFIT_NAMES, sj_div="IS")
        gross_margin = (_amount(gross_profit_row) / revenue) if gross_profit_row and revenue else 0.0
        prior_gross_profit = _prior_amount(gross_profit_row)
        gross_margin_prior_year = (prior_gross_profit / prior_revenue) if prior_gross_profit and prior_revenue else gross_margin

        op_income_row = _find_account(rows, _OPERATING_INCOME_NAMES, sj_div="IS")
        operating_margin = (_amount(op_income_row) / revenue) if op_income_row and revenue else 0.0

        cash_row = _find_account(rows, _CASH_NAMES, sj_div="BS")
        liabilities_row = _find_account(rows, _TOTAL_LIABILITIES_NAMES, sj_div="BS")

        return FundamentalsSnapshot(
            ticker=ticker,
            period_label=f"FY{used_year} report {used_report} (consolidated)",
            period_end_date=f"{used_year}-12-31",
            revenue=revenue,
            revenue_yoy_growth=revenue_yoy_growth,
            gross_margin=gross_margin,
            gross_margin_prior_year=gross_margin_prior_year,
            operating_margin=operating_margin,
            # DART's basic single-account-all endpoint doesn't reliably separate
            # capex from other investing cash flows, so free cash flow can't be
            # computed accurately here — left at 0.0 rather than mislabeling
            # operating cash flow as free cash flow.
            free_cash_flow=0.0,
            cash_and_equivalents=_amount(cash_row),
            total_debt=_amount(liabilities_row),
            # Shares outstanding isn't part of this financial-statement endpoint
            # (it's a separate DART ownership/equity disclosure) — not built yet.
            shares_outstanding=0.0,
            shares_outstanding_yoy_change=0.0,
            source_title=f"DART financial statement ({used_report}, FY{used_year}, consolidated)",
            source_url_or_identifier=f"https://dart.fss.or.kr/dsae001/main.do?corpCode={corp_code}",
            source_date=f"{used_year}-12-31",
            source_type="Regulatory Filing",
            is_mock=False,
        )
