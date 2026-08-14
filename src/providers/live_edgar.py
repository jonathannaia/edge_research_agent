"""Live SEC EDGAR provider — free, keyless (just a compliant User-Agent).

Covers filings and fundamentals for US-listed tickers. See registry.py for
how this is wired in behind EDGE_DATA_MODE=live, and README section 4 for
what other domains (price, transcripts, non-US filings) still need a
live provider.

Honesty note on filing "highlights": this reads filing METADATA (form type,
date, accession number, a direct SEC.gov URL) — it does not fetch and parse
full filing document text. Highlight excerpts are therefore factual
restatements of that metadata, not quotes extracted from inside the filing.
Real full-document excerpt extraction is real future work; it was
deliberately not attempted here rather than risk generating plausible-
sounding "highlights" that aren't actually grounded in the filing text —
that would undermine the app's core no-hallucination guarantee even though
the citation guardrail itself wouldn't catch it (it checks that a claim has
a source, not that the claim is true).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.config.settings import Settings
from src.providers import edgar_client
from src.providers.base import (
    FilingHighlight,
    FilingsProvider,
    FundamentalsProvider,
    FundamentalsSnapshot,
)

FILING_FORMS_OF_INTEREST = {"10-K", "10-Q", "8-K"}

# XBRL us-gaap tags, in preference order, for each fundamentals field —
# different companies/industries report under slightly different concepts,
# so each field tries a short list rather than a single hardcoded tag.
_REVENUE_TAGS = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"]
_GROSS_PROFIT_TAGS = ["GrossProfit"]
_OPERATING_INCOME_TAGS = ["OperatingIncomeLoss"]
_CASH_TAGS = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
]
_DEBT_TAGS = ["LongTermDebtNoncurrent", "LongTermDebt", "DebtLongtermAndShorttermCombinedAmount"]
_SHARES_TAGS = ["CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding"]
_OPERATING_CASH_FLOW_TAGS = ["NetCashProvidedByUsedInOperatingActivities"]
_CAPEX_TAGS = ["PaymentsToAcquirePropertyPlantAndEquipment"]


class EdgarUnavailableError(RuntimeError):
    """Raised when EDGAR has no CIK/usable data for a ticker — callers
    should treat this as "can't get live data for this one" and fall back
    to mock data rather than crash the whole research pipeline."""


def _cik_or_raise(ticker: str, user_agent: str) -> int:
    cik = edgar_client.get_cik_for_ticker(ticker, user_agent)
    if cik is None:
        raise EdgarUnavailableError(
            f"No SEC EDGAR CIK found for ticker {ticker!r} — not a US-listed filer, or the ticker is wrong."
        )
    return cik


def _latest_value_for_tags(facts: dict, tags: list[str], unit: str = "USD") -> tuple[Optional[dict], Optional[str]]:
    """Returns (best datapoint, which tag matched) for the most recent
    10-Q/10-K-reported value across a list of candidate XBRL tags, trying
    each tag in order until one has data."""
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    for tag in tags:
        concept = us_gaap.get(tag)
        if not concept:
            continue
        points = [p for p in concept.get("units", {}).get(unit, []) if p.get("form") in ("10-Q", "10-K") and p.get("end")]
        if not points:
            continue
        points.sort(key=lambda p: p["end"], reverse=True)
        return points[0], tag
    return None, None


def _prior_year_value(facts: dict, tag: str, current_end: str, unit: str = "USD") -> Optional[float]:
    """Best-effort match for the same metric ~1 year before current_end,
    within a +/-25 day window (covers fiscal-year-end drift). Returns None
    if nothing lines up closely enough — callers must treat that as "growth
    unknown", not "growth is zero"."""
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    concept = us_gaap.get(tag)
    if not concept:
        return None
    try:
        target = datetime.fromisoformat(current_end).replace(year=datetime.fromisoformat(current_end).year - 1)
    except ValueError:
        return None

    best_val, best_diff = None, None
    for p in concept.get("units", {}).get(unit, []):
        if p.get("form") not in ("10-Q", "10-K") or not p.get("end"):
            continue
        try:
            end = datetime.fromisoformat(p["end"])
        except ValueError:
            continue
        diff = abs((target - end).days)
        if diff <= 25 and (best_diff is None or diff < best_diff):
            best_val, best_diff = p["val"], diff
    return best_val


