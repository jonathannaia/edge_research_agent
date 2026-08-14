"""Tests for src/radar/feeds.py. Network calls are mocked — no real
requests to sec.gov or any RSS source from the test suite."""
from unittest.mock import patch

from src.providers.edgar_client import EdgarError
from src.radar import feeds
from src.radar.models import Niche

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
    with patch("src.radar.feeds.fetch_feed", return_value=([], None)):  # skip real RSS feeds
        with patch("src.radar.feeds.edgar_client.full_text_search", return_value=FAKE_SEARCH_RESPONSE):
            items, errors = feeds.fetch_all(feeds=[])  # empty RSS feed list, EDGAR search still runs

    assert len(items) == 2
    assert all(feed.niche == Niche.AI_BUILDOUT.value for feed, _ in items)
    assert errors == []
