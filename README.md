# Edge Research Agent

A personal, evidence-first equity research tool for identifying and monitoring emerging business
inflections in underfollowed public companies — with a focus on AI infrastructure and adjacent
supply-chain beneficiaries (optical networking, data-center components, compound semiconductors,
power/cooling, and related industrial suppliers).

**This tool does not execute trades, move money, or give personalized investment advice.** It
organizes evidence, cites every material claim, tracks how a thesis changes over time, and tells
you what would confirm or invalidate it. You make all final investment decisions.

Runs entirely locally: Python + Streamlit + SQLite. Ships in **mock mode** by default — three seed
tickers (COHR, AAOI, AXTI) with clearly labeled synthetic data — so the whole app is usable with
zero API keys before you connect anything real.

---

## 1. Quick start

### macOS

```bash
cd edge_research_agent
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m src.database.seed      # creates data/edge_research.db and seeds COHR/AAOI/AXTI
python -m pytest -q              # optional: run the test suite
streamlit run app.py
```

> Use Python 3.12 (confirmed working) for the venv. Very new/beta Python versions (3.14+) don't yet
> have prebuilt wheels for `pyarrow`, a Streamlit dependency, and will fail to `pip install`.

### Windows (PowerShell)

```powershell
cd edge_research_agent
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m src.database.seed
python -m pytest -q
streamlit run app.py
```

Streamlit opens automatically at `http://localhost:8501`. The database file lives at
`data/edge_research.db` (created on first run) and is never sent anywhere — everything stays local.

To reset to a clean demo state, stop the app and delete `data/edge_research.db`, then re-run the
seed command.

---

## 2. Architecture

```
app.py                    Streamlit entry point / page router
src/
  config/settings.py      Env-driven config (Settings dataclass), no secrets hardcoded
  database/                schema.sql (DDL), db.py (connection mgmt), seed.py (demo data)
  models/models.py        Dataclasses + enums for every domain object (Tier, Source, Brief, ...)
  providers/               Abstract provider interfaces (base.py) + mock implementations
                           (mock_providers.py) + registry.py (mock/live provider selection)
  scoring/                 12-component scorecard: defaults.py (weights), context.py (cited
                           evidence bundle), component_scorers.py (per-component logic),
                           scorecard.py (weighting, caps, warnings)
  guardrails/               citation_validator.py, source_hierarchy.py, language_filters.py —
                           enforced as code, not just prompt instructions
  services/                 Business logic + persistence: ticker, watchlist, thesis, source,
                           research (the core brief-generation pipeline), snapshot (change
                           detection), alert, notes, audit, settings
  utils/                   export.py (Markdown/HTML brief export), formatting.py
  ui/                       One module per Streamlit page, plus components.py for shared widgets
tests/                     pytest suite (see section 5)
sample_data/               Mock fixtures for COHR, AAOI, AXTI (clearly marked fictional)
```

**Data flow for "Generate Research Brief":**

1. `research_service._build_context()` calls each provider (fundamentals, filings, transcripts,
   news, insiders, ownership, price, valuation, earnings calendar), bounded by
   `EDGE_MAX_SOURCES_PER_BRIEF` / `EDGE_MAX_EXCERPTS_PER_SOURCE`.
2. Every item returned is immediately persisted as a `Source` row (+ `SourceExcerpt` rows), so it
   has a citable ID before it's used anywhere else.
3. `scoring.scorecard.compute_scorecard()` scores all 12 components against that cited evidence.
4. The brief's sections are assembled entirely from cited `Fact` objects
   (`{text, source_id}` or `{text, label: "unverified"/"estimate"/"insufficient evidence"}`).
5. `guardrails.citation_validator.validate_brief()` walks every section and refuses to save the
   brief if any material claim is missing a citation or label — this is a hard gate, not a
   suggestion.
6. `guardrails.language_filters.enforce_no_advice_language()` hard-blocks the system's own
   synthesized narrative (never the quoted evidence itself) from containing buy/sell/hold/
   price-target language.
