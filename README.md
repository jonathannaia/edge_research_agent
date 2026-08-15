# EevaResearch AI

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

Two independent parts, kept deliberately separate:
1. **Manual Research** (sections 1–4 below) — you drive it: add tickers, generate briefs, review.
   Zero LLM calls, zero ongoing cost.
2. **Radar** (section 5) — a fully autonomous scanner, scoped to four fixed niches (AI Buildout,
   Humanoids, Space, Macro/Rates/Policy), that runs on a schedule with no human approval per
   finding. Costs a small, bounded amount per month once you turn it on (see section 5).

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
                           (mock_providers.py) + registry.py (mock/live provider selection) +
                           edgar_client.py (shared SEC EDGAR client) + live_edgar.py (live US
                           fundamentals/filings)
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
  radar/                   Autonomous scanner — separate feature, see section 5. feeds.py (RSS +
                           SEC EDGAR search sources), keyword_filter.py / freshness.py (free
                           pre-filters), llm_tagger.py (Claude Haiku 4.5 tagging),
                           ticker_registry.py (SEC ticker verification), store.py (JSON
                           persistence), analytics.py (trend aggregation), notifier.py (optional
                           webhook), scan.py (orchestration)
scripts/run_radar_scan.py  CLI entrypoint the GitHub Actions workflow calls
.github/workflows/         radar_scan.yml — the scheduled job that runs Radar
tests/                     pytest suite (see section 6)
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

Set `EDGE_DATA_MODE=live` in `.env` to turn on live fundamentals and filings for **US and South
Korea tickers** — `src/providers/live_edgar.py` and `src/providers/live_dart.py` implement both
against SEC EDGAR's free, keyless APIs and Korea's DART API (requires a free registered key)
respectively, with a per-ticker fallback to mock (still correctly labeled) if the live source has
no data for a given ticker. `registry.py` routes each call by the ticker's jurisdiction; every
other domain (price, transcripts, insiders, ownership, earnings calendar, news) is still mock-only,
and Japan/China/Hong Kong filings are still mock too (see below).

**Korean tickers are DART's 6-digit exchange stock codes** (e.g. `005930` for Samsung
Electronics), not letter symbols — that's what to enter as the ticker when adding a South
Korea-jurisdiction watchlist entry.

### Filings beyond the US

Every ticker carries a `jurisdiction` field (set via the dropdown on the Watchlist page: United
States, Japan, South Korea, China, Hong Kong, or Other). `SourceType`'s regulatory-filing category
is deliberately jurisdiction-agnostic — a live `FilingsProvider` branches on the ticker's
jurisdiction to call the matching regulator. US and South Korea are live; the rest were researched
directly (not assumed) and are each blocked for a specific, different reason:

