"""edinet.document_extractor.extract_excerpt — pure function, fully
fixture-driven. No network. Gate 10.A added real PDF text extraction
(via pypdf) behind this seam — every PDF fixture below is a small,
synthetic, hand-built, non-secret PDF constructed in this test file
itself (never a real EDINET document or copyrighted filing). ZIP/XBRL
parsing remains explicitly out of scope and still returns
UNSUPPORTED_FORMAT, unchanged from Gate 1."""
from __future__ import annotations

from unittest.mock import patch

from src.data_access.edinet.document_extractor import (
    MAX_DOCUMENT_SIZE_BYTES,
    MAX_EXCERPT_CHARS,
    extract_excerpt,
)
from src.models.models import ExtractionState


def _build_minimal_pdf(text: str = "Hello World") -> bytes:
    """Hand-built minimal single-page PDF with correctly computed xref
    offsets — a real, valid, parseable PDF structure, not a mock. Text
    is placed via a bare `Tj` show-text operator. Synthetic and
    non-secret; never real EDINET content."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream_content = f"BT /F1 24 Tf 100 700 Td ({text}) Tj ET".encode("latin-1")
    objects.append(b"<< /Length " + str(len(stream_content)).encode() + b" >>\nstream\n" + stream_content + b"\nendstream")
    return _assemble_pdf(objects)


def _build_pdf_with_no_text_content() -> bytes:
    """A structurally valid, parseable PDF with one page and an empty
    content stream — no text-showing operator at all. Stands in for an
    image-only/no-text-layer PDF without needing real image binary data
    — pypdf's extract_text() legitimately returns "" for a page with no
    text content either way, which is exactly the observable behavior
    this module needs to handle safely."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 612 792] /Contents 4 0 R >>",
        b"<< /Length 0 >>\nstream\n\nendstream",
    ]
    return _assemble_pdf(objects)


def _assemble_pdf(objects: list[bytes]) -> bytes:
    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    return pdf


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
    # A real ZIP file's magic bytes (PK\x03\x04) are explicitly detected
    # and refused — ZIP extraction is out of scope for this gate.
    zip_like = b"\x50\x4b\x03\x04\x14\x00\x00\x00\x08\x00" + bytes(range(200))
    result = extract_excerpt(zip_like)
    assert result.state == ExtractionState.UNSUPPORTED_FORMAT
    assert "ZIP" in result.detail


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


# --- Gate 10.A: PDF text extraction (pypdf, fixture-only, synthetic
# non-secret PDFs built above) ---

def test_valid_text_bearing_pdf_is_extracted():
    pdf = _build_minimal_pdf("Synthetic test evidence text for extraction validation.")
    result = extract_excerpt(pdf)
    assert result.state == ExtractionState.EXTRACTED
    assert "Synthetic test evidence text" in result.excerpt_original


def test_pdf_excerpt_is_bounded_to_max_chars():
    pdf = _build_minimal_pdf("A" * 2000)
    result = extract_excerpt(pdf)
    assert result.state == ExtractionState.EXTRACTED
    assert len(result.excerpt_original) == MAX_EXCERPT_CHARS


def test_pdf_text_is_normalized_but_not_translated_or_summarized():
    # Collapsed whitespace only — the exact substring must survive
    # verbatim, proving no translation/summarization/classification
    # occurs during extraction.
    pdf = _build_minimal_pdf("Original Japanese-context evidence unchanged")
    result = extract_excerpt(pdf)
    assert result.state == ExtractionState.EXTRACTED
    assert "Original Japanese-context evidence unchanged" == result.excerpt_original


def test_image_only_no_text_pdf_returns_parse_failed():
    pdf = _build_pdf_with_no_text_content()
    result = extract_excerpt(pdf)
    assert result.state == ExtractionState.PARSE_FAILED
    assert "image-only" in result.detail or "no extractable text" in result.detail


def test_empty_bytes_returns_parse_failed_not_pdf_path():
    # Empty bytes never match the %PDF- magic prefix, so this exercises
    # the pre-existing generic empty-input path, not the new PDF code —
    # confirming the two paths don't interfere with each other.
    result = extract_excerpt(b"")
    assert result.state == ExtractionState.PARSE_FAILED


def test_corrupt_truncated_pdf_returns_parse_failed_not_a_crash():
    # Real %PDF- magic bytes followed by non-PDF garbage — must be
    # caught by _extract_pdf_text's broad exception handler, never
    # surface a raw pypdf exception/stack trace.
    corrupt = b"%PDF-1.4\n" + bytes(range(200))
    result = extract_excerpt(corrupt)
    assert result.state == ExtractionState.PARSE_FAILED
    assert "corrupt" in result.detail.lower() or "truncated" in result.detail.lower()


