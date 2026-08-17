"""EDINET's own category-routing rules (Japan radar pilot, planning
Gate 1). No LLM calls, no market interpretation — same "routing input
only, never proof of relevance" posture as dart_rules.py/edgar_rules.py.

Gate 1 status — read before extending this module: per the approved
EDINET-only plan (§4), real Japanese statutory document-type codes
(ordinanceCode/formCode combinations, or their docDescription/title text)
must NOT be guessed into this module — they are populated "only after a
live pull, never guessed." Gate 0 did not confirm any such code, and the
plan explicitly forbids encoding a Japan ownership/large-shareholding
materiality threshold in this pilot. So this module intentionally ships
with only the STRUCTURE of a category system — the category slugs
themselves (English, provisional labels for the taxonomy this pilot
expects to need) and a routing function driven by an explicit, injectable
`code_category_map` — and DEFAULT_CODE_CATEGORY_MAP is deliberately
empty. With the empty default, evaluate_document() matches nothing for
every real input, which is the honest, correct Gate 1 behavior: this
module does not yet know a single real EDINET code-to-category mapping.
Fixture tests exercise the mechanism using their own explicit,
fictional-and-labeled-as-such test codes, never real EDINET codes.
"""
from __future__ import annotations

from dataclasses import dataclass

LEXICON_VERSION = "v0-2026-08-edinet-gate1-unpopulated"

# Provisional category taxonomy (English slugs only) — see module
# docstring. Mirrors the shape of DART/EDGAR's category sets structurally,
# not their content; every one of these is a placeholder bucket name, not
# yet backed by any real EDINET code.
EDINET_CATEGORIES: tuple[str, ...] = (
    "earnings_or_results",
    "guidance",
    "capex_or_facility_expansion",
    "material_contract_or_partnership",
    "financing_or_debt",
    "ma_or_strategic_investment",
    "governance",
    "ownership_or_large_shareholding",
    "regulatory_or_legal",
    "technology_or_product",
    "other",
)

# Intentionally empty. See module docstring — do not populate with a
# guessed real ordinanceCode/formCode/docTypeCode mapping. A future gate
# must populate this only from a confirmed, live-verified source.
DEFAULT_CODE_CATEGORY_MAP: dict[str, str] = {}


@dataclass(frozen=True)
class RuleEvaluation:
    matched_rules: tuple[str, ...]
    # None means: stay a FilingEvent, do not promote to CandidateSignal.
    confidence: str | None


def _confidence_for(matched: list[str]) -> str | None:
    if not matched:
        return None
    distinct_categories = len({m.split(":", 1)[0] for m in matched})
    return "High" if distinct_categories >= 2 else "Moderate"


def _routing_key(ordinance_code: str, form_code: str) -> str:
    return f"{ordinance_code.strip()}:{form_code.strip()}"


def evaluate_document(
    ordinance_code: str,
    form_code: str,
    code_category_map: dict[str, str] = DEFAULT_CODE_CATEGORY_MAP,
) -> RuleEvaluation:
    """Scan-time evaluation from EDINET's ordinanceCode+formCode pair
    (the provisional field names the user explicitly authorized recording
    — see design/DECISIONS.md's Gate 0 entry). Pure function, no I/O.
    `code_category_map` is injectable specifically so fixtures can supply
    their own explicit, labeled-provisional test mappings without this
    module claiming any real EDINET code as fact — with the module-level
    DEFAULT_CODE_CATEGORY_MAP (empty), every real input yields
    confidence=None, i.e. no candidate is ever produced from real EDINET
    data by this rule set yet."""
    category = code_category_map.get(_routing_key(ordinance_code, form_code))
    if category is None:
        return RuleEvaluation(matched_rules=(), confidence=None)
    key = _routing_key(ordinance_code, form_code)
    return RuleEvaluation(matched_rules=(f"{category}:{key}",), confidence="Moderate")


def merge_evaluations(evaluations: list[RuleEvaluation]) -> RuleEvaluation:
    """Combines multiple independent matches (e.g. a code-based match plus
    a future keyword-based match) into one — additive union, never a
    destructive overwrite, same monotonic-merge principle
    edgar_rules.merge_8k_item_evaluation established. Not yet exercised by
    any real caller in Gate 1 (only one evaluation source — code-based —
    exists so far); included now so scan_service has a stable seam to
    call if/when a second evaluation source (e.g. docDescription keyword
    matching) is added in a later gate, without needing to change the
    merge contract at that point."""
    matched: list[str] = []
    for evaluation in evaluations:
        for rule in evaluation.matched_rules:
            if rule not in matched:
                matched.append(rule)
    return RuleEvaluation(matched_rules=tuple(matched), confidence=_confidence_for(matched))
