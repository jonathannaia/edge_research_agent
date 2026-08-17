"""edinet.document_extractor.extract_excerpt — pure function, fully
fixture-driven. No network. Gate 1 deliberately does NOT parse real
EDINET ZIP/PDF/XBRL payloads (see module docstring) — this suite proves
the safe-fallback behavior for binary content and the one real case that
does work today (plain-text/HTML content), never a guessed real-format
parse."""
from __future__ import annotations

from src.data_access.edinet.document_extractor import (
    MAX_DOCUMENT_SIZE_BYTES,
    MAX_EXCERPT_CHARS,
    extract_excerpt,
)
from src.models.models import ExtractionState


def test_extracts_text_from_plain_html():
    html = "<html><body><p>有価証券報告書 Annual Securities Report summary text.</p></body></html>".encode("utf-8")
    result = extract_excerpt(html)
    assert result.state == ExtractionState.EXTRACTED
    assert "Annual Securities Report" in result.excerpt_original


def test_extracts_from_plain_text_document_with_no_html_tags():
    text = "重要な開示事項です。 An important disclosure summary follows.".encode("utf-8")
    result = extract_excerpt(text)
    assert result.state == ExtractionState.EXTRACTED
    assert "An important disclosure" in result.excerpt_original


def test_skips_script_and_style_content():
    html = b"<html><head><style>.a{color:red}</style></head><body><script>var x=1;</script><p>Disclosure text here.</p></body></html>"
    result = extract_excerpt(html)
    assert result.state == ExtractionState.EXTRACTED
    assert "color:red" not in result.excerpt_original
    assert "var x=1" not in result.excerpt_original
    assert "Disclosure text here" in result.excerpt_original


def test_excerpt_is_bounded_to_max_chars():
    long_text = ("Disclosure summary. " + "x" * 2000).encode("utf-8")
    result = extract_excerpt(long_text)
    assert result.state == ExtractionState.EXTRACTED
    assert len(result.excerpt_original) == MAX_EXCERPT_CHARS


def test_oversized_document_is_rejected_without_parsing():
    oversized = b"x" * (MAX_DOCUMENT_SIZE_BYTES + 1)
    result = extract_excerpt(oversized)
    assert result.state == ExtractionState.UNSUPPORTED_FORMAT
    assert "safety limit" in result.detail


def test_empty_document_returns_parse_failed():
    result = extract_excerpt(b"")
    assert result.state == ExtractionState.PARSE_FAILED


def test_html_with_only_tags_and_no_text_returns_parse_failed():
    result = extract_excerpt(b"<html><body><div></div><span></span></body></html>")
    assert result.state == ExtractionState.PARSE_FAILED


def test_real_looking_zip_payload_is_unsupported_format_not_a_crash():
    # A real ZIP file's magic bytes (\x50\x4b\x03\x04) are invalid UTF-8 —
    # this is exactly the honest Gate 1 behavior: no real ZIP/XBRL parsing
    # is attempted, a clear UNSUPPORTED_FORMAT is returned instead.
    zip_like = b"\x50\x4b\x03\x04\x14\x00\x00\x00\x08\x00" + bytes(range(200))
    result = extract_excerpt(zip_like)
    assert result.state == ExtractionState.UNSUPPORTED_FORMAT
    assert "ZIP" in result.detail or "binary" in result.detail


def test_real_looking_pdf_payload_is_unsupported_format_not_a_crash():
    pdf_like = b"%PDF-1.4\n" + bytes(range(200))
    result = extract_excerpt(pdf_like)
    assert result.state == ExtractionState.UNSUPPORTED_FORMAT


def test_result_never_raises_for_garbage_input():
    for payload in (b"\xff\xfe\x00\xff", b"<broken<html", b""):
        result = extract_excerpt(payload)
        assert result.state in ExtractionState


def test_reprocessing_the_same_bytes_is_deterministic():
    html = b"<html><body><p>Consistent disclosure text.</p></body></html>"
    first = extract_excerpt(html)
    second = extract_excerpt(html)
    assert first.excerpt_original == second.excerpt_original
    assert first.state == second.state
