"""Bounded, best-effort extraction seam for one official EDINET document
(Japan radar pilot). For a single, explicitly selected FilingEvent/
CandidateSignal only, never a bulk/background operation.

Gate 1 status (superseded for PDF only, see Gate 10.A below) —
deliberately minimal, per the approved plan and the explicit Gate 1
instruction "Do not write a real XBRL parser/analytics engine. Build
only a bounded, source-specific extraction seam and fixtures sufficient
to validate its safe fallback behavior": real EDINET documents are
described (unconfirmed — see client.py's module docstring) as ZIP
packages containing XBRL/PDF/CSV content, not plain HTML/text like
EDGAR's primary documents. This module therefore:

  1. Handles genuinely plain-text/HTML content exactly like
     DART/EDGAR's shared `_LenientHtmlTextExtractor` (reused directly,
     not reimplemented).
  2. Handles a PDF payload via pypdf (Gate 10.A — see below).
  3. For anything else (a real ZIP, or other unrecognized binary
     payload), returns UNSUPPORTED_FORMAT with a clear, honest detail
     message rather than attempting a guessed parse. ZIP/XBRL parsing
     remains explicit follow-up work for a later, live-validated gate.

Gate 10.A — fixture-only PDF text extraction, added behind this same
seam, using `pypdf` (added to requirements.txt this gate — a lightweight,
pure-Python library; no OCR, no external binaries, no browser
automation, no Java tool, no shell-out). Detected by magic bytes
(`%PDF-`) BEFORE the plain-text/HTML path runs, so a real PDF — which is
never valid UTF-8 — gets real extraction instead of falling through to
the generic UNSUPPORTED_FORMAT binary fallback. Every fixture exercising
this path this gate is synthetic, non-secret, and built in-test — no
real EDINET document or copyrighted filing is added to this repository.
Zero live network calls are made or needed to write or test this code;
S100YGH5 itself is not fetched this gate."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass

from pypdf import PdfReader

from src.data_access.dart.document_extractor import _LenientHtmlTextExtractor
from src.models.models import ExtractionState

MAX_DOCUMENT_SIZE_BYTES = 8 * 1024 * 1024  # same pilot ceiling as DART/EDGAR
MAX_EXCERPT_CHARS = 600  # same generic bounded-excerpt cap as DART/EDGAR

_PDF_MAGIC = b"%PDF-"
_ZIP_MAGIC = b"PK\x03\x04"

_UNSUPPORTED_BINARY_DETAIL = (
    "Document is not plain-text/HTML-decodable and not a recognized PDF — "
    "likely a ZIP or other binary EDINET payload. ZIP/XBRL extraction is "
    "out of scope for this gate; only a safe UNSUPPORTED_FORMAT fallback "
    "is produced."
)
_ZIP_DETAIL = (
    "Document is a ZIP/container payload (magic bytes PK\\x03\\x04) — ZIP "
    "extraction is out of scope for this gate; only a safe "
    "UNSUPPORTED_FORMAT fallback is produced."
)
_PDF_ENCRYPTED_DETAIL = "PDF is encrypted; cannot extract text without a password."
_PDF_CORRUPT_DETAIL = "PDF could not be parsed — corrupt or truncated payload."
_PDF_NO_TEXT_DETAIL = "PDF parsed but contained no extractable text (likely image-only/scanned, with no text layer)."


@dataclass(frozen=True)
class ExtractionResult:
    state: ExtractionState
    excerpt_original: str | None = None
    detail: str = ""


def _decode_if_plain_text(raw: bytes) -> str | None:
    """Returns decoded text only when the payload is plausibly plain
    text/HTML — never for binary content. A ZIP/PDF payload will fail
    UTF-8 decoding almost always (both are binary formats with byte
    sequences invalid as UTF-8), which is exactly the signal this
    function uses to refuse rather than guess. No Shift-JIS/legacy
    fallback is attempted here: unlike DART's Korean HWP/legacy-encoding
    problem (a real, confirmed encoding-variance issue), EDINET's actual
    text encoding for non-binary content is unconfirmed, and guessing an
    encoding chain for a format this module doesn't yet know the real
    shape of would be exactly the kind of premature assumption Gate 1 is
    meant to avoid."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _extract_pdf_text(document_bytes: bytes) -> ExtractionResult:
    """pypdf-based extraction (Gate 10.A) — every pypdf-raised exception
    (malformed structure, unsupported filter, truncated stream, etc.) is
    caught broadly and mapped to PARSE_FAILED with a safe, generic
    detail, same discipline the HTML-parser path below already uses:
    never a raw exception/stack trace surfaced to the caller. Text is
    normalized (collapsed whitespace) but never translated, summarized,
    or interpreted — this function only decides EXTRACTED vs.
    PARSE_FAILED and returns the bounded original-language excerpt."""
    try:
        reader = PdfReader(io.BytesIO(document_bytes))
        if reader.is_encrypted:
            return ExtractionResult(state=ExtractionState.PARSE_FAILED, detail=_PDF_ENCRYPTED_DETAIL)
        parts = [page.extract_text() or "" for page in reader.pages]
    except Exception:
        return ExtractionResult(state=ExtractionState.PARSE_FAILED, detail=_PDF_CORRUPT_DETAIL)

    excerpt = re.sub(r"\s+", " ", " ".join(parts)).strip()
    if not excerpt:
        return ExtractionResult(state=ExtractionState.PARSE_FAILED, detail=_PDF_NO_TEXT_DETAIL)
    return ExtractionResult(state=ExtractionState.EXTRACTED, excerpt_original=excerpt[:MAX_EXCERPT_CHARS])


def extract_excerpt(document_bytes: bytes) -> ExtractionResult:
    """Pure function over already-fetched bytes — network I/O and the
    per-docID cache/dedup live in document_service.py, one layer up
    (same separation DART/EDGAR's own document_service.py modules use)."""
    if len(document_bytes) > MAX_DOCUMENT_SIZE_BYTES:
        return ExtractionResult(
            state=ExtractionState.UNSUPPORTED_FORMAT,
            detail=f"Document exceeds the {MAX_DOCUMENT_SIZE_BYTES // (1024 * 1024)}MB safety limit.",
        )

    if document_bytes.startswith(_ZIP_MAGIC):
        return ExtractionResult(state=ExtractionState.UNSUPPORTED_FORMAT, detail=_ZIP_DETAIL)

    if document_bytes.startswith(_PDF_MAGIC):
        return _extract_pdf_text(document_bytes)

    text = _decode_if_plain_text(document_bytes)
    if text is None:
        return ExtractionResult(state=ExtractionState.UNSUPPORTED_FORMAT, detail=_UNSUPPORTED_BINARY_DETAIL)

    parser = _LenientHtmlTextExtractor()
    try:
        parser.feed(text)
    except Exception:
        return ExtractionResult(state=ExtractionState.PARSE_FAILED, detail="Document could not be parsed.")

    excerpt = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
    if not excerpt and "<" not in text:
        # Plain-text (non-HTML, non-binary) document — no tags for the
        # HTML parser to walk. Same "only for genuinely non-HTML input"
        # gate EDGAR's own extractor uses.
        excerpt = re.sub(r"\s+", " ", text).strip()

    if not excerpt:
        return ExtractionResult(state=ExtractionState.PARSE_FAILED, detail="Document parsed but contained no extractable text.")

    return ExtractionResult(state=ExtractionState.EXTRACTED, excerpt_original=excerpt[:MAX_EXCERPT_CHARS])
