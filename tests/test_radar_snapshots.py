"""Tests for src/radar/snapshots.py. All provider calls are mocked — no
real network access from the test suite."""
from unittest.mock import patch

from src.config.settings import Settings
from src.providers.finnhub_client import FinnhubError
from src.providers.live_edgar import InsiderTransaction, NewsItem
from src.providers.live_price import PriceUnavailableError
from src.radar import snapshots


def test_load_tracked_tickers_returns_empty_list_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshots, "TRACKED_TICKERS_PATH", tmp_path / "tracked_tickers.json")
    assert snapshots.load_tracked_tickers() == []


def test_load_tracked_tickers_reads_themed_schema(tmp_path, monkeypatch):
    path = tmp_path / "tracked_tickers.json"
    path.write_text(
        '{"_readme": "x", "themes": {"Memory": ["mu", "SNDK"], "Space": ["RKLB"]}}'
    )
    monkeypatch.setattr(snapshots, "TRACKED_TICKERS_PATH", path)
    assert snapshots.load_tracked_tickers() == ["MU", "RKLB", "SNDK"]


def test_load_tracked_tickers_tolerates_malformed_file(tmp_path, monkeypatch):
    path = tmp_path / "tracked_tickers.json"
    path.write_text("not valid json {{{")
    monkeypatch.setattr(snapshots, "TRACKED_TICKERS_PATH", path)
    assert snapshots.load_tracked_tickers() == []


def test_load_ticker_themes_maps_ticker_to_theme_name(tmp_path, monkeypatch):
    path = tmp_path / "tracked_tickers.json"
    path.write_text(
        '{"_readme": "x", "themes": {"Memory": ["MU", "SNDK"], "Space": ["RKLB"], "Humanoid Robotics": []}}'
    )
    monkeypatch.setattr(snapshots, "TRACKED_TICKERS_PATH", path)
    themes = snapshots.load_ticker_themes()
    assert themes["MU"] == "Memory"
    assert themes["SNDK"] == "Memory"
    assert themes["RKLB"] == "Space"
    assert "Humanoid Robotics" not in themes.values()  # empty theme contributes no mappings


def _fake_price_ctx(ticker):
    from src.providers.base import PriceContext

    return PriceContext(
        ticker=ticker, last_price=100.0, fifty_two_week_low=80.0, fifty_two_week_high=120.0,
        pct_change_3m=0.05, pct_change_1y=0.20, avg_volume_30d=1_000_000.0,
        trend_note="test", as_of_date="2026-08-15", is_mock=False,
    )


def _fake_valuation_ctx(ticker):
    from src.providers.base import ValuationContext

    return ValuationContext(
        ticker=ticker, market_cap=1_000_000_000.0, ev_to_revenue=5.0, ev_to_ebitda=15.0,
        price_to_sales=4.0, peer_median_ev_to_revenue=None, as_of_date="2026-08-15", is_mock=False,
    )


def test_refresh_snapshots_writes_all_domains(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshots, "SNAPSHOTS_PATH", tmp_path / "ticker_snapshots.json")
    settings = Settings(finnhub_api_key="fake-key")

    fake_txn = InsiderTransaction(
        ticker="NVDA", insider_name="Test Person", role="Director", transaction_type="Sell",
        shares=100.0, value_usd=10000.0, filing_date="2026-08-01", url_or_identifier="https://example.com", is_mock=False,
    )
    fake_news = NewsItem(
        ticker="NVDA", title="Test news", url_or_identifier="https://example.com", published_date="2026-08-01",
        source_type="Press Release", snippet="test", tag="neutral", is_mock=False,
    )

    fake_recommendation = {"symbol": "NVDA", "period": "2026-08-01", "strongBuy": 10, "buy": 20, "hold": 5, "sell": 1, "strongSell": 0}

    with patch("src.radar.snapshots.LivePriceProvider.get_price_context", return_value=_fake_price_ctx("NVDA")):
        with patch("src.radar.snapshots.LivePriceProvider.get_valuation_context", return_value=_fake_valuation_ctx("NVDA")):
            with patch("src.radar.snapshots.LiveInsiderProvider.get_insider_transactions", return_value=[fake_txn]):
                with patch("src.radar.snapshots.LiveNewsProvider.get_recent_news", return_value=[fake_news]):
                    with patch("src.radar.snapshots.finnhub_client.get_quote", return_value={"c": 100.0, "dp": 1.5}):
                        with patch("src.radar.snapshots.finnhub_client.get_recommendation_trends", return_value=[fake_recommendation]):
                            summary = snapshots.refresh_snapshots(["NVDA"], settings)

    assert summary["tickers_refreshed"] == 1
    assert summary["tickers_failed"] == 0

    saved = snapshots.load_snapshots()
    assert "NVDA" in saved
    assert saved["NVDA"]["price"]["last_price"] == 100.0
    assert saved["NVDA"]["valuation"]["market_cap"] == 1_000_000_000.0
    assert len(saved["NVDA"]["insider_transactions"]) == 1
    assert len(saved["NVDA"]["news"]) == 1
    assert saved["NVDA"]["pct_change_1d"] == 1.5
    assert saved["NVDA"]["unusual_move"] is False
    assert saved["NVDA"]["analyst_recommendations"] == fake_recommendation


