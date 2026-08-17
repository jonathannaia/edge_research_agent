"""Bounded, best-effort extraction seam for one official EDINET document
(Japan radar pilot, planning Gate 1). For a single, explicitly selected
FilingEvent/CandidateSignal only, never a bulk/background operation.

Gate 1 status — deliberately minimal, per the approved plan and the
explicit Gate 1 instruction "Do not write a real XBRL parser/analytics
engine. Build only a bounded, source-specific extraction seam and
fixtures sufficient to validate its safe fallback behavior": real EDINET
documents are described (unconfirmed — see client.py's module docstring)
as ZIP packages containing XBRL/PDF/CSV content, not plain HTML/text like
EDGAR's primary documents. Actually parsing any of those formats is
explicitly out of scope this gate. This module therefore:

  1. Handles genuinely plain-text/HTML content exactly like
     DART/EDGAR's shared `_LenientHtmlTextExtractor` (reused directly,
     not reimplemented) — the one case a real, safe excerpt can be
     produced today.
  2. For anything that isn't plain-text/HTML-decodable (a real ZIP, PDF,
     or other binary payload), returns UNSUPPORTED_FORMAT with a clear,
     honest detail message rather than attempting a guessed parse. This
     is the correct, safe behavior for Gate 1 — real format-specific
     extraction (ZIP→XBRL, PDF text, etc.) is explicit follow-up work
     for a later, live-validated gate, once Gate 4's real document pull
     shows the actual shape.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from src.data_access.dart.document_extractor import _LenientHtmlTextExtractor
from src.models.models import ExtractionState

MAX_DOCUMENT_SIZE_BYTES = 8 * 1024 * 1024  # same pilot ceiling as DART/EDGAR
MAX_EXCERPT_CHARS = 600  # same generic bounded-excerpt cap as DART/EDGAR

_UNSUPPORTED_BINARY_DETAIL = (
    "Document is not plain-text/HTML-decodable — likely a ZIP, PDF, or "
    "other binary EDINET payload. Real format-specific extraction "
    "(ZIP/XBRL/PDF) is out of scope for this gate; only a safe "
    "UNSUPPORTED_FORMAT fallback is produced."
)


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


def extract_excerpt(document_bytes: bytes) -> ExtractionResult:
    """Pure function over already-fetched bytes — network I/O and the
    per-docID cache/dedup live in document_service.py, one layer up
    (same separation DART/EDGAR's own document_service.py modules use)."""
    if len(document_bytes) > MAX_DOCUMENT_SIZE_BYTES:
        return ExtractionResult(
            state=ExtractionState.UNSUPPORTED_FORMAT,
            detail=f"Document exceeds the {MAX_DOCUMENT_SIZE_BYTES // (1024 * 1024)}MB safety limit.",
        )

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
