from datetime import datetime, timedelta, timezone

from src.radar import analytics
from src.radar.models import Niche, RadarFinding, TickerTag


def _finding(niche: str, hours_ago: float, tickers: list[TickerTag] | None = None) -> RadarFinding:
    ts = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    return RadarFinding(
        niche=niche, headline="H", summary="S", source_url="https://example.com/x",
        source_name="Feed", source_type="Press Release", published_at="", retrieved_at=ts,
        tickers=tickers or [],
    )


def test_findings_within_excludes_older_than_window():
    fresh = _finding(Niche.MACRO.value, hours_ago=2)
    old = _finding(Niche.MACRO.value, hours_ago=24 * 10)  # 10 days old
    result = analytics.findings_within([fresh, old], days=7)
    assert result == [fresh]


def test_findings_within_handles_unparseable_date():
    bad = _finding(Niche.MACRO.value, hours_ago=1)
    bad.retrieved_at = "not-a-date"
    assert analytics.findings_within([bad], days=7) == []


def test_mentions_per_niche_counts_correctly():
    findings = [
        _finding(Niche.AI_BUILDOUT.value, 1),
        _finding(Niche.AI_BUILDOUT.value, 2),
        _finding(Niche.SPACE.value, 3),
    ]
    counts = analytics.mentions_per_niche(findings)
    assert counts == {Niche.AI_BUILDOUT.value: 2, Niche.SPACE.value: 1}


def test_mentions_per_day_zero_fills_quiet_days():
    findings = [_finding(Niche.MACRO.value, hours_ago=1)]  # today only
    buckets = analytics.mentions_per_day(findings, days=3)
    assert len(buckets) == 3
    assert sum(buckets.values()) == 1
    assert list(buckets.values())[-1] == 1  # most recent day (today) has the one finding


def test_top_tickers_ranks_by_mention_count():
    findings = [
        _finding(Niche.AI_BUILDOUT.value, 1, [TickerTag(ticker="NVDA", company_name="NVIDIA", jurisdiction="United States")]),
        _finding(Niche.AI_BUILDOUT.value, 2, [TickerTag(ticker="NVDA", company_name="NVIDIA", jurisdiction="United States")]),
        _finding(Niche.SPACE.value, 3, [TickerTag(ticker="RKLB", company_name="Rocket Lab", jurisdiction="United States")]),
    ]
    top = analytics.top_tickers(findings)
    assert top[0]["ticker"] == "NVDA"
    assert top[0]["count"] == 2
    assert top[1]["ticker"] == "RKLB"
    assert top[1]["count"] == 1


def test_is_scan_overdue_false_for_recent_run():
    recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert analytics.is_scan_overdue(recent) is False


def test_is_scan_overdue_true_when_far_past_expected_interval():
    stale = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    assert analytics.is_scan_overdue(stale, expected_interval_hours=2, grace_multiplier=3) is True


def test_is_scan_overdue_false_with_no_prior_run():
    assert analytics.is_scan_overdue(None) is False


def test_is_scan_overdue_false_for_unparseable_timestamp():
    assert analytics.is_scan_overdue("not-a-date") is False


def test_top_tickers_respects_limit():
    findings = [
        _finding(Niche.MACRO.value, i, [TickerTag(ticker=f"T{i}", company_name="X", jurisdiction="United States")])
        for i in range(20)
    ]
    assert len(analytics.top_tickers(findings, limit=5)) == 5


def _tag(ticker):
    return TickerTag(ticker=ticker, company_name=ticker, jurisdiction="United States")


def test_find_cross_theme_findings_requires_two_different_themes_in_same_finding():
    themes = {"MU": "Memory", "COHR": "Photonics", "MP": "Rare Earths"}

    single_theme = _finding(Niche.AI_BUILDOUT.value, 1, [_tag("MU")])
    cross_theme = _finding(Niche.AI_BUILDOUT.value, 2, [_tag("MU"), _tag("COHR")])
    three_theme = _finding(Niche.AI_BUILDOUT.value, 3, [_tag("MU"), _tag("COHR"), _tag("MP")])
    untracked_ticker = _finding(Niche.AI_BUILDOUT.value, 4, [_tag("ZZZZ")])

    results = analytics.find_cross_theme_findings(
        [single_theme, cross_theme, three_theme, untracked_ticker], themes
    )

    assert len(results) == 2
    result_findings = [r["finding"] for r in results]
    assert cross_theme in result_findings
    assert three_theme in result_findings
    assert single_theme not in result_findings
    assert untracked_ticker not in result_findings


def test_find_cross_theme_findings_reports_which_themes():
    themes = {"MU": "Memory", "COHR": "Photonics"}
    finding = _finding(Niche.AI_BUILDOUT.value, 1, [_tag("MU"), _tag("COHR")])

    results = analytics.find_cross_theme_findings([finding], themes)

    assert results[0]["themes"] == ["Memory", "Photonics"]


def test_find_cross_theme_findings_two_tickers_same_theme_does_not_count():
    themes = {"MU": "Memory", "SNDK": "Memory"}
    finding = _finding(Niche.AI_BUILDOUT.value, 1, [_tag("MU"), _tag("SNDK")])

    assert analytics.find_cross_theme_findings([finding], themes) == []