class LiveFilingsProvider(FilingsProvider):
    def __init__(self, settings: Settings):
        self._settings = settings

    def get_recent_filings(self, ticker: str, limit: int = 5) -> list[FilingHighlight]:
        ua = self._settings.sec_user_agent
        cik = _cik_or_raise(ticker, ua)
        submissions = edgar_client.get_submissions(cik, ua)
        recent = submissions.get("filings", {}).get("recent", {})

        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        docs = recent.get("primaryDocument", [])
        descriptions = recent.get("primaryDocDescription", [])

        results: list[FilingHighlight] = []
        for i, form in enumerate(forms):
            if form not in FILING_FORMS_OF_INTEREST:
                continue
            url = edgar_client.filing_document_url(cik, accessions[i], docs[i])
            desc = descriptions[i] if i < len(descriptions) and descriptions[i] else form
            results.append(
                FilingHighlight(
                    ticker=ticker.upper(),
                    filing_type=form,
                    title=f"{form} filed {dates[i]} — {desc}",
                    url_or_identifier=url,
                    filing_date=dates[i],
                    highlights=[
                        (
                            f"SEC EDGAR {form} filed {dates[i]} (accession {accessions[i]}). This is "
                            "filing metadata only — full-document excerpt extraction isn't built yet; "
                            "open the source to read the filing.",
                            "neutral",
                        )
                    ],
                    is_mock=False,
                )
            )
            if len(results) >= limit:
                break
        return results


class LiveFundamentalsProvider(FundamentalsProvider):
    def __init__(self, settings: Settings):
        self._settings = settings

    def get_fundamentals(self, ticker: str) -> FundamentalsSnapshot:
        ua = self._settings.sec_user_agent
        cik = _cik_or_raise(ticker, ua)
        facts = edgar_client.get_company_facts(cik, ua)

        revenue_point, revenue_tag = _latest_value_for_tags(facts, _REVENUE_TAGS)
        if revenue_point is None:
            raise EdgarUnavailableError(f"No XBRL revenue data found for {ticker} on SEC EDGAR.")

        period_end = revenue_point["end"]
        revenue = float(revenue_point["val"])
        prior_revenue = _prior_year_value(facts, revenue_tag, period_end)
        revenue_yoy_growth = ((revenue - prior_revenue) / prior_revenue) if prior_revenue else 0.0

        gross_profit_point, gp_tag = _latest_value_for_tags(facts, _GROSS_PROFIT_TAGS)
        gross_margin = (gross_profit_point["val"] / revenue) if gross_profit_point and revenue else 0.0
        prior_gross_profit = _prior_year_value(facts, gp_tag, period_end) if gp_tag else None
        gross_margin_prior_year = (
            (prior_gross_profit / prior_revenue) if (prior_gross_profit and prior_revenue) else gross_margin
        )

        op_income_point, _ = _latest_value_for_tags(facts, _OPERATING_INCOME_TAGS)
        operating_margin = (op_income_point["val"] / revenue) if op_income_point and revenue else 0.0

        ocf_point, _ = _latest_value_for_tags(facts, _OPERATING_CASH_FLOW_TAGS)
        capex_point, _ = _latest_value_for_tags(facts, _CAPEX_TAGS)
        free_cash_flow = (
            (ocf_point["val"] - (capex_point["val"] if capex_point else 0.0)) if ocf_point else 0.0
        )

        cash_point, _ = _latest_value_for_tags(facts, _CASH_TAGS)
        debt_point, _ = _latest_value_for_tags(facts, _DEBT_TAGS)
        shares_point, shares_tag = _latest_value_for_tags(facts, _SHARES_TAGS, unit="shares")
        shares_outstanding = float(shares_point["val"]) if shares_point else 0.0
        prior_shares = _prior_year_value(facts, shares_tag, period_end, unit="shares") if shares_tag else None
        shares_outstanding_yoy_change = (
            (shares_outstanding - prior_shares) / prior_shares if prior_shares else 0.0
        )

        return FundamentalsSnapshot(
            ticker=ticker.upper(),
            period_label=f"{revenue_point.get('fp', '')} FY{revenue_point.get('fy', '')} ({revenue_point.get('form')})",
            period_end_date=period_end,
            revenue=revenue,
            revenue_yoy_growth=revenue_yoy_growth,
            gross_margin=gross_margin,
            gross_margin_prior_year=gross_margin_prior_year,
            operating_margin=operating_margin,
            free_cash_flow=free_cash_flow,
            cash_and_equivalents=float(cash_point["val"]) if cash_point else 0.0,
            total_debt=float(debt_point["val"]) if debt_point else 0.0,
            shares_outstanding=shares_outstanding,
            shares_outstanding_yoy_change=shares_outstanding_yoy_change,
            source_title=f"SEC EDGAR XBRL company facts — {revenue_tag} ({revenue_point.get('form')} filed {revenue_point.get('filed')})",
            source_url_or_identifier=edgar_client.filing_index_url(cik, revenue_point.get("accn", "")),
            source_date=period_end,
            source_type="Regulatory Filing",
            is_mock=False,
        )
