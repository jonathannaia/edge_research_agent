from unittest.mock import MagicMock, patch

from src.radar.models import Niche, RadarFinding
from src.radar.notifier import send_webhook_notification


def _finding(headline: str) -> RadarFinding:
    return RadarFinding(
        niche=Niche.SPACE.value, headline=headline, summary="S", source_url="https://example.com/x",
        source_name="Feed", source_type="Press Release", published_at="", retrieved_at="2026-08-01T00:00:00+00:00",
    )


def test_no_ops_when_env_var_unset(monkeypatch):
    monkeypatch.delenv("EDGE_RADAR_WEBHOOK_URL", raising=False)
    with patch("src.radar.notifier.urllib.request.urlopen") as mock_urlopen:
        result = send_webhook_notification([_finding("Test")])
    mock_urlopen.assert_not_called()
    assert result is None


def test_no_ops_when_no_new_findings(monkeypatch):
    monkeypatch.setenv("EDGE_RADAR_WEBHOOK_URL", "https://hooks.example.com/x")
    with patch("src.radar.notifier.urllib.request.urlopen") as mock_urlopen:
        result = send_webhook_notification([])
    mock_urlopen.assert_not_called()
    assert result is None


def test_posts_when_url_set_and_findings_present(monkeypatch):
    monkeypatch.setenv("EDGE_RADAR_WEBHOOK_URL", "https://hooks.example.com/x")
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp
    with patch("src.radar.notifier.urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        result = send_webhook_notification([_finding("Rocket launch")])

    mock_urlopen.assert_called_once()
    assert result is None


def test_returns_error_string_on_failure_never_raises(monkeypatch):
    import urllib.error

    monkeypatch.setenv("EDGE_RADAR_WEBHOOK_URL", "https://hooks.example.com/x")
    with patch("src.radar.notifier.urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
        result = send_webhook_notification([_finding("Rocket launch")])

    assert result is not None
    assert "failed" in result.lower()