| Jurisdiction | Regulator / system | Status |
|---|---|---|
| United States | [SEC EDGAR](https://www.sec.gov/edgar/sec-api-documentation) | **Live.** Free, keyless — just a compliant `User-Agent`. |
| South Korea | [DART / OpenDART](https://opendart.fss.or.kr/) | **Live**, given a free registered key (`EDGE_DART_API_KEY`). Verified against real data (Samsung Electronics) — filings, fundamentals, and year-over-year revenue growth all confirmed correct, including for quarterly/semi-annual reports (see `src/providers/live_dart.py`'s module docstring for the two real bugs this caught and fixed). Filings are in Korean; no translation step built yet. |
| Japan | [EDINET](https://api.edinet-fsa.go.jp/api/auth/index.aspx?mode=1) API v2 | Free official API, but requires registering an account with **phone number verification** to get an API key — an account-creation step that has to be done by a human, not automated. Filings are in Japanese; no translation step built yet. |
| China | CNINFO / SSE / SZSE | **No official public API exists at all.** The only options are scraping undocumented endpoints or a paid third-party vendor — scraping would violate this project's own "never scrape in a way that violates a site's terms of service" principle, so it isn't wired up. |
| Hong Kong | [HKEXnews](https://www.hkexnews.hk/) | Public and login-free to browse, but its search is a stateful Java web form (session/viewstate-based) — confirmed by direct inspection — not a documented API. Would require reverse-engineering a fragile, unsupported endpoint. |

**To unblock Japan:** register a free account yourself (needs a phone number for verification —
a few minutes), then set `EDGE_EDINET_API_KEY` in `.env`. Not built yet, for the same reason DART
wasn't built blind: this project doesn't write untested client code against API shapes it can't
verify against real responses — DART only got built once a real key existed to verify it against
(see `scripts/dart_smoke_test.py`, a manual GitHub Actions workflow used to confirm it against
live data without ever exposing the raw key). Two things to plan for once a non-English regulator
is wired up: (1) translation isn't built in, and the original-language text should be preserved
alongside any translation for auditability; (2) each system's rate limits and terms of use differ
from SEC EDGAR's and should be reviewed
independently.

---

## 5. Radar — the autonomous scanner

Radar is a **separate feature** from everything above: it's a fully autonomous, always-on scanner
that watches free news/press sources for four fixed niches — **AI Buildout, Humanoids, Space, and
Macro/Rates/Policy** — tags any tickers involved (US and international), writes a short cited
summary, and surfaces it in the app with **no human approval in the loop**. It runs on its own
schedule and never touches your Watchlist, theses, or research briefs, and nothing you do in the
manual workflow affects it either.

It is held to the same guardrails as the rest of the app:
- **24-hour freshness gate, hard-enforced** — an item must have a publish timestamp within the last
  24 hours (`EDGE_RADAR_MAX_AGE_HOURS`, default 24) or it's dropped before it ever reaches the LLM.
  An item with no parseable publish date is dropped too — unknown age is treated as stale, not
  assumed fresh. This runs first, for free, ahead of every other filter.
- **Cited by construction** — every finding links to its source article; there's no free-floating
  claim, because the finding *is* a summary of that one article.
- **No advice language, hard-enforced** — every LLM-generated summary is run through
  `guardrails.language_filters.enforce_no_advice_language()` before it's ever saved; anything that
  fails is discarded and logged, not shown.
- **Ticker tagging cross-checked, not trusted outright** — US tickers the LLM tags are verified
  against SEC EDGAR's free ticker registry (`src/radar/ticker_registry.py`); the app labels each
  tag "verified" or "unverified" rather than presenting every guess as confirmed. Non-US tickers
  are always labeled unverified — no equivalent free registry is wired up for them yet.
- **Fully auditable** — every scan run (feeds checked, items within the freshness window, items
  sent to the LLM, items saved, items rejected by the guardrail, any errors) is recorded in
  `data/radar_state.json` and visible in the "Scan run history" expander at the bottom of the Radar
  page. An **overdue-scan banner** on that page fires if the last recorded run is more than 3x the
  expected 2-hour cadence old — a signal the scheduled job stopped firing silently.
- **Cost-bounded** — a hard cap (`EDGE_RADAR_MAX_ITEMS_PER_RUN`, default 25) on how many candidate
  items get an LLM call per run; a free, zero-cost keyword pre-filter runs first so only plausibly
  relevant items reach that cap.

### What it captures and where from

For each item that survives the freshness gate and keyword pre-filter, Claude Haiku 4.5 is given
**only the item's title and RSS snippet** (never the full article body — no scraping) and asked to
judge relevance, tag any concretely-implicated public company, and write a 1–2 sentence factual
summary grounded only in that text. The result: headline, summary, niche, source link, ticker
tag(s) with jurisdiction and verified/unverified status, and timestamps.

Sources are the entire crawl surface — Radar never follows links off these or discovers new sources
on its own. All hand-picked and URL-verified before being added (`src/radar/feeds.py`):

| Niche | Sources |
|---|---|
| AI Buildout | Data Center Dynamics, Data Center Knowledge, Semiconductor Engineering, NVIDIA Newsroom, TechCrunch AI, IEEE Spectrum AI, **+ SEC EDGAR full-text search** for real 8-K filings mentioning data-center capex (capped at 8/run — see below) |
| Humanoids | IEEE Spectrum Robotics, The Robot Report |
| Space | NASA News Releases, SpaceNews, Ars Technica Space, Space.com |
| Macro / Rates / Policy | Federal Reserve press releases, European Central Bank press, Bank of Japan press (English), Bank of England news |

The SEC EDGAR entry is not RSS — it's a live full-text search (`src/providers/edgar_client.py`,
free and keyless, same API `live_edgar.py` uses) for real 8-K filings mentioning data-center capex,
filed in roughly the last 2 days. Its findings carry a **confirmed filer straight from the filing
itself**, not an LLM's guess at who a news story is about — the strongest-grounded ticker tags
Radar produces. Capped at the 8 most relevant hits per run so one broad-matching source can't crowd
out every other feed's share of the per-run LLM budget.

### Cross-referenced against your Watchlist, and trend views

Radar isn't just a separate feed you have to remember to check:
- **Ticker Detail** has a "Radar Mentions" tab showing any findings that tag the currently selected
  ticker.
- The **Radar** page has a "Watchlist only" filter to see just what's relevant to tickers you're
  already tracking.
- The **Radar Trends** page aggregates the findings history — mentions per day, per niche, and the
  most-mentioned tickers over a selectable 7/14/30-day window — instead of only a flat
  reverse-chronological list.

### Optional: webhook notifications

Set `EDGE_RADAR_WEBHOOK_URL` (as a GitHub Actions repo secret, same place as `ANTHROPIC_API_KEY`)
to a Slack/Discord/Mattermost incoming webhook URL, and Radar posts a one-message digest of each
run's new findings. **This is not filtered to your Watchlist** — the scan job runs in GitHub
Actions, which only has the checked-out repo; your Watchlist lives in `data/edge_research.db`, a
local SQLite file that's gitignored and never committed, so the job has no way to see it. Left
unset (the default), nothing is sent — this is genuinely inactive infrastructure, not a hidden
default-on notification.

### Architecture — why no new database

Radar's scanner runs in **GitHub Actions** (free on a public repo) on a schedule
(`.github/workflows/radar_scan.yml`, every 2 hours by default), completely separate from the
Streamlit process. Rather than standing up a hosted database to bridge the two, the scan job simply
**writes `data/radar_findings.json` and `data/radar_state.json` and commits them back to the repo**.
Streamlit Cloud re-pulls the repo on redeploy/reboot, so the app always reads the latest committed
findings straight off disk — zero new infrastructure, zero extra accounts beyond the ones you
already have.

```
GitHub Actions (cron)              Streamlit app
  fetch RSS feeds        ─┐
  keyword pre-filter      │        reads data/radar_findings.json
  Claude Haiku 4.5 tag ───┼──git──▶ and data/radar_state.json
  guardrail check          │        straight off disk — no DB, no API call
  commit + push findings ─┘
```

### Setup

1. **Get an Anthropic API key** if you don't already have one, from the Anthropic Console.
2. In your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**,
   name it `ANTHROPIC_API_KEY`, and paste the key. This is the *only* secret Radar needs — every
   data source it reads (RSS feeds) is free and keyless.
3. The workflow is already committed and will start firing on its schedule automatically. To test
   it immediately instead of waiting up to 2 hours: **Actions tab → Radar scan → Run workflow**.
4. Open the app's **Radar** section (separate from Manual Research in the sidebar) to see results
   once a run has completed.

Nothing above touches your local `.env` — `ANTHROPIC_API_KEY` there is only needed if you want to
run `python -m scripts.run_radar_scan` locally yourself.

### Cost

RSS feeds and GitHub Actions are free. The only recurring cost is Claude Haiku 4.5 calls
(`$1.00 / $5.00 per 1M input/output tokens`) — at the default cadence (every 2 hours, capped at 25
tagging calls per run) this runs in the ballpark of **$15–30/month**, and scales down automatically
on quiet news days since the keyword pre-filter and per-run cap both reduce how much gets sent to
the model. Lower `EDGE_RADAR_MAX_ITEMS_PER_RUN` or widen the cron interval in
`.github/workflows/radar_scan.yml` to spend less.

### Adding or changing sources

Every feed Radar reads is listed explicitly in `src/radar/feeds.py` — there's no open-ended
crawling or link-following. Add a `Feed(name, url, niche, source_type)` entry to add a source;
niche must be one of the four values in `src/radar/models.py::Niche`. A broken feed is logged as an
error in that run's audit record and skipped — it never fails the whole scan.

### Limitations

- Findings are based on RSS title/snippet only — Radar does not fetch or read full article bodies
  (keeps it simple and avoids scraping/ToS concerns), so summaries are necessarily brief.
- Ticker tagging is the model's best-effort judgment from short text; it's instructed to omit a
  ticker rather than guess, but always verify against the linked source before relying on it.
- The `data/radar_findings.json` file is capped at the 500 most recent findings and
  `data/radar_state.json`'s run history at 200 runs — older entries roll off automatically so the
  repo doesn't grow unbounded.

---

## 6. Tests

```bash
python -m pytest -q
```

Covers: scorecard weighting/normalization and the evidence-quality cap, risk-warning generation,
citation validation (including the "missing both source_id and label" failure case), source
authority ranking and conflict resolution, thesis confirmation/invalidation signal logic, and
snapshot change-detection bucketing (confirming/disconfirming/neutral/new-unknowns).

---

## 7. Known limitations

- **Legal/compliance**: SEC EDGAR access requires a compliant `User-Agent` and reasonable request
  rates — read EDGAR's fair-access policy before wiring a live filings provider. Never scrape a
  site in a way that violates its terms of service; several "typical live source" cells above call
  this out explicitly.
- **Technical**: single-user, single-SQLite-file design — no concurrent-write support, no
  multi-user auth. Fine for personal local use, not for a shared deployment as-is.
- **Data quality**: mock mode is synthetic by construction; live mode is only as good as the
  providers you connect. The evidence-quality score is a partial mitigation, not a guarantee.
- **Cost**: the manual research pipeline makes zero LLM calls and no browser automation; only Radar
  (section 5) calls an LLM, and its cost is bounded as described there. Live-mode data-provider
  calls in the manual pipeline are bounded by `EDGE_MAX_SOURCES_PER_BRIEF` /
  `EDGE_MAX_EXCERPTS_PER_SOURCE`, but a paid data vendor will still bill per call — check your
  plan's limits before pointing this at a large watchlist.
- **Alerts** are local-only and only run when you click the button in-app — there is no background
  scheduler and no external notification channel for the manual pipeline (Radar has its own
  schedule — see section 5).

---

## 8. Roadmap

- **V1 (this repo)**: local watchlist, thesis records, single-ticker research briefs, transparent
  editable scorecard, snapshot-based change detection, local alerts/review queue, Markdown/HTML
  export, mock data providers, full audit log, and Radar — a separate autonomous scanner for AI
  buildout / humanoids / space / macro news with ticker tagging.
- **V2**: live compliant data providers (SEC EDGAR first), richer source ingestion (manual PDF/
  transcript paste with excerpt tagging), local desktop notifications, optional narrowly-scoped
  LLM narrative polish (rewrite-only, over already-cited text, with the same guardrails re-checked
  post-hoc), and expanding Radar's sources beyond RSS (e.g. a financial-news API) once cost/value
  is validated against the free-tier version.
- **V3**: optional hosted deployment (multi-user auth, concurrent-write storage), collaborative
  research (shared watchlists/notes), deeper change detection (NLP-assisted management-language
  tone tracking across calls), and custom integrations.
