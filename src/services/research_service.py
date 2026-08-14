"""Orchestrates single-ticker research brief generation.

Pipeline: fetch bounded data from providers -> persist each item as a cited
Source (+ excerpts) -> assemble a ResearchContext of already-cited evidence
-> compute the scorecard -> assemble brief sections as Fact-shaped dicts ->
validate citations (guardrail #1) -> validate no-advice language on our own
synthesized narrative (guardrail #7) -> diff against the prior snapshot ->
persist brief + snapshot + scorecard, all inside one transaction, all logged
to audit_logs (guardrail #9).

Every provider call and every excerpt saved is bounded by
settings.max_sources_per_brief / max_excerpts_per_source (guardrail #10) —
this is intentionally not an open-ended crawl.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import date
from typing import Any, Optional

from src.config.settings import Settings
from src.guardrails.citation_validator import CitationError, validate_brief
from src.guardrails.language_filters import enforce_no_advice_language
from src.guardrails.source_hierarchy import ExcerptRef, resolve_conflict
from src.models.models import BottomLine, ConfidenceLevel
from src.providers.registry import get_provider_bundle
from src.scoring.context import EvidenceItem, ResearchContext
from src.scoring.scorecard import compute_scorecard
from src.services import audit_service, settings_service, snapshot_service, source_service, watchlist_service

BULL_TAGS = {"bullish", "demand", "margin", "product_cycle"}
BEAR_TAGS = {"bearish", "risk", "dilution"}


def _fact(text: str, source_id: Optional[int] = None, label: Optional[str] = None) -> dict:
    return {"text": text, "source_id": source_id, "label": label}


def _build_context(conn: sqlite3.Connection, settings: Settings, ticker: str) -> ResearchContext:
    providers = get_provider_bundle(settings)
    ctx = ResearchContext(ticker=ticker.upper())

    fundamentals = providers.fundamentals.get_fundamentals(ticker)
    ctx.fundamentals = fundamentals
    ctx.fundamentals_source_id = source_service.save_source(
        conn, ticker, "Regulatory Filing", fundamentals.source_title,
        fundamentals.source_url_or_identifier, fundamentals.source_date,
    )
    ctx.all_source_dates.append((ctx.fundamentals_source_id, fundamentals.source_date))

    filings = providers.filings.get_recent_filings(ticker, limit=settings.max_sources_per_brief)
    for filing in filings:
        source_id = source_service.save_source(
            conn, ticker, "Regulatory Filing", f"{filing.filing_type}: {filing.title}",
            filing.url_or_identifier, filing.filing_date,
        )
        ctx.all_source_dates.append((source_id, filing.filing_date))
        for text, tag in filing.highlights[: settings.max_excerpts_per_source]:
            source_service.save_excerpt(conn, source_id, text, tag)
            ctx.evidence.append(EvidenceItem(text, tag, source_id, "Regulatory Filing", filing.filing_date))

    commentary = providers.transcripts.get_latest_commentary(ticker)
    if commentary:
        source_id = source_service.save_source(
            conn, ticker, "Earnings Call Transcript", commentary.event_label,
            commentary.url_or_identifier, commentary.event_date,
        )
        ctx.all_source_dates.append((source_id, commentary.event_date))
        for text, tag in commentary.quotes[: settings.max_excerpts_per_source]:
            source_service.save_excerpt(conn, source_id, text, tag)
            ctx.evidence.append(EvidenceItem(text, tag, source_id, "Earnings Call Transcript", commentary.event_date))

    news_items = providers.news.get_recent_news(ticker, limit=settings.max_sources_per_brief)
    for item in news_items:
        source_id = source_service.save_source(
            conn, ticker, item.source_type, item.title, item.url_or_identifier, item.published_date,
        )
        ctx.all_source_dates.append((source_id, item.published_date))
        source_service.save_excerpt(conn, source_id, item.snippet, item.tag)
        ctx.evidence.append(EvidenceItem(item.snippet, item.tag, source_id, item.source_type, item.published_date))

    insider_txns = providers.insiders.get_insider_transactions(ticker, limit=settings.max_sources_per_brief)
    for txn in insider_txns:
        source_id = source_service.save_source(
            conn, ticker, "Insider/Ownership Filing", f"Form 4 — {txn.insider_name} ({txn.transaction_type})",
            txn.url_or_identifier, txn.filing_date,
        )
        ctx.all_source_dates.append((source_id, txn.filing_date))
        ctx.insider_source_ids.append(source_id)
    ctx.insider_txns = insider_txns

    ownership = providers.ownership.get_ownership_summary(ticker)
    if ownership:
        ctx.ownership = ownership
        ctx.ownership_source_id = source_service.save_source(
            conn, ticker, "Ownership Data", f"Ownership summary as of {ownership.as_of_date}",
            ownership.source_url_or_identifier, ownership.as_of_date,
        )
        ctx.all_source_dates.append((ctx.ownership_source_id, ownership.as_of_date))

    price = providers.price.get_price_context(ticker)
    if price:
        ctx.price = price
        ctx.price_source_id = source_service.save_source(
            conn, ticker, "Reputable Financial News", f"Market price/volume snapshot as of {price.as_of_date}",
            f"MOCK-MARKET-DATA-{ticker.upper()}", price.as_of_date,
        )
        ctx.all_source_dates.append((ctx.price_source_id, price.as_of_date))

    valuation = providers.price.get_valuation_context(ticker)
    if valuation:
        ctx.valuation = valuation
        ctx.valuation_source_id = source_service.save_source(
            conn, ticker, "Reputable Financial News", f"Valuation snapshot as of {valuation.as_of_date}",
            f"MOCK-VALUATION-DATA-{ticker.upper()}", valuation.as_of_date,
        )
        ctx.all_source_dates.append((ctx.valuation_source_id, valuation.as_of_date))

    earnings = providers.earnings_calendar.get_next_earnings(ticker)
    if earnings:
        today_iso = date.today().isoformat()
        ctx.next_earnings_date = earnings.next_earnings_date
        ctx.earnings_source_id = source_service.save_source(
            conn, ticker, "Investor Relations Page",
            f"Earnings calendar entry ({'confirmed' if earnings.is_confirmed else 'estimated'})",
            f"MOCK-EARNINGS-CAL-{ticker.upper()}", today_iso,
        )
        ctx.all_source_dates.append((ctx.earnings_source_id, today_iso))
        existing = conn.execute(
            "SELECT id FROM catalysts WHERE ticker = ? AND catalyst_date = ? AND description = ?",
            (ticker.upper(), earnings.next_earnings_date, "Next earnings release"),
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO catalysts (ticker, description, catalyst_date, status) VALUES (?, ?, ?, 'upcoming')",
                (ticker.upper(), "Next earnings release", earnings.next_earnings_date),
            )

    return ctx


def _sources_table(conn: sqlite3.Connection, ctx: ResearchContext, settings: Settings, today_iso: str) -> list[dict]:
    seen_ids = sorted({sid for sid, _ in ctx.all_source_dates})
    table = []
    for sid in seen_ids:
        row = source_service.get_source(conn, sid)
        if not row:
            continue
        age_days = (date.fromisoformat(today_iso) - date.fromisoformat(row["source_date"])).days
        table.append(
            {
                "source_id": sid,
                "source_type": row["source_type"],
                "title": row["title"],
                "source_date": row["source_date"],
                "retrieval_date": row["retrieval_date"],
                "url_or_identifier": row["url_or_identifier"],
                "freshness_status": settings.freshness_status(age_days),
                "age_days": age_days,
            }
        )
    return table


def generate_research_brief(conn: sqlite3.Connection, settings: Settings, ticker: str, question: str) -> dict[str, Any]:
    ticker = ticker.upper()
    today_iso = date.today().isoformat()

    ctx = _build_context(conn, settings, ticker)
    weights = settings_service.get_score_weights(conn)
    scorecard = compute_scorecard(ctx, settings, weights, today_iso)

    evidence_component = next(c for c in scorecard.components if c.key == "evidence_quality_freshness")
    n_sources = len({sid for sid, _ in ctx.all_source_dates})
    insufficient = evidence_component.raw_score <= 1 or n_sources < 2

    if insufficient:
        bottom_line = BottomLine.INSUFFICIENT_EVIDENCE
        confidence = ConfidenceLevel.LOW
        confidence_explanation = (
            "Too few or too low-quality primary sources were available to support a bull, bear, "
            f"or mixed conclusion ({n_sources} source(s) reviewed). Treat this as a data gap, not a signal."
        )
    else:
        if scorecard.is_capped:
            confidence = ConfidenceLevel.LOW
        elif scorecard.total_score >= 4.0:
            confidence = ConfidenceLevel.HIGH
        elif scorecard.total_score >= 2.75:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

        if scorecard.total_score >= 3.5:
            bottom_line = BottomLine.BULLISH_SETUP
        elif scorecard.total_score <= 2.25:
            bottom_line = BottomLine.BEARISH_SETUP
        else:
            bottom_line = BottomLine.MIXED_SETUP

        cap_note = f" {scorecard.cap_reason}" if scorecard.cap_reason else ""
        confidence_explanation = (
            f"Total conviction score {scorecard.total_score:.1f}/5 across {n_sources} source(s), "
            f"evidence quality/freshness scored {evidence_component.raw_score}/5.{cap_note}"
        )

    bull_evidence = ctx.evidence_with_tag(*BULL_TAGS)
    bear_evidence = ctx.evidence_with_tag(*BEAR_TAGS)

    contradictions: list[str] = []
    if bull_evidence and bear_evidence:
        refs = [
            ExcerptRef(e.source_id, e.source_type, e.source_date, e.tag, e.text)
            for e in (bull_evidence + bear_evidence)
        ]
        _winner, explanation = resolve_conflict(refs)
        contradictions.append(explanation)

    open_questions: list[str] = []
    if not ctx.evidence:
        open_questions.append("No filing, transcript, or news evidence was found for this ticker in the current mock dataset.")
    if ctx.ownership is None:
        open_questions.append("No ownership/insider ownership summary was available.")
    if evidence_component.raw_score <= 2:
        open_questions.append("Evidence set is sparse and/or stale — more primary sources are needed before treating this as high confidence.")
    if not ctx.next_earnings_date:
        open_questions.append("No confirmed upcoming catalyst date was found.")

    research_conclusion = (
        f"{bottom_line.value}, {confidence.value.lower()} confidence. "
        f"This reflects a rules-based read of the cited evidence below, not a prediction — "
        "it is not investment advice and does not constitute a buy, sell, or hold recommendation."
    )
    enforce_no_advice_language(research_conclusion, context="research_conclusion")
    enforce_no_advice_language(confidence_explanation, context="confidence_explanation")

    sources_table = _sources_table(conn, ctx, settings, today_iso)
    stale_count = sum(1 for s in sources_table if s["freshness_status"] in ("stale", "very_stale"))

    fundamentals_facts = []
    if ctx.fundamentals:
        f = ctx.fundamentals
        sid = ctx.fundamentals_source_id
        fundamentals_facts = [
            _fact(f"Revenue {f.revenue:,.0f} ({f.period_label}), {f.revenue_yoy_growth:+.1%} YoY.", sid),
            _fact(f"Gross margin {f.gross_margin:.1%} vs {f.gross_margin_prior_year:.1%} prior year.", sid),
            _fact(f"Operating margin {f.operating_margin:.1%}.", sid),
            _fact(f"Free cash flow {f.free_cash_flow:,.0f}.", sid),
            _fact(f"Cash and equivalents {f.cash_and_equivalents:,.0f}; total debt {f.total_debt:,.0f}.", sid),
            _fact(f"Shares outstanding YoY change {f.shares_outstanding_yoy_change:+.1%}.", sid),
        ]

    sections = {
        "bottom_line": bottom_line.value,
        "confidence_level": confidence.value,
        "confidence_explanation": confidence_explanation,
        "thesis_summary": question or f"General inflection research on {ticker}.",
        "what_changed_recently": {},  # filled in below after snapshot diff
        "verified_evidence": [_fact(e.text, e.source_id) for e in ctx.evidence],
        "fundamentals_snapshot": fundamentals_facts,
        "filing_highlights": [_fact(e.text, e.source_id) for e in ctx.evidence if e.source_type == "Regulatory Filing"],
        "earnings_commentary_highlights": [
            _fact(e.text, e.source_id) for e in ctx.evidence if e.source_type == "Earnings Call Transcript"
        ],
        "demand_bookings_backlog_signals": [
            _fact(e.text, e.source_id) for e in ctx.evidence_with_tag("demand", "product_cycle")
        ],
        "insider_ownership_context": (
            [
                _fact(
                    f"{t.transaction_type} — {t.insider_name} ({t.role}): {t.shares:,.0f} shares, ${t.value_usd:,.0f}, filed {t.filing_date}.",
                    sid,
                )
                for t, sid in zip(ctx.insider_txns, ctx.insider_source_ids)
            ]
            + (
                [
                    _fact(
                        f"Institutional ownership {ctx.ownership.institutional_ownership_pct:.0%}, "
                        f"insider ownership {ctx.ownership.insider_ownership_pct:.0%} as of {ctx.ownership.as_of_date}.",
                        ctx.ownership_source_id,
                    )
                ]
                if ctx.ownership
                else []
            )
        ),
        "bull_case_evidence": [_fact(e.text, e.source_id) for e in bull_evidence],
        "bear_case_evidence": [_fact(e.text, e.source_id) for e in bear_evidence],
        "contradictions_and_uncertainty": contradictions,
        "catalyst_calendar": (
            [_fact(f"Next earnings expected {ctx.next_earnings_date}.", ctx.earnings_source_id)]
            if ctx.next_earnings_date
            else [_fact("No confirmed catalyst date available.", label="unverified")]
        ),
        "technical_price_context": (
            [
                _fact(
                    f"CONTEXT ONLY: Last price ${ctx.price.last_price:.2f}, 52-week range "
                    f"${ctx.price.fifty_two_week_low:.2f}-${ctx.price.fifty_two_week_high:.2f}, "
                    f"{ctx.price.pct_change_3m:+.0%} 3-month change. {ctx.price.trend_note}",
                    ctx.price_source_id,
                )
            ]
            if ctx.price
            else []
        ),
        "valuation_context": (
            [
                _fact(
                    f"CONTEXT ONLY: EV/Revenue {ctx.valuation.ev_to_revenue}, peer median "
                    f"{ctx.valuation.peer_median_ev_to_revenue}, market cap {ctx.valuation.market_cap:,.0f}.",
                    ctx.valuation_source_id,
                )
            ]
            if ctx.valuation
            else []
        ),
        "key_risks": scorecard.risk_warnings + [_r.text for _r in ctx.evidence_with_tag("risk")],
        "what_would_confirm_thesis": "See thesis confirmation conditions on the ticker's thesis record.",
        "what_would_invalidate_thesis": "See thesis invalidation conditions on the ticker's thesis record.",
        "open_questions": open_questions,
        "research_conclusion": research_conclusion,
        "sources_table": sources_table,
        "data_freshness": {
            "n_sources": n_sources,
            "stale_or_very_stale_count": stale_count,
            "freshness_thresholds_days": {
                "fresh": settings.freshness_fresh_days,
                "aging": settings.freshness_aging_days,
                "stale": settings.freshness_stale_days,
            },
        },
        "scorecard": {
            "total_score": scorecard.total_score,
            "is_capped": scorecard.is_capped,
            "cap_reason": scorecard.cap_reason,
            "components": [asdict(c) for c in scorecard.components],
        },
    }

    validation = validate_brief(sections)
    if not validation.is_valid:
        audit_service.log_event(
            conn, "guardrail_block", {"reason": "citation_validation_failed", "errors": validation.errors}, ticker=ticker
        )
        raise CitationError(
            "Brief failed citation validation and was not saved: " + "; ".join(validation.errors)
        )

    version = (
        conn.execute("SELECT COALESCE(MAX(version), 0) AS v FROM research_briefs WHERE ticker = ?", (ticker,)).fetchone()["v"]
        + 1
    )

    prior_snapshot_row = conn.execute(
        "SELECT * FROM research_snapshots WHERE ticker = ? ORDER BY id DESC LIMIT 1", (ticker,)
    ).fetchone()

    new_snapshot_facts = snapshot_service.build_snapshot_facts(ctx, scorecard, bottom_line.value, evidence_component.raw_score)

    what_changed = {"confirming": [], "disconfirming": [], "neutral": [], "new_unknowns": []}
    if prior_snapshot_row:
        prior_facts = json.loads(prior_snapshot_row["snapshot_json"])
        what_changed = snapshot_service.compare_snapshots(prior_facts, new_snapshot_facts)
    sections["what_changed_recently"] = what_changed

    cur = conn.execute(
        """INSERT INTO research_briefs
            (ticker, question, version, bottom_line, confidence_level, confidence_explanation, sections_json, what_changed_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            ticker, question, version, bottom_line.value, confidence.value, confidence_explanation,
            json.dumps(sections), json.dumps(what_changed),
        ),
    )
    brief_id = cur.lastrowid

    conn.execute(
        "INSERT INTO research_snapshots (ticker, brief_id, snapshot_json) VALUES (?, ?, ?)",
        (ticker, brief_id, json.dumps(new_snapshot_facts)),
    )

    scorecard_cur = conn.execute(
        "INSERT INTO scorecards (ticker, brief_id, total_score, is_capped, cap_reason) VALUES (?, ?, ?, ?, ?)",
        (ticker, brief_id, scorecard.total_score, int(scorecard.is_capped), scorecard.cap_reason),
    )
    scorecard_id = scorecard_cur.lastrowid
    for c in scorecard.components:
        conn.execute(
            """INSERT INTO score_components
                (scorecard_id, component_key, label, weight, raw_score, explanation, citation_source_ids)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (scorecard_id, c.key, c.label, c.weight, c.raw_score, c.explanation, json.dumps(c.citation_source_ids)),
        )

    risk_flags = []
    if scorecard.is_capped:
        risk_flags.append("Low evidence quality")
    if any(c.key == "cash_flow_balance_sheet" and c.raw_score <= 2 for c in scorecard.components):
        risk_flags.append("Balance sheet / liquidity risk")
    if any(c.key == "risk_level_thesis_fragility" and c.raw_score <= 2 for c in scorecard.components):
        risk_flags.append("High thesis fragility")
    if stale_count > 0:
        risk_flags.append("Stale evidence")
    watchlist_service.update_risk_flags(conn, ticker, risk_flags)

    existing_watchlist = watchlist_service.get_watchlist_record(conn, ticker)
    if existing_watchlist:
        n_confirming = len(what_changed["confirming"])
        n_disconfirming = len(what_changed["disconfirming"])
        if insufficient:
            new_evidence_status = "Insufficient evidence"
        elif n_confirming > n_disconfirming:
            new_evidence_status = "Strengthening"
        elif n_disconfirming > n_confirming:
            new_evidence_status = "Weakening"
        else:
            new_evidence_status = "Unchanged"

        watchlist_service.upsert_watchlist_record(
            conn,
            ticker=ticker,
            tier=existing_watchlist["tier"],
            thesis_short=existing_watchlist["thesis_short"],
            why_on_watchlist=existing_watchlist["why_on_watchlist"],
            conviction_score=round(scorecard.total_score),
            evidence_status=new_evidence_status,
            next_catalyst=existing_watchlist["next_catalyst"] or "Next earnings release",
            next_catalyst_date=ctx.next_earnings_date or existing_watchlist["next_catalyst_date"],
            key_confirmation_metric=existing_watchlist["key_confirmation_metric"],
            key_invalidation_metric=existing_watchlist["key_invalidation_metric"],
            latest_material_change=f"Brief v{version}: {bottom_line.value} ({confidence.value} confidence).",
            reason=f"Auto-updated from research brief v{version}",
        )

    audit_service.log_event(
        conn,
        "research_brief_generated",
        {
            "brief_id": brief_id, "version": version, "bottom_line": bottom_line.value,
            "confidence": confidence.value, "total_score": scorecard.total_score, "n_sources": n_sources,
        },
        ticker=ticker,
    )

    return {
        "brief_id": brief_id,
        "version": version,
        "ticker": ticker,
        "sections": sections,
        "scorecard": scorecard,
        "what_changed": what_changed,
    }
