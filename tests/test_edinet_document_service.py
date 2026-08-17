"""edinet.document_service.get_or_fetch_excerpt — fully mocked
EdinetClient, zero network calls. Covers caching/idempotency, retry+
backoff-with-jitter on transient failures, and terminal failure states
(404/403/429/timeout) that must not retry forever."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.data_access.edinet import document_service
from src.data_access.edinet.errors import (
    EdinetForbiddenError,
    EdinetNotFoundError,
    EdinetRateLimitError,
    EdinetTimeoutError,
)
from src.models.models import ExtractionState


def _client(fetch_result) -> MagicMock:
    client = MagicMock()
    if isinstance(fetch_result, Exception):
        client.fetch_document.side_effect = fetch_result
    else:
        client.fetch_document.return_value = fetch_result
    return client


def test_successful_fetch_extracts_and_caches(tmp_path):
    client = _client(b"<html><body><p>Disclosure summary text.</p></body></html>")

    result = document_service.get_or_fetch_excerpt(client, "S100TEST1", tmp_path)

    assert result.state == ExtractionState.EXTRACTED
    assert result.from_cache is False
    assert "Disclosure summary" in result.excerpt_original


def test_repeated_call_uses_cache_not_a_second_network_call(tmp_path):
    client = _client(b"<html><body><p>Disclosure summary.</p></body></html>")

    first = document_service.get_or_fetch_excerpt(client, "S100TEST1", tmp_path)
    second = document_service.get_or_fetch_excerpt(client, "S100TEST1", tmp_path)

    assert first.from_cache is False
    assert second.from_cache is True
    assert client.fetch_document.call_count == 1


def test_missing_document_404_is_retrieval_failed(tmp_path):
    client = _client(EdinetNotFoundError(404, "not found"))

    result = document_service.get_or_fetch_excerpt(client, "S100MISSING", tmp_path)

    assert result.state == ExtractionState.RETRIEVAL_FAILED
    assert result.from_cache is False


def test_forbidden_403_is_retrieval_failed_not_retried(tmp_path):
    client = _client(EdinetForbiddenError(403, "forbidden"))

    result = document_service.get_or_fetch_excerpt(client, "S100FORBID", tmp_path)

    assert result.state == ExtractionState.RETRIEVAL_FAILED
    assert client.fetch_document.call_count == 1  # 403 is not one of the retried transient errors


def test_rate_limit_429_retries_then_succeeds(monkeypatch, tmp_path):
    monkeypatch.setattr(document_service.time, "sleep", lambda s: None)
    monkeypatch.setattr(document_service.random, "uniform", lambda a, b: 0)
    client = MagicMock()
    client.fetch_document.side_effect = [EdinetRateLimitError(429, "rate limited"), b"<html><body><p>ok content</p></body></html>"]

    result = document_service.get_or_fetch_excerpt(client, "S100RETRY", tmp_path)

    assert result.state == ExtractionState.EXTRACTED
    assert client.fetch_document.call_count == 2


def test_rate_limit_exhausts_retries_and_ends_as_retrieval_failed(monkeypatch, tmp_path):
    monkeypatch.setattr(document_service.time, "sleep", lambda s: None)
    monkeypatch.setattr(document_service.random, "uniform", lambda a, b: 0)
    client = _client(EdinetRateLimitError(429, "still rate limited"))

    result = document_service.get_or_fetch_excerpt(client, "S100RATELIMIT", tmp_path)

    assert result.state == ExtractionState.RETRIEVAL_FAILED
    assert client.fetch_document.call_count == document_service._MAX_RETRIES + 1


def test_timeout_retries_with_bounded_exponential_backoff_and_jitter(monkeypatch, tmp_path):
    sleeps = []
    monkeypatch.setattr(document_service.time, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(document_service.random, "uniform", lambda a, b: 0.25)
    client = MagicMock()
    client.fetch_document.side_effect = [EdinetTimeoutError("t1"), EdinetTimeoutError("t2"), b"<html><body><p>ok</p></body></html>"]

    result = document_service.get_or_fetch_excerpt(client, "S100TIMEOUT", tmp_path)

    assert result.state == ExtractionState.EXTRACTED
    assert len(sleeps) == 2
    assert sleeps[0] == 1.0 + 0.25
    assert sleeps[1] == 2.0 + 0.25


def test_never_retries_indefinitely(monkeypatch, tmp_path):
    monkeypatch.setattr(document_service.time, "sleep", lambda s: None)
    client = _client(EdinetTimeoutError("always times out"))

    result = document_service.get_or_fetch_excerpt(client, "S100ALWAYSTIMEOUT", tmp_path)

    assert result.state == ExtractionState.RETRIEVAL_FAILED
    assert client.fetch_document.call_count == document_service._MAX_RETRIES + 1


def test_failed_result_is_also_cached_so_it_is_not_retried_on_next_page_view(tmp_path):
    client = _client(EdinetNotFoundError(404, "not found"))

    document_service.get_or_fetch_excerpt(client, "S100NOTFOUND", tmp_path)
    second = document_service.get_or_fetch_excerpt(client, "S100NOTFOUND", tmp_path)

    assert second.from_cache is True
    assert client.fetch_document.call_count == 1


def test_default_type_requests_the_zip_format():
    from src.data_access.edinet.client import DOCUMENT_TYPE_ZIP
    client = MagicMock()
    client.fetch_document.return_value = b"<html><body><p>content</p></body></html>"

    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        document_service.get_or_fetch_excerpt(client, "S100TYPE", Path(d))

    client.fetch_document.assert_called_once_with("S100TYPE", DOCUMENT_TYPE_ZIP)


def test_binary_zip_content_is_a_safe_unsupported_format_not_a_crash(tmp_path):
    client = _client(b"\x50\x4b\x03\x04" + bytes(range(200)))

    result = document_service.get_or_fetch_excerpt(client, "S100BINARY", tmp_path)

    assert result.state == ExtractionState.UNSUPPORTED_FORMAT
    assert result.from_cache is False
