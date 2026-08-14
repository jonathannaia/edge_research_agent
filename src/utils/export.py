"""Exports a saved research brief to Markdown or HTML. No external markdown
library is used — both formats are built directly from the same structured
section data so they never drift from each other or from what's stored in
the database.
"""
from __future__ import annotations

import html as _html
from typing import Any


def fact_line(fact: dict) -> str:
    text = fact.get("text", "")
    if fact.get("source_id"):
        return f"{text} [Source #{fact['source_id']}]"
    if fact.get("label"):
        return f"{text} [{fact['label'].upper()}]"
    return text


def _facts_or_strings(items: list) -> list[str]:
    out = []
    for item in items:
        if isinstance(item, dict):
            out.append(fact_line(item))
        else:
            out.append(str(item))
    return out


SECTION_TITLES: list[tuple[str, str]] = [
    ("bottom_line", "Bottom Line"),
    ("confidence_level", "Confidence Level"),
    ("thesis_summary", "Thesis Summary"),
    ("what_changed_recently", "What Changed Since Last Review"),
    ("verified_evidence", "Verified Evidence"),
    ("fundamentals_snapshot", "Fundamentals Snapshot"),
    ("filing_highlights", "Filing Highlights"),
    ("earnings_commentary_highlights", "Earnings & Management Commentary Highlights"),
    ("demand_bookings_backlog_signals", "Demand, Bookings, Backlog & Product-Cycle Signals"),
    ("insider_ownership_context", "Insider & Ownership Context"),
    ("bull_case_evidence", "Bull-Case Evidence"),
    ("bear_case_evidence", "Bear-Case Evidence"),
    ("contradictions_and_uncertainty", "Contradictions & Uncertainty"),
    ("catalyst_calendar", "Catalyst Calendar"),
    ("technical_price_context", "Technical / Price Context (context only)"),
    ("valuation_context", "Valuation Context (context only)"),
    ("key_risks", "Key Risks"),
    ("what_would_confirm_thesis", "What Would Confirm the Thesis"),
    ("what_would_invalidate_thesis", "What Would Invalidate the Thesis"),
    ("open_questions", "Open Questions"),
    ("research_conclusion", "Research Conclusion"),
]

DISCLAIMER = (
    "This report is an evidence-organizing research aid. It is not investment advice and does not "
    "recommend buying, selling, or holding any security. All material factual claims are cited to a "
    "source or explicitly labeled unverified/estimate/insufficient evidence."
)


def brief_to_markdown(ticker: str, version: int, created_at: str, question: str, sections: dict[str, Any]) -> str:
    lines = [f"# Research Brief — {ticker} (v{version})", "", f"*Generated: {created_at}*", "", f"> {DISCLAIMER}", ""]
    if question:
        lines += [f"**Research question:** {question}", ""]

    for key, title in SECTION_TITLES:
        value = sections.get(key)
        if value in (None, "", [], {}):
            continue
        lines.append(f"## {title}")
        if key == "what_changed_recently" and isinstance(value, dict):
            for bucket, items in value.items():
                if not items:
                    continue
                lines.append(f"**{bucket.capitalize()}:**")
                for item in items:
                    lines.append(f"- {item}")
        elif isinstance(value, list):
            for line in _facts_or_strings(value):
                lines.append(f"- {line}")
        elif isinstance(value, dict):
            lines.append(f"- {fact_line(value)}")
        else:
            lines.append(str(value))
        lines.append("")

    sources = sections.get("sources_table") or []
    if sources:
        lines.append("## Sources")
        lines.append("| # | Type | Title | Source Date | Retrieved | Freshness | Identifier |")
        lines.append("|---|------|-------|--------------|-----------|-----------|------------|")
        for s in sources:
            lines.append(
                f"| {s['source_id']} | {s['source_type']} | {s['title']} | {s['source_date']} | "
                f"{s['retrieval_date']} | {s['freshness_status']} | {s['url_or_identifier']} |"
            )
        lines.append("")

    scorecard = sections.get("scorecard") or {}
    if scorecard:
        lines.append("## Scorecard")
        lines.append(f"**Total conviction score: {scorecard.get('total_score')}/5**")
        if scorecard.get("is_capped"):
            lines.append(f"*Capped: {scorecard.get('cap_reason')}*")
        lines.append("")
        lines.append("| Component | Weight | Raw Score | Weighted | Explanation |")
        lines.append("|-----------|--------|-----------|----------|-------------|")
        for c in scorecard.get("components", []):
            lines.append(
                f"| {c['label']} | {c['weight']:.2f} | {c['raw_score']}/5 | {c['weighted_score']:.2f} | {c['explanation']} |"
            )
        lines.append("")

    return "\n".join(lines)


