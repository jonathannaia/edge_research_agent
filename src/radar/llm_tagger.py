"""Claude Haiku 4.5-backed relevance filter, ticker tagger, and cited
summarizer for candidate Radar items.

This is the ONE place in the whole app that calls an LLM — everywhere else
(the manual research pipeline) is deliberately rule-based/zero-LLM-cost by
design (see README "Why there's no LLM in the loop"). Radar is the
exception, and it's held to the same guardrails as the rest of the app:

  - The model is given ONLY the feed item's title + RSS summary/snippet —
    never asked to browse or invent facts beyond that text.
  - Its output summary is treated as untrusted generated content and run
    through guardrails.language_filters.enforce_no_advice_language() before
    it's ever saved (see src/radar/scan.py).
  - Every finding is anchored to source_url — there is no un-cited claim;
    the "citation" is structural (the finding IS the article), not a
    separate lookup the model could get wrong.
  - Haiku 4.5, not a larger model: this is high-volume, low-complexity
    classification/extraction work (relevance + ticker tagging + a one-line
    factual restatement), and the user was explicit about keeping ongoing
    API cost minimal for a ~12-scans/day cron job.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from src.radar.models import Niche, TickerTag

MODEL = "claude-haiku-4-5"

_JURISDICTIONS = ["United States", "Japan", "South Korea", "China", "Hong Kong", "Other"]

_SYSTEM_PROMPT = (
    "You are a scoping and tagging assistant for an equity research tool's autonomous news radar. "
    "You are given the title and short snippet of one article from a pre-approved RSS feed. Your job:\n\n"
    "1. Decide if this item is genuinely relevant to one of these four scopes: AI Buildout (data centers, "
    "GPUs/accelerators, chip supply chain, hyperscaler capex, power/cooling for AI infrastructure), "
    "Humanoids (humanoid robots, robotics automation), Space (space launch, satellites, spacecraft), "
    "or Macro (interest rates, inflation, central bank policy, market-moving economic data/events). "
    "Reject items that only superficially mention a keyword but aren't substantively about one of these.\n"
    "2. If relevant, identify any publicly traded companies concretely implicated by the item (not just "
    "mentioned in passing) and tag their stock ticker if you are reasonably confident of it, with a "
    "best-guess jurisdiction. Only include a ticker you are confident is correct — omit it rather than guess.\n"
    "3. Write a one-to-two sentence factual summary using ONLY information present in the provided title "
    "and snippet. Do not add outside facts, do not speculate about stock price impact, and NEVER use "
    "investment-recommendation language (no buy/sell/hold, no price targets, no 'you should'). State what "
    "happened, not what it means for the stock.\n\n"
    "If the snippet is too thin to summarize responsibly, set relevant to false rather than guessing."
)

_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "relevant": {"type": "boolean"},
        "relevance_reason": {"type": "string", "description": "One short clause explaining the relevance judgment."},
        "summary": {"type": "string", "description": "1-2 sentence factual summary grounded only in the provided text. Empty string if not relevant."},
        "tickers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "company_name": {"type": "string"},
                    "jurisdiction": {"type": "string", "enum": _JURISDICTIONS},
                },
                "required": ["ticker", "company_name", "jurisdiction"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["relevant", "relevance_reason", "summary", "tickers"],
    "additionalProperties": False,
}


@dataclass
class TaggingResult:
    relevant: bool
    relevance_reason: str
    summary: str
    tickers: list[TickerTag]


class TaggingError(RuntimeError):
    pass


def _client():
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise TaggingError("ANTHROPIC_API_KEY is not set — Radar cannot tag items without it.")
    return anthropic.Anthropic(api_key=api_key)


def tag_item(niche: str, title: str, snippet: str) -> TaggingResult:
    """Makes one bounded Haiku call to classify/tag/summarize a single
    candidate item. Raises TaggingError on any API or parsing failure so the
    caller can log it and skip the item rather than saving something
    malformed."""
    client = _client()

    user_content = (
        f"Feed's declared scope: {niche}\n"
        f"Title: {title}\n"
        f"Snippet: {snippet or '(no snippet provided)'}"
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            output_config={"format": {"type": "json_schema", "schema": _OUTPUT_SCHEMA}},
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception as exc:  # anthropic.APIError and friends
        raise TaggingError(f"Anthropic API call failed: {exc}") from exc

    text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), None)
    if text is None:
        raise TaggingError("Model response had no text block.")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TaggingError(f"Model output was not valid JSON: {exc}") from exc

    tickers = [
        TickerTag(ticker=t["ticker"].upper().strip(), company_name=t["company_name"].strip(), jurisdiction=t["jurisdiction"])
        for t in data.get("tickers", [])
        if t.get("ticker")
    ]

    return TaggingResult(
        relevant=bool(data.get("relevant")),
        relevance_reason=(data.get("relevance_reason") or "").strip(),
        summary=(data.get("summary") or "").strip(),
        tickers=tickers,
    )
