"""Tests for LiveInsiderProvider. Uses a real Form 4 XML shape (structure
confirmed by fetching an actual NVIDIA Form 4 from SEC EDGAR before this
was written — see live_edgar.py's _BUY_CODE/_SELL_CODE comment)."""
from unittest.mock import patch

from src.config.settings import Settings
from src.providers.live_edgar import (
    LiveInsiderProvider,
    _parse_form4_transactions,
)

# Trimmed but structurally real Form 4 XML — same shape as the live
# document fetched from SEC EDGAR (NVIDIA, accession 0001310264-26-000008).
REAL_SHAPE_FORM4_XML = """<?xml version="1.0"?>
<ownershipDocument>
    <issuer>
        <issuerCik>0001045810</issuerCik>
        <issuerName>NVIDIA CORP</issuerName>
        <issuerTradingSymbol>NVDA</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerCik>0001310264</rptOwnerCik>
            <rptOwnerName>NORA JOHNSON SUZANNE M</rptOwnerName>
        </reportingOwnerId>
        <reportingOwnerRelationship>
            <isDirector>1</isDirector>
            <isOfficer>0</isOfficer>
            <isTenPercentOwner>0</isTenPercentOwner>
            <isOther>0</isOther>
        </reportingOwnerRelationship>
    </reportingOwner>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <transactionCoding>
                <transactionFormType>4</transactionFormType>
                <transactionCode>A</transactionCode>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares><value>1262</value></transactionShares>
                <transactionPricePerShare><value>0</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
        </nonDerivativeTransaction>
        <nonDerivativeTransaction>
            <transactionCoding>
                <transactionFormType>4</transactionFormType>
                <transactionCode>S</transactionCode>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares><value>500</value></transactionShares>
                <transactionPricePerShare><value>180.50</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
        </nonDerivativeTransaction>
        <nonDerivativeTransaction>
            <transactionCoding>
                <transactionFormType>4</transactionFormType>
                <transactionCode>P</transactionCode>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares><value>1000</value></transactionShares>
                <transactionPricePerShare><value>175.25</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>
"""


def test_parse_form4_excludes_grants_keeps_only_buy_sell():
    """Code "A" (grant/award) must be excluded — only P (buy) and S (sell)
    represent a genuine conviction signal."""
    txns = _parse_form4_transactions(REAL_SHAPE_FORM4_XML, "NVDA", "2026-08-10", "https://example.com/form4")
    assert len(txns) == 2  # the "A" grant is excluded, only S and P remain
    codes = {t.transaction_type for t in txns}
    assert codes == {"Sell", "Buy"}


def test_parse_form4_extracts_insider_name_and_role():
    txns = _parse_form4_transactions(REAL_SHAPE_FORM4_XML, "NVDA", "2026-08-10", "https://example.com/form4")
    assert all(t.insider_name == "NORA JOHNSON SUZANNE M" for t in txns)
    assert all(t.role == "Director" for t in txns)


def test_parse_form4_computes_value_usd_correctly():
    txns = _parse_form4_transactions(REAL_SHAPE_FORM4_XML, "NVDA", "2026-08-10", "https://example.com/form4")
    sell = next(t for t in txns if t.transaction_type == "Sell")
    buy = next(t for t in txns if t.transaction_type == "Buy")
    assert sell.shares == 500
    assert sell.value_usd == 500 * 180.50
    assert buy.shares == 1000
    assert buy.value_usd == 1000 * 175.25


def test_parse_form4_handles_malformed_xml_gracefully():
    assert _parse_form4_transactions("not xml at all", "NVDA", "2026-08-10", "url") == []


def test_parse_form4_handles_missing_reporting_owner():
    assert _parse_form4_transactions("<ownershipDocument></ownershipDocument>", "NVDA", "2026-08-10", "url") == []


def test_live_insider_provider_filters_to_form_4_and_respects_limit():
    fake_submissions = {
        "filings": {
            "recent": {
                "form": ["8-K", "4", "4", "10-Q"],
                "filingDate": ["2026-08-01", "2026-08-02", "2026-08-03", "2026-08-04"],
                "accessionNumber": ["0001-26-1", "0001-26-2", "0001-26-3", "0001-26-4"],
                "primaryDocument": ["8k.htm", "xslF345X06/form4a.xml", "xslF345X06/form4b.xml", "10q.htm"],
            }
        }
    }
    settings = Settings()
    provider = LiveInsiderProvider(settings)
    with patch("src.providers.live_edgar.edgar_client.get_cik_for_ticker", return_value=12345):
        with patch("src.providers.live_edgar.edgar_client.get_submissions", return_value=fake_submissions):
            with patch("src.providers.live_edgar.edgar_client.get_document_text", return_value=REAL_SHAPE_FORM4_XML):
                txns = provider.get_insider_transactions("NVDA", limit=3)

    # 2 real Form 4 filings, each yielding 2 buy/sell txns = 4 available, capped at limit=3
    assert len(txns) == 3
    assert all(t.is_mock is False for t in txns)


def test_live_insider_provider_fetches_raw_xml_not_xsl_rendered_html():
    """Regression test: primaryDocument from the submissions feed points at
    SEC's XSLT-rendered HTML view (an "xslF345X06/" subfolder, despite the
    .xml extension), which returns HTML, not parseable XML. The raw XML
    lives at the same filename one directory up. Confirmed against a real
    live NVIDIA Form 4 before this was fixed."""
    fake_submissions = {
        "filings": {
            "recent": {
                "form": ["4"],
                "filingDate": ["2026-08-02"],
                "accessionNumber": ["0001310264-26-000008"],
                "primaryDocument": ["xslF345X06/wk-form4_1786569187.xml"],
            }
        }
    }
    settings = Settings()
    provider = LiveInsiderProvider(settings)
    fetched_urls = []

    def fake_get_document_text(url, ua):
        fetched_urls.append(url)
        return REAL_SHAPE_FORM4_XML

    with patch("src.providers.live_edgar.edgar_client.get_cik_for_ticker", return_value=1045810):
        with patch("src.providers.live_edgar.edgar_client.get_submissions", return_value=fake_submissions):
            with patch("src.providers.live_edgar.edgar_client.get_document_text", side_effect=fake_get_document_text):
                txns = provider.get_insider_transactions("NVDA", limit=5)

    assert len(fetched_urls) == 1
    assert "xslF345X06" not in fetched_urls[0]
    assert fetched_urls[0].endswith("wk-form4_1786569187.xml")
    # the display URL shown to the user should still be the nicer rendered one
    assert all("xslF345X06" in t.url_or_identifier for t in txns)
    assert len(txns) == 2