def test_refresh_snapshots_flags_notable_and_watch_trigger_moves(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshots, "SNAPSHOTS_PATH", tmp_path / "ticker_snapshots.json")
    settings = Settings(finnhub_api_key="fake-key")

    with patch("src.radar.snapshots.LivePriceProvider.get_price_context", side_effect=PriceUnavailableError("x")):
        with patch("src.radar.snapshots.LivePriceProvider.get_valuation_context", side_effect=PriceUnavailableError("x")):
            with patch("src.radar.snapshots.LiveInsiderProvider.get_insider_transactions", return_value=[]):
                with patch("src.radar.snapshots.LiveNewsProvider.get_recent_news", return_value=[]):
                    with patch("src.radar.snapshots.finnhub_client.get_recommendation_trends", return_value=[]):
                        with patch("src.radar.snapshots.finnhub_client.get_quote", return_value={"c": 50.0, "dp": 4.2}):
                            snapshots.refresh_snapshots(["NOTABLE"], settings)
                        with patch("src.radar.snapshots.finnhub_client.get_quote", return_value={"c": 50.0, "dp": -8.1}):
                            snapshots.refresh_snapshots(["TRIGGER"], settings)
                        with patch("src.radar.snapshots.finnhub_client.get_quote", return_value={"c": 50.0, "dp": 0.4}):
                            snapshots.refresh_snapshots(["QUIET"], settings)

    saved = snapshots.load_snapshots()
    assert saved["NOTABLE"]["unusual_move"] is True and saved["NOTABLE"]["watch_trigger_move"] is False
    assert saved["TRIGGER"]["unusual_move"] is True and saved["TRIGGER"]["watch_trigger_move"] is True
    assert saved["QUIET"]["unusual_move"] is False and saved["QUIET"]["watch_trigger_move"] is False


def test_refresh_snapshots_one_domain_failing_doesnt_block_others(tmp_path, monkeypatch):
    """If Finnhub isn't configured, insider/news should still populate —
    each domain is independently best-effort."""
    monkeypatch.setattr(snapshots, "SNAPSHOTS_PATH", tmp_path / "ticker_snapshots.json")
    settings = Settings(finnhub_api_key="")  # no Finnhub key
    fake_txn = InsiderTransaction(
        ticker="NVDA", insider_name="Test Person", role="Director", transaction_type="Buy",
        shares=50.0, value_usd=5000.0, filing_date="2026-08-01", url_or_identifier="https://example.com", is_mock=False,
    )

    with patch("src.radar.snapshots.LiveInsiderProvider.get_insider_transactions", return_value=[fake_txn]):
        with patch("src.radar.snapshots.LiveNewsProvider.get_recent_news", return_value=[]):
            summary = snapshots.refresh_snapshots(["NVDA"], settings)

    saved = snapshots.load_snapshots()
    assert saved["NVDA"]["price"] is None
    assert any("price" in e for e in saved["NVDA"]["errors"])
    assert len(saved["NVDA"]["insider_transactions"]) == 1
    assert summary["tickers_refreshed"] == 1  # still counted refreshed since insiders succeeded


def test_refresh_snapshots_respects_max_tickers_bound(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshots, "SNAPSHOTS_PATH", tmp_path / "ticker_snapshots.json")
    settings = Settings(finnhub_api_key="fake-key")

    with patch("src.radar.snapshots.LivePriceProvider.get_price_context", side_effect=PriceUnavailableError("x")):
        with patch("src.radar.snapshots.LivePriceProvider.get_valuation_context", side_effect=PriceUnavailableError("x")):
            with patch("src.radar.snapshots.LiveInsiderProvider.get_insider_transactions", return_value=[]):
                with patch("src.radar.snapshots.LiveNewsProvider.get_recent_news", return_value=[]):
                    with patch("src.radar.snapshots.finnhub_client.get_quote", return_value={"c": 0, "dp": None}):
                        with patch("src.radar.snapshots.finnhub_client.get_recommendation_trends", return_value=[]):
                            summary = snapshots.refresh_snapshots(
                                ["A", "B", "C", "D", "E"], settings, max_tickers=2
                            )

    assert summary["tickers_considered"] == 5
    assert summary["tickers_attempted"] == 2


def test_refresh_snapshots_merges_into_existing_store(tmp_path, monkeypatch):
    path = tmp_path / "ticker_snapshots.json"
    monkeypatch.setattr(snapshots, "SNAPSHOTS_PATH", path)
    settings = Settings(finnhub_api_key="")

    with patch("src.radar.snapshots.LiveInsiderProvider.get_insider_transactions", return_value=[]):
        with patch("src.radar.snapshots.LiveNewsProvider.get_recent_news", return_value=[]):
            snapshots.refresh_snapshots(["AAA"], settings)
            snapshots.refresh_snapshots(["BBB"], settings)

    saved = snapshots.load_snapshots()
    assert "AAA" in saved and "BBB" in saved  # second call didn't clobber the first
