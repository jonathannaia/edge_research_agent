"""Guardrail principle #7: no price prediction or trade recommendation.

Applied as a HARD block on anything the system generates (research brief
text, scorecard explanations). Applied as a SOFT warning (not a block) on
the user's own free-text fields (notes, thesis owner notes) — those are the
user's private reasoning, and the tool's job is to flag risky phrasing, not
censor the user's own notebook.
"""
from __future__ import annotations

import re

BANNED_PATTERNS = [
    r"\bstrong buy\b",
    r"\bbuy this stock\b",
    r"\byou should buy\b",
    r"\bbuy now\b",
    r"\bsell this stock\b",
    r"\byou should sell\b",
    r"\bsell now\b",
    r"\bhold rating\b",
    r"\bprice target of\b",
    r"\bpt of \$",
    r"\bguaranteed return\b",
    r"\bguaranteed to\b",
    r"\bcan't lose\b",
    r"\brecommend(ed|ing)? buying\b",
    r"\brecommend(ed|ing)? selling\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in BANNED_PATTERNS]


def find_advice_language(text: str) -> list[str]:
    if not text:
        return []
    hits = []
    for pattern in _COMPILED:
        for match in pattern.finditer(text):
            hits.append(match.group(0))
    return hits


class AdviceLanguageError(ValueError):
    pass


def enforce_no_advice_language(text: str, context: str = "") -> None:
    """Hard block for system-generated content. Raises if any banned phrase
    is found."""
    hits = find_advice_language(text)
    if hits:
        where = f" in {context}" if context else ""
        raise AdviceLanguageError(
            f"Generated content{where} contains trade-recommendation language: {hits}. "
            "The system may describe bull/bear/mixed evidence-based setups only."
        )


def warn_no_advice_language(text: str) -> list[str]:
    """Soft check for user-authored free text. Returns matches for the UI to
    display as a non-blocking warning; never raises."""
    return find_advice_language(text)