def test_truncated_valid_pdf_returns_parse_failed():
    pdf = _build_minimal_pdf("This text will never be reached.")
    truncated = pdf[: len(pdf) // 2]  # cut a real, valid PDF in half
    result = extract_excerpt(truncated)
    assert result.state == ExtractionState.PARSE_FAILED


def test_zip_magic_when_pdf_expected_is_unsupported_format():
    zip_like = b"\x50\x4b\x03\x04" + bytes(range(200))
    result = extract_excerpt(zip_like)
    assert result.state == ExtractionState.UNSUPPORTED_FORMAT
    assert "ZIP" in result.detail


def test_non_pdf_unrecognized_binary_is_unsupported_format():
    unrecognized = bytes([0x00, 0x01, 0x02, 0x03]) + bytes(range(200))
    result = extract_excerpt(unrecognized)
    assert result.state == ExtractionState.UNSUPPORTED_FORMAT


def test_oversize_pdf_shaped_payload_is_unsupported_format_before_parsing():
    # The 8MB size gate must fire before any PDF parsing is attempted,
    # even when the payload starts with real PDF magic bytes.
    oversized_pdf_shaped = b"%PDF-1.4\n" + b"x" * MAX_DOCUMENT_SIZE_BYTES
    result = extract_excerpt(oversized_pdf_shaped)
    assert result.state == ExtractionState.UNSUPPORTED_FORMAT
    assert "safety limit" in result.detail


def test_encrypted_pdf_returns_parse_failed():
    # No real encrypted-PDF fixture is hand-built (nontrivial without a
    # PDF-writing library) — the reader.is_encrypted branch is verified
    # directly via a minimal patch of PdfReader, not by mocking away the
    # rest of the function's real logic.
    with patch("src.data_access.edinet.document_extractor.PdfReader") as mock_reader_cls:
        mock_reader_cls.return_value.is_encrypted = True
        pdf = _build_minimal_pdf("irrelevant")
        result = extract_excerpt(pdf)
    assert result.state == ExtractionState.PARSE_FAILED
    assert "encrypted" in result.detail.lower()


def test_pdf_extraction_is_deterministic_on_repeat():
    pdf = _build_minimal_pdf("Deterministic repeat check.")
    first = extract_excerpt(pdf)
    second = extract_excerpt(pdf)
    assert first.excerpt_original == second.excerpt_original
    assert first.state == second.state


def test_pdf_result_never_raises_for_garbage_shaped_like_pdf():
    for payload in (b"%PDF-", b"%PDF-1.4", b"%PDF-" + bytes(range(255)), b"%PDF-\x00\x00\x00"):
        result = extract_excerpt(payload)
        assert result.state in ExtractionState


# --- No raw PDF bytes are ever persisted; DART/EDGAR extractors are
# untouched by this gate ---

def test_extract_excerpt_never_returns_raw_document_bytes():
    # The function's own contract: excerpt_original is always str or
    # None, never the original bytes object — the only way raw PDF
    # bytes could leak into anything persisted downstream.
    pdf = _build_minimal_pdf("Some evidence text.")
    result = extract_excerpt(pdf)
    assert result.excerpt_original is None or isinstance(result.excerpt_original, str)
    assert not isinstance(result.excerpt_original, bytes)


def test_dart_document_extractor_module_is_not_imported_by_pdf_path():
    # DART's own document_extractor.py is reused only for its
    # _LenientHtmlTextExtractor helper (plain-text/HTML path) — the new
    # PDF path must not touch it at all.
    import src.data_access.edinet.document_extractor as edinet_extractor
    import src.data_access.dart.document_extractor as dart_extractor
    pdf = _build_minimal_pdf("Isolation check.")
    with patch.object(dart_extractor, "_LenientHtmlTextExtractor", side_effect=AssertionError("DART extractor must not be invoked for a PDF payload")):
        result = edinet_extractor.extract_excerpt(pdf)
    assert result.state == ExtractionState.EXTRACTED


def test_edgar_document_extractor_is_unmodified_and_still_html_only():
    # Confirms EDGAR's own extractor (a separate module entirely) was
    # not touched by this gate — it still has no PDF-handling code path.
    import src.data_access.edgar.document_extractor as edgar_extractor
    assert not hasattr(edgar_extractor, "PdfReader")
    assert not hasattr(edgar_extractor, "_extract_pdf_text")


def test_dart_document_extractor_is_unmodified_and_still_html_only():
    import src.data_access.dart.document_extractor as dart_extractor
    assert not hasattr(dart_extractor, "PdfReader")
    assert not hasattr(dart_extractor, "_extract_pdf_text")
