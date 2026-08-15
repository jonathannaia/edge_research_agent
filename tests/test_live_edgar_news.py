"""Tests for LiveNewsProvider. Uses the real "items" field shape confirmed
against a live NVIDIA submissions response before this was written."""
from unittest.mock import patch

from src.config.settings import Settings
from src.providers.live_edgar import LiveNewsProvider

FAKE_SUBMISSIONS = {
    "filings": {
        "recent": {
            "form": ["8-K", "8-K", "8-K", "4", "10-Q"],
            "filingDate": ["2026-07-02", "2026-06-30", "2026-06-18", "2026-06-20", "2026-06-15"],
            "accessionNumber": ["0001-26-1", "0001-26-2", "0001-26-3", "0001-26-4", "0001-26-5"],
            "primaryDocument": ["8k1.htm", "8k2.htm", "8k3.htm", "form4.xml", "10q.htm"],
            "items": ["5.02", "5.07", "8.01,9.01", "", ""],
        }
    }
}


def test_live_news_filters_to_newsworthy_8k_items():
    settings = Settings()
    provider = LiveNewsProvider(settings)
    with patch("src.providers.live_edgar.edgar_client.get_cik_for_ticker", return_value=12345):
        with patch("src.providers.live_edgar.edgar_client.get_submissions", return_value=FAKE_SUBMISSIONS):
            news = provider.get_recent_news("TEST", limit=5)

    # "5.02" (executive change) and "8.01" (other events) are newsworthy;
    # "5.07" (vote results, procedural only) is not, and Form 4/10-Q aren't 8-Ks at all.
    assert len(news) == 2
    dates = {n.published_date for n in news}
    assert dates == {"2026-07-02", "2026-06-18"}
    assert all(n.is_mock is False for n in news)


def test_live_news_respects_limit():
    settings = Settings()
    provider = LiveNewsProvider(settings)
    with patch("src.providers.live_edgar.edgar_client.get_cik_for_ticker", return_value=12345):
        with patch("src.providers.live_edgar.edgar_client.get_submissions", return_value=FAKE_SUBMISSIONS):
            news = provider.get_recent_news("TEST", limit=1)

    assert len(news) == 1


def test_live_news_title_includes_item_labels():
    settings = Settings()
    provider = LiveNewsProvider(settings)
    with patch("src.providers.live_edgar.edgar_client.get_cik_for_ticker", return_value=12345):
        with patch("src.providers.live_edgar.edgar_client.get_submissions", return_value=FAKE_SUBMISSIONS):
            news = provider.get_recent_news("TEST", limit=5)

    exec_change = next(n for n in news if n.published_date == "2026-07-02")
    assert "Departure/Election" in exec_change.title
