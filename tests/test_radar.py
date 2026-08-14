"""Radar tests. The LLM tagger is always mocked here — the test suite must
never make a real Anthropic API call (cost, determinism, CI without a key)."""
from unittest.mock import patch

from src.radar import scan, store
from src.radar.keyword_filter import is_plausibly_relevant
from src.radar.llm_tagger import TaggingResult
from src.radar.models import Niche, RadarFinding, ScanRunRecord, TickerTag


# --- keyword_filter ---

def test_keyword_filter_matches_niche_keyword():
    assert is_plausibly_relevant(Niche.AI_BUILDOUT.value, "Hyperscaler announces new data center", "") is True


def test_keyword_filter_rejects_off_topic_item():
    assert is_plausibly_relevant(Niche.AI_BUILDOUT.value, "Local bakery wins award", "") is False


def test_keyword_filter_matches_in_summary_not_just_title():
    assert is_plausibly_relevant(Niche.MACRO.value, "Central bank statement", "The Federal Reserve signaled a rate cut.") is True


def test_keyword_filter_unknown_niche_never_matches():
    assert is_plausibly_relevant("Not A Real Niche", "GPU data center rate hike", "") is False


# --- store: dedup + round trip ---

def test_store_round_trip_and_dedup(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "FINDINGS_PATH", tmp_path / "radar_findings.json")
    monkeypatch.setattr(store, "STATE_PATH", tmp_path / "radar_state.json")

    finding = RadarFinding(
        niche=Niche.SPACE.value,
        headline="Rocket launch succeeds",
        summary="A rocket launched successfully.",
        source_url="https://example.com/article-1",
        source_name="Test Feed",
        source_type="Press Release",
        published_at="2026-08-01T00:00:00+00:00",
        retrieved_at="2026-08-01T01:00:00+00:00",
        tickers=[TickerTag(ticker="ABC", company_name="Abc Corp", jurisdiction="United States")],
    )
    run_record = ScanRunRecord(
        started_at="2026-08-01T00:59:00+00:00", finished_at="2026-08-01T01:00:00+00:00",
        status="ok", feeds_checked=1, items_seen=1, items_after_keyword_filter=1,
        items_sent_to_llm=1, items_saved=1, items_rejected_by_guardrail=0,
    )

    store.save_scan_results([finding], run_record)

    loaded = store.load_findings()
    assert len(loaded) == 1
    assert loaded[0].headline == "Rocket launch succeeds"
    assert loaded[0].tickers[0].ticker == "ABC"
    assert loaded[0].url_hash == store.url_hash("https://example.com/article-1")

    seen = store.load_seen_hashes()
    assert store.url_hash("https://example.com/article-1") in seen

    history = store.load_run_history()
    assert len(history) == 1
    assert history[0].items_saved == 1


def test_store_bounds_findings_to_max(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "FINDINGS_PATH", tmp_path / "radar_findings.json")
    monkeypatch.setattr(store, "STATE_PATH", tmp_path / "radar_state.json")
    monkeypatch.setattr(store, "MAX_FINDINGS", 2)

    for i in range(5):
        finding = RadarFinding(
            niche=Niche.MACRO.value, headline=f"Item {i}", summary="Summary.",
            source_url=f"https://example.com/{i}", source_name="Feed", source_type="Press Release",
            published_at="", retrieved_at=f"2026-08-01T0{i}:00:00+00:00",
        )
        run_record = ScanRunRecord(
            started_at="x", finished_at="y", status="ok", feeds_checked=1, items_seen=1,
            items_after_keyword_filter=1, items_sent_to_llm=1, items_saved=1, items_rejected_by_guardrail=0,
        )
        store.save_scan_results([finding], run_record)

    assert len(store.load_findings()) == 2


# --- scan orchestration: guardrail rejection path (LLM mocked) ---

def _fake_feed():
    from src.radar.feeds import Feed
    return Feed("Fake Macro Feed", "https://example.com/rss", Niche.MACRO.value, "Press Release")


def test_scan_rejects_finding_with_advice_language(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "FINDINGS_PATH", tmp_path / "radar_findings.json")
    monkeypatch.setattr(store, "STATE_PATH", tmp_path / "radar_state.json")

    feed = _fake_feed()
    entry = {"title": "Fed signals rate cut", "link": "https://example.com/fed-story", "summary": "Central bank hints at policy shift.", "published": ""}

    with patch("src.radar.scan.feeds_module.fetch_all", return_value=([(feed, entry)], [])):
        with patch(
            "src.radar.scan.tag_item",
            return_value=TaggingResult(
                relevant=True,
                relevance_reason="Rate policy news",
                summary="Investors should buy this stock now given the rate cut.",  # banned phrasing
                tickers=[],
            ),
        ):
            record = scan.run(max_items_per_run=5)

    assert record.items_saved == 0
    assert record.items_rejected_by_guardrail == 1
    assert store.load_findings() == []


def test_scan_saves_clean_finding(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "FINDINGS_PATH", tmp_path / "radar_findings.json")
    monkeypatch.setattr(store, "STATE_PATH", tmp_path / "radar_state.json")

    feed = _fake_feed()
    entry = {"title": "Fed holds rates steady", "link": "https://example.com/fed-hold", "summary": "The Federal Reserve left rates unchanged.", "published": ""}

    with patch("src.radar.scan.feeds_module.fetch_all", return_value=([(feed, entry)], [])):
        with patch(
            "src.radar.scan.tag_item",
            return_value=TaggingResult(
                relevant=True,
                relevance_reason="Direct Fed policy announcement",
                summary="The Federal Reserve announced it is holding interest rates steady this month.",
                tickers=[],
            ),
        ):
            record = scan.run(max_items_per_run=5)

    assert record.items_saved == 1
    assert record.items_rejected_by_guardrail == 0
    saved = store.load_findings()
    assert len(saved) == 1
    assert saved[0].source_url == "https://example.com/fed-hold"


def test_scan_skips_items_below_keyword_relevance(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "FINDINGS_PATH", tmp_path / "radar_findings.json")
    monkeypatch.setattr(store, "STATE_PATH", tmp_path / "radar_state.json")

    feed = _fake_feed()
    entry = {"title": "Local bakery opens new branch", "link": "https://example.com/bakery", "summary": "", "published": ""}

    with patch("src.radar.scan.feeds_module.fetch_all", return_value=([(feed, entry)], [])):
        with patch("src.radar.scan.tag_item") as mock_tag:
            record = scan.run(max_items_per_run=5)
            mock_tag.assert_not_called()

    assert record.items_after_keyword_filter == 0
    assert record.items_saved == 0