def brief_to_html(ticker: str, version: int, created_at: str, question: str, sections: dict[str, Any]) -> str:
    def esc(s: Any) -> str:
        return _html.escape(str(s))

    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        f"<title>Research Brief — {esc(ticker)} v{version}</title>",
        "<style>body{font-family:-apple-system,Helvetica,Arial,sans-serif;max-width:900px;margin:2rem auto;"
        "padding:0 1rem;line-height:1.5;color:#1a1a1a} h1{margin-bottom:0} .disclaimer{background:#fff6e5;"
        "border:1px solid #e5c07b;padding:0.75rem 1rem;border-radius:6px;font-size:0.9rem} "
        "table{border-collapse:collapse;width:100%;margin:1rem 0} td,th{border:1px solid #ddd;padding:6px 8px;"
        "font-size:0.85rem;text-align:left} th{background:#f5f5f5} ul{margin-top:0.25rem}</style></head><body>",
        f"<h1>Research Brief — {esc(ticker)} (v{version})</h1>",
        f"<p><em>Generated: {esc(created_at)}</em></p>",
        f"<div class='disclaimer'>{esc(DISCLAIMER)}</div>",
    ]
    if question:
        parts.append(f"<p><strong>Research question:</strong> {esc(question)}</p>")

    for key, title in SECTION_TITLES:
        value = sections.get(key)
        if value in (None, "", [], {}):
            continue
        parts.append(f"<h2>{esc(title)}</h2>")
        if key == "what_changed_recently" and isinstance(value, dict):
            for bucket, items in value.items():
                if not items:
                    continue
                parts.append(f"<h3>{esc(bucket.capitalize())}</h3><ul>")
                parts += [f"<li>{esc(i)}</li>" for i in items]
                parts.append("</ul>")
        elif isinstance(value, list):
            parts.append("<ul>")
            parts += [f"<li>{esc(line)}</li>" for line in _facts_or_strings(value)]
            parts.append("</ul>")
        elif isinstance(value, dict):
            parts.append(f"<p>{esc(fact_line(value))}</p>")
        else:
            parts.append(f"<p>{esc(value)}</p>")

    sources = sections.get("sources_table") or []
    if sources:
        parts.append("<h2>Sources</h2><table><tr><th>#</th><th>Type</th><th>Title</th><th>Source Date</th>"
                      "<th>Retrieved</th><th>Freshness</th><th>Identifier</th></tr>")
        for s in sources:
            parts.append(
                f"<tr><td>{s['source_id']}</td><td>{esc(s['source_type'])}</td><td>{esc(s['title'])}</td>"
                f"<td>{esc(s['source_date'])}</td><td>{esc(s['retrieval_date'])}</td>"
                f"<td>{esc(s['freshness_status'])}</td><td>{esc(s['url_or_identifier'])}</td></tr>"
            )
        parts.append("</table>")

    scorecard = sections.get("scorecard") or {}
    if scorecard:
        parts.append(f"<h2>Scorecard</h2><p><strong>Total conviction score: {esc(scorecard.get('total_score'))}/5</strong></p>")
        if scorecard.get("is_capped"):
            parts.append(f"<p><em>Capped: {esc(scorecard.get('cap_reason'))}</em></p>")
        parts.append("<table><tr><th>Component</th><th>Weight</th><th>Raw Score</th><th>Weighted</th><th>Explanation</th></tr>")
        for c in scorecard.get("components", []):
            parts.append(
                f"<tr><td>{esc(c['label'])}</td><td>{c['weight']:.2f}</td><td>{c['raw_score']}/5</td>"
                f"<td>{c['weighted_score']:.2f}</td><td>{esc(c['explanation'])}</td></tr>"
            )
        parts.append("</table>")

    parts.append("</body></html>")
    return "\n".join(parts)
