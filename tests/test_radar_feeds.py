"""Tests for src/radar/feeds.py. Network calls are mocked — no real
requests to sec.gov, federalregister.gov, or any RSS source from the test
suite."""
import json
from unittest.mock import MagicMock, patch

from src.providers.edgar_client import EdgarError
from src.radar import feeds
from src.radar.models import Niche

FAKE_FEDERAL_REGISTER_RESPONSE = {
    "count": 1,
    "results": [
        {
            "title": "Streamlining Export Controls for Drone Exports",
            "publication_date": "2026-08-14",
            "html_url": "https://www.federalregister.gov/documents/2026/08/14/2026-16628/streamlining-export-controls-for-drone-exports",
            "type": "Rule",
            "abstract": "The Bureau of Industry and Security (BIS) is easing export controls on certain UAVs...",
        }
    ],
}

FAKE_SEARCH_RESPONSE = {
    "hits": {
        "total": {"value": 2},
        "hits": [
            {
                "_id": "0001213900-26-089450:ea030173001ex99-1.htm",
                "_source": {
                    "ciks": ["0001854368"],
                    "display_names": ["Digi Power X Inc.  (DGXX)  (CIK 0001854368)"],
                    "form": "8-K",
                    "file_date": "2026-08-14",
                    "adsh": "0001213900-26-089450",
                },
            },
            {
                "_id": "0000002488-26-000121:amdq22026earningsslidesf.htm",
                "_source": {
                    "ciks": ["0000002488"],
                    "display_names": ["ADVANCED MICRO DEVICES INC  (AMD)  (CIK 0000002488)"],
                    "form": "8-K",
                    "file_date": "2026-08-04",
                    "adsh": "0000002488-26-000121",
                },
            },
        ],
    }
}


def test_fetch_edgar_search_entries_parses_real_shape():
    with patch("src.radar.feeds.edgar_client.full_text_search", return_value=FAKE_SEARCH_RESPONSE):
        entries, err = feeds.fetch_edgar_search_entries()

    assert err is None
    assert len(entries) == 2
    assert "AMD" in entries[1]["title"] or "ADVANCED MICRO DEVICES" in entries[1]["title"]
    assert entries[0]["link"].startswith("https://www.sec.gov/Archives/edgar/data/1854368/")
    assert entries[0]["published_epoch"] is not None


def test_fetch_edgar_search_entries_caps_at_max_results():
    many_hits = {
        "hits": {
            "total": {"value": 50},
            "hits": [
                {
                    "_id": f"0001-26-{i:06d}:doc{i}.htm",
                    "_source": {"ciks": ["0000000001"], "display_names": [f"Company {i}"], "form": "8-K", "file_date": "2026-08-14", "adsh": f"0001-26-{i:06d}"},
                }
                for i in range(50)
            ],
        }
    }
    with patch("src.radar.feeds.edgar_client.full_text_search", return_value=many_hits):
        entries, err = feeds.fetch_edgar_search_entries()

    assert len(entries) == feeds.EDGAR_SEARCH_MAX_RESULTS


def test_fetch_edgar_search_entries_returns_error_not_raises_on_failure():
    with patch("src.radar.feeds.edgar_client.full_text_search", side_effect=EdgarError("network down")):
        entries, err = feeds.fetch_edgar_search_entries()

    assert entries == []
    assert err is not None
    assert "network down" in err


def test_fetch_all_includes_edgar_search_results():
    import urllib.error

    with patch("src.radar.feeds.fetch_feed", return_value=([], None)):  # skip real RSS feeds
        with patch("src.radar.feeds.edgar_client.full_text_search", return_value=FAKE_SEARCH_RESPONSE):
            with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("network disabled in test")):
                items, errors = feeds.fetch_all(feeds=[])  # empty RSS feed list, EDGAR search still runs

    edgar_items = [item for item in items if item[0].name == feeds.EDGAR_SEARCH_FEED.name]
    assert len(edgar_items) == 2
    assert all(feed.niche == Niche.AI_BUILDOUT.value for feed, _ in edgar_items)


def _mock_urlopen(json_body: dict):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(json_body).encode()
    mock_resp.__enter__.return_value = mock_resp
    return mock_resp


def test_fetch_federal_register_entries_parses_real_shape():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(FAKE_FEDERAL_REGISTER_RESPONSE)):
        entries, err = feeds.fetch_federal_register_entries()

    assert err is None
    assert len(entries) == 1
    assert "Export Controls" in entries[0]["title"]
    assert entries[0]["link"] == "https://www.federalregister.gov/documents/2026/08/14/2026-16628/streamlining-export-controls-for-drone-exports"
    assert entries[0]["published_epoch"] is not None
    assert "Bureau of Industry and Security" in entries[0]["summary"]


def test_fetch_federal_register_entries_falls_back_to_title_when_no_abstract():
    response = {"results": [{"title": "Notice Only", "publication_date": "2026-08-14", "html_url": "https://example.com", "type": "Notice"}]}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(response)):
        entries, err = feeds.fetch_federal_register_entries()

    assert err is None
    assert entries[0]["summary"] == "Notice Only"


def test_fetch_federal_register_entries_returns_error_not_raises_on_failure():
    import urllib.error

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("network down")):
        entries, err = feeds.fetch_federal_register_entries()

    assert entries == []
    assert err is not None
    assert "network down" in err


def test_fetch_all_includes_federal_register_results():
    with patch("src.radar.feeds.fetch_feed", return_value=([], None)):
        with patch("src.radar.feeds.edgar_client.full_text_search", return_value={"hits": {"hits": []}}):
            with patch("urllib.request.urlopen", return_value=_mock_urlopen(FAKE_FEDERAL_REGISTER_RESPONSE)):
                items, errors = feeds.fetch_all(feeds=[])

    fr_items = [item for item in items if item[0].name == feeds.FEDERAL_REGISTER_FEED.name]
    assert len(fr_items) == 1
    assert fr_items[0][0].niche == Niche.MACRO.value
    assert errors == []
