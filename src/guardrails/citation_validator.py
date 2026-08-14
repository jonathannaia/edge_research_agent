"""Guardrail principle #1: "No citation, no factual claim."

Every material fact assembled into a brief is represented as a Fact dict:

    {"text": str, "source_id": int | None, "label": str | None}

`label` is one of UNVERIFIED_LABELS ("unverified", "estimate",
"insufficient evidence") and is only valid in place of a source_id, never
alongside a fabricated one. This module is the single choke point a brief
must pass through before it can be saved — src.services.research_service
calls validate_brief() and refuses to persist a brief that fails it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

UNVERIFIED_LABELS = {"unverified", "estimate", "insufficient evidence"}


class CitationError(ValueError):
    pass


@dataclass
class Fact:
    text: str
    source_id: Optional[int] = None
    label: Optional[str] = None


def validate_fact(fact: dict) -> tuple[bool, Optional[str]]:
    """Returns (is_valid, error_message)."""
    text = (fact.get("text") or "").strip()
    if not text:
        return False, "Fact has no text."

    source_id = fact.get("source_id")
    label = (fact.get("label") or "").strip().lower() or None

    if source_id is not None:
        if not isinstance(source_id, int) or source_id <= 0:
            return False, f"Fact '{text[:60]}...' has an invalid source_id."
        return True, None

    if label is not None:
        if label not in UNVERIFIED_LABELS:
            return False, f"Fact '{text[:60]}...' has an unrecognized label '{label}'."
        return True, None

    return False, f"Fact '{text[:60]}...' has neither a source_id nor an unverified/estimate label."


@dataclass
class BriefValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)


def validate_brief_facts(facts: list[dict]) -> BriefValidationResult:
    """Validates every fact in a flattened list pulled from all sections of
    a brief (verified evidence, fundamentals snapshot, filing highlights,
    bull/bear evidence, etc.)."""
    errors: list[str] = []
    for fact in facts:
        ok, err = validate_fact(fact)
        if not ok:
            errors.append(err)
    return BriefValidationResult(is_valid=not errors, errors=errors)


def collect_facts_from_sections(sections: dict) -> list[dict]:
    """Walks a brief's sections_json payload and extracts every dict that
    looks like a Fact (has a 'text' key) so it can be validated in bulk."""
    facts: list[dict] = []

    def _walk(node):
        if isinstance(node, dict):
            if "text" in node:
                # Any dict carrying a 'text' key is a fact candidate, whether or
                # not it also carries source_id/label — a fact missing both is
                # exactly the violation this validator exists to catch.
                facts.append(node)
            else:
                for v in node.values():
                    _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(sections)
    return facts


def validate_brief(sections: dict) -> BriefValidationResult:
    facts = collect_facts_from_sections(sections)
    return validate_brief_facts(facts)