7. The brief, a normalized snapshot (for future diffing), and the scorecard are saved in one
   transaction; the new snapshot is diffed against the ticker's prior snapshot
   (`snapshot_service.compare_snapshots`) to produce "What Changed Since Last Review?".
8. Every step is logged to `audit_logs` (guardrail principle #9 — auditability).

### Why there's no LLM in the loop (V1 design choice)

Brief text is assembled by deterministic, rule-based synthesis over already-cited data — not
generated by a language model. This was a deliberate choice, not a shortcut: it makes "no
hallucination" structurally true rather than something to police, and it keeps V1's cost at
exactly zero model calls (guardrail principle #10). `src/prompts/` is scaffolded for a future,
narrowly-scoped LLM enrichment step (e.g. rewriting already-cited sentences for readability
without adding facts) — see the Roadmap.

---

## 3. Scoring system and its limitations

Twelve components (revenue growth, gross margin/operating leverage, cash flow & balance sheet,
guidance & earnings quality, bookings/backlog/customer, product cycle & partnerships, insider &
ownership, valuation context, technical/price context, catalyst strength, risk/thesis fragility,
evidence quality & freshness), each scored 1–5 (5 = most favorable), each with a weight editable
in **Scoring Settings**. Weights are normalized to sum to 1.0 however you set them.

```
total_score = Σ (normalized_weight_i × raw_score_i)   for i in the 12 components
```

Two hard rules layered on top:
- If **evidence quality/freshness** scores ≤2/5, the total is **capped at 2.5/5** and confidence
  is forced to Low, regardless of how favorable everything else looks.
- If **cash flow/balance sheet** or **risk/thesis fragility** scores ≤2/5, a prominent risk warning
  is generated and surfaced on the watchlist and in the brief.

**Limitations — read before trusting a score:**
- Component logic is **threshold-based, not a trained model** — it does not learn, and it can be
  wrong or naive about a given company's specific situation. Treat it as a structured way to read
  the evidence you already have, not an oracle.
- Scores are only as good as the underlying data. In mock mode, that data is synthetic. In live
  mode, it's only as complete as whatever providers you've wired up.
- The score is explicitly **not a prediction and not investment advice** — it never maps to a
  buy/sell/hold action or a price target, by design (see Guardrails page in-app).
- Weight changes apply going forward; historical briefs keep the weights that were active when
  they were generated (stored per-scorecard) so past conclusions stay auditable.

---

## 4. Data Provider Integration Guide — mock → live

V1 ships **mock providers only** (`src/providers/mock_providers.py`), driven by
`sample_data/mock_{cohr,aaoi,axti}.json` for the three seed tickers and deterministic synthetic
data for any other ticker you add. Every mock value is labeled `is_mock=True` and every
identifier is prefixed `MOCK-` so it can never be mistaken for a real citation.

To go live for a given data domain: implement the matching interface from `src/providers/base.py`
in a new module, then wire it into `src/providers/registry.py` (one domain at a time — no
big-bang cutover). Each interface returns the same dataclass regardless of source, so nothing
downstream (scoring, guardrails, UI) needs to change.

| Domain | Interface | Typical live source | Notes |
|---|---|---|---|
| Filings | `FilingsProvider` | [SEC EDGAR full-text search & submissions API](https://www.sec.gov/edgar/sec-api-documentation) | Free. Requires a compliant `User-Agent` header identifying you (`EDGE_SEC_USER_AGENT`) and respecting SEC's fair-access rate limits. |
| Fundamentals | `FundamentalsProvider` | SEC EDGAR "company facts" API, or a fundamentals vendor | Free via EDGAR for as-reported figures; a vendor gives cleaner normalized data. |
| Insider transactions | `InsiderProvider` | SEC EDGAR Form 4 filings | Free, same access rules as filings. |
| Ownership | `OwnershipProvider` | 13F aggregation or a data vendor | 13F data is quarterly and lagged by design. |
| Transcripts | `TranscriptProvider` | A transcript vendor, or manually paste excerpts via the Sources page | No good free/compliant bulk source; manual entry is a legitimate V1 workflow. |
| Price/volume | `PriceProvider` | A market data vendor (free tier or paid) | Needed for the technical/valuation context sections. |
| Earnings calendar | `EarningsCalendarProvider` | A market data vendor or company IR page | |
| News/press releases | `NewsProvider` | A news API, or official company RSS/press feeds | Never scrape a site in a way that violates its terms of service. |

Set `EDGE_DATA_MODE=live` in `.env` once you've wired at least one live provider; `registry.py`
is the single place that decides mock vs. live per domain.

### Filings beyond the US

Every ticker carries a `jurisdiction` field (set via the dropdown on the Watchlist page: United
States, Japan, South Korea, China, Hong Kong, or Other). `SourceType`'s regulatory-filing category
is deliberately jurisdiction-agnostic — a live `FilingsProvider` should branch on the ticker's
jurisdiction to call the matching regulator:

| Jurisdiction | Regulator / system | Notes |
|---|---|---|
| United States | [SEC EDGAR](https://www.sec.gov/edgar/sec-api-documentation) | Free; compliant `User-Agent` required. |
| Japan | [EDINET](https://disclosure2.edinet-fsa.go.jp/) | Free; Financial Services Agency's disclosure system. Filings are in Japanese. |
| South Korea | [DART](https://opendart.fss.or.kr/) | Free with a registered API key from the Financial Supervisory Service. Filings are in Korean. |
| China | CNINFO / SSE / SZSE | Free public disclosure portals. Filings are in Simplified Chinese. |
| Hong Kong | [HKEXnews](https://www.hkexnews.hk/) | Free public disclosure portal for HKEX-listed issuers. |

None of these are wired up in V1 — all filings are mock data regardless of jurisdiction. Two things
to plan for before wiring a non-English regulator: (1) translation isn't built in, and the original-
language text should be preserved alongside any translation for auditability; (2) each system's
rate limits and terms of use differ from SEC EDGAR's and should be reviewed independently.

---

## 5. Tests

```bash
python -m pytest -q
```

Covers: scorecard weighting/normalization and the evidence-quality cap, risk-warning generation,
citation validation (including the "missing both source_id and label" failure case), source
authority ranking and conflict resolution, thesis confirmation/invalidation signal logic, and
snapshot change-detection bucketing (confirming/disconfirming/neutral/new-unknowns).

---

## 6. Known limitations

- **Legal/compliance**: SEC EDGAR access requires a compliant `User-Agent` and reasonable request
  rates — read EDGAR's fair-access policy before wiring a live filings provider. Never scrape a
  site in a way that violates its terms of service; several "typical live source" cells above call
  this out explicitly.
- **Technical**: single-user, single-SQLite-file design — no concurrent-write support, no
  multi-user auth. Fine for personal local use, not for a shared deployment as-is.
- **Data quality**: mock mode is synthetic by construction; live mode is only as good as the
  providers you connect. The evidence-quality score is a partial mitigation, not a guarantee.
- **Cost**: V1 makes zero LLM calls and no browser automation. Live-mode data-provider calls are
  bounded by `EDGE_MAX_SOURCES_PER_BRIEF` / `EDGE_MAX_EXCERPTS_PER_SOURCE`, but a paid data vendor
  will still bill per call — check your plan's limits before pointing this at a large watchlist.
- **Alerts** are local-only and only run when you click the button in-app — there is no background
  scheduler and no external notification channel in V1.

---

## 7. Roadmap

- **V1 (this repo)**: local watchlist, thesis records, single-ticker research briefs, transparent
  editable scorecard, snapshot-based change detection, local alerts/review queue, Markdown/HTML
  export, mock data providers, full audit log.
- **V2**: live compliant data providers (SEC EDGAR first), richer source ingestion (manual PDF/
  transcript paste with excerpt tagging), local desktop notifications, optional narrowly-scoped
  LLM narrative polish (rewrite-only, over already-cited text, with the same guardrails re-checked
  post-hoc).
- **V3**: optional hosted deployment (multi-user auth, concurrent-write storage), collaborative
  research (shared watchlists/notes), deeper change detection (NLP-assisted management-language
  tone tracking across calls), and custom integrations.
