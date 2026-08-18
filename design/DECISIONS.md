# Implementation decisions log

Running log of judgment calls made while implementing design/eevaresearch-brief.md
autonomously, per instruction to not stop and ask. Ordered chronologically.

## Pre-existing (from the foundation checkpoint, before this run)

- **Fact chip "must link to source"** vs. the project's standing rule of never
  fabricating external source URLs (everything is demo data attributed to
  "EevaResearch Demo Data," no real links): implemented the fail-loud check
  against source *attribution* (`has_source`/`source_name`) rather than a live
  URL. Same bug being guarded against (an unbacked Fact claim), without
  inventing a fake link.
- **Unread/last-seen persistence**: session-state only (`st.session_state`),
  since the app has no auth/user backend to persist "per user" against.

## This run

- **§11 signal drawer**: implemented with `st.dialog` (Streamlit's native
  modal) rather than a hand-rolled HTML/JS slide-over panel. It's a real
  Streamlit overlay primitive — opens over the feed without navigating away,
  closes via X/Esc, doesn't fight the non-goal against custom JS where a
  native equivalent exists. Visually centered rather than right-edge-
  anchored; functionally identical otherwise. Verified interactively:
  drawer renders all eight fields, "Save to watchlist"/"Open filing"/"Ask
  about this" footer actions present, and opening it clears that signal's
  unread dot immediately while a not-yet-opened signal in the same list
  stays unread — matches "mark read on drawer open, not hover."
- **Signal → Evidence linkage gap**: the `Signal` model has no literal
  source-excerpt field (only `evidence_count: int`). The drawer's Evidence
  section falls back to the first evidence item for the signal's first
  related ticker (via the existing `evidence_repository.get_evidence_for_ticker`
  call, not a new data-logic path) when available, else a plain "N demo
  evidence item(s) attributed — no individual excerpt in this phase" line.
- **CJK fallback needs real CJK content to verify**: added `excerpt_original`
  (+ `document_location`) as additive `EvidenceItem` fields, and gave two
  demo evidence rows (ev-002, ev-007) fabricated Japanese/Korean "original"
  text above their English translation, clearly still demo data, so the
  Source Serif 4 → CJK-fallback requirement has something real to render
  against rather than being unverifiable.
- **Unread badge rendering**: `st.page_link` only accepts a plain text
  label, no separate badge slot — the Signals nav item's unread count
  renders as inline text ("Signals · 2 unread") rather than a pill badge
  next to the label.
- **§12 command palette**: tested the real ⌘K/Ctrl+K shortcut before
  reaching for the sanctioned fallback, per the brief's own instruction —
  it genuinely works. A tiny `st.components.v1.html` snippet reaches into
  `window.parent.document` (same-origin, allowed) to attach the listener
  and `.click()` a real Streamlit button by its `st-key-*` class; verified
  interactively opening the dialog from a page with no prior focus.
  Live filtering, grouped results, and click-to-navigate all verified
  working end-to-end in the browser (typing "photon" correctly narrowed to
  the DEMO company and clicking it opened the Company page). What's
  genuinely not buildable without a custom React component (ruled out by
  "stays Streamlit, no React"): distinguishing a literal Enter-to-open
  keypress from a blur inside `st.text_input` (both just commit the same
  way), and intercepting ↑/↓/⌘↵ while a Streamlit widget has focus. So:
  search commits on Enter-or-blur (not per-keystroke), an explicit "Open
  top result ↵" button stands in for a literal Enter-key handler, and
  ↑/↓/⌘↵ are click/tap only. `Esc`-closes and focus-restore are `st.dialog`'s
  own native behavior, not reimplemented.
- **Themes/Capital-Rotation merge**: the brief's route table lists a single
  "Themes" route (no separate per-theme URL), so theme selection stays on
  the existing outer `st.tabs` (one per theme name) rather than becoming
  five routes — the required Map/Rotation/Companies/Catalysts tabs nest
  *inside* each theme's outer tab. "Related signals" isn't assigned to a
  specific tab by the brief; placed it in Rotation (pairs with "what's
  moving" narrative) rather than Map or Companies. Cross-theme rotation
  lives on the Dashboard panel (already built); within-theme rotation here
  reuses the same narrative-card pattern from the now-unrouted
  `capital_rotation.py` (kept on disk, not deleted, per the non-goal
  against deleting content — its Altair leaderboard chart wasn't reused
  since comparing all 5 themes belongs on the Dashboard panel, not inside
  a single theme's own tab).
- **§13 freshness**: since this build has zero live data sources connected
  anywhere, every panel genuinely renders "demo" in practice — Live/Stale
  are real, implemented code paths (`freshness_state()` classifies by fetch
  age) but aren't exercised until a real provider lands behind the existing
  repository interfaces (Phase 2). "Every panel header carries its own
  timestamp" is interpreted as the major data panels identified across the
  brief (Dashboard's four sections, Signals' page header, each theme's four
  tabs, Company's Key metrics/Recent signals/Thesis/Catalysts) rather than
  literally every st.write() on every page — a `panel_header()` helper
  keeps the label+chip pairing consistent everywhere it's used.
- **§14 empty states**: `empty_state()` rebuilt as a bordered card (title +
  detail + optional action button/link) instead of `st.info` (a blue
  accent box, incompatible with zero-accent-colour). The three exact
  copies from the brief are wired to their described contexts: empty
  watchlist tab, Dashboard's "New signals" panel when nothing is unread,
  and Research's first-visit empty state. "New thread"'s action focuses
  the chat composer via the same trusted parent-document JS pattern used
  for ⌘K, rather than being decorative. Skeletons (`skeletons.py`) are
  built to spec (shimmer, real row geometry) but not wired into any live
  loading path — this build's demo data loads synchronously, so there's no
  real latency to cover yet; a grep confirms zero `st.spinner` calls exist
  anywhere, so "never a bare spinner" holds trivially.
- **§15 watchlist enforcement**: verified the full loop end-to-end in the
  browser (not just code-reading) — opened the dialog from Company, Save
  stayed disabled with an empty field, typing enabled it, saved, then
  navigated in-app (sidebar link, not a raw URL reload) to Dashboard and
  saw the new entry's exact invalidation text surfaced under a "Moving
  against thesis" callout, because the ticker now has a Mixed-direction
  signal tied to it. Also closed a real enforcement gap found along the
  way: `watchlists.py`'s own inline "Add ticker" control used to add
  directly with no invalidation condition at all, bypassing the rule built
  everywhere else — it now routes through the same save dialog.
  Testing note for future browser checks in this app: a raw URL `navigate()`
  call in this harness starts a fresh Streamlit session (session_state
  resets), which looks identical to a working feature if the seeded
  defaults happen to match — only in-app link clicks (sidebar / page_link)
  preserve session state for verifying anything that isn't derived fresh
  from seed data every render.
- **§8 Home revisited**: rebuilt to match the brief's exact structure and
  copy, not the earlier looser approximation — 40px "Start with what was
  filed." headline, single 900px column (no sidebar), minimal top bar
  (logo + wordmark only), primary "Open Dashboard" + ghost "What this tool
  won't do" (anchor-scrolls to the limits section on the same page), the
  exact four limits and exact closing line from the brief. Removed the
  animated/decorative hero SVG and watermark entirely — the brief's Home
  spec doesn't include one, and §17 explicitly says to remove the
  watermark logo behind the hero. Verified the anchor-scroll link
  interactively.
- **§16 motion/texture verified**: film-grain parameters now match the
  brief's snippet exactly (140x140, numOctaves 3, opacity .03, z-index
  9998) — confirmed via computed-style inspection in the browser, applied
  to `.stApp::before` rather than `body::before` (body sits behind
  Streamlit's own app root in this version and doesn't reliably paint over
  the visible surface). Audited every `@keyframes`/`animation:` in
  styles.css: `dot-pulse` (live-dot pulse, reused identically across the
  sidebar status dot and freshness chips — one functional pattern, not a
  third instance), `fill` (breadth bars), and `skel-pulse` (skeleton
  shimmer, tightened from 1.6s to the brief's exact 1.4s — this one is
  explicitly sanctioned by §14 separately from §16's "exactly two"
  count for ambient/background motion). All three are gated inside
  `@media (prefers-reduced-motion: no-preference)`, with an explicit
  `reduce`-query fallback that hard-resets the two dynamic ones. Could not
  emulate `prefers-reduced-motion` directly in the browser tool available
  here to visually confirm the disabled state — verified by CSS review
  instead.
- **§17 Streamlit hygiene + logo + disclaimer footer**: confirmed via
  computed-style JS query that `#MainMenu`, `header`, and
  `[data-testid="stToolbar"]` are all present and `display:none` — the
  Deploy button and hamburger menu are visibly gone in the browser (they
  appeared in every earlier screenshot this session, absent from here on).
  `footer`, `[data-testid="stDecoration"]`, and `[data-testid="stStatusWidget"]`
  aren't present in the DOM at all in this Streamlit version — the hide
  rules stay in for those selectors anyway (harmless if the element never
  renders). Logo resized to 22px beside a 14.5px semibold wordmark. Added
  the fourth disclaimer placement — a "Disclaimer" link in every page
  footer — completing all four weights from the brief's table (Home limits
  section, Research composer line, first-session dismissible note, footer
  link). `page_title` kept as "EevaResearch AI" (not the brief's bare
  "EevaResearch") — that's the product's actual established name used
  throughout the codebase and tests; the brief's snippet reads as
  illustrative, not a rename instruction. `@st.cache_data` calls (the logo
  data-URI, seed-JSON loaders) are left without an explicit TTL — the data
  is static Phase-1 fixtures that never change at runtime, so no-TTL *is*
  the sensible choice for this data, not an oversight.
- **Signals absorbs watchlist filters**: sidebar watchlist links now carry
  real counts and set `?watchlist=<name>` on the Signals route; Signals
  resolves that against the same session-state watchlists used everywhere
  else and shows a "Filtered from the X watchlist (N names)" notice with a
  working Clear-filter button. Verified in the browser: clicking "Core
  Themes (1)" correctly narrowed Signals from 8 to 3 (every signal tied to
  DEMO, the list's one member).
- **Test suite audit**: `capital_rotation_page.py` and (previously)
  `watchlists_page.py` AppTest harnesses existed on disk but weren't
  referenced by any test — added a real smoke test for
  `watchlists_page.py` (still a reachable hidden route); left
  `capital_rotation_page.py` unreferenced since that page is now fully
  unrouted, superseded by the Dashboard panel + Themes Rotation tab.
  Added dedicated unit-test files for the two new pure-logic modules
  (`test_unread.py`, `test_watchlist_risk.py`) and new coverage in
  `test_evidence.py` (`cite_label`) and a new `test_evidence_chips.py`
  (the Fact-chip fail-loud behavior specifically, since that's the one
  place the brief calls a bug: "a Fact chip without a working source link
  is a bug — fail loudly in dev"). Full suite: 92 passed.

## Post-implementation gap sweep (before final acceptance report)

Re-read the brief's acceptance checklist line by line against the actual
app and found several real gaps the section-by-section pass missed. Fixed:

- **Sidebar "Recent research" group** was entirely missing — added, using
  this session's asked questions (research.py has no richer "thread"
  object than the question string itself).
- **Home-first-visit-only / Dashboard-default-thereafter** wasn't
  implemented — Home had `default=True` unconditionally. Fixed in app.py
  via a one-time `_has_visited` session flag that flips which page owns
  the root path; Dashboard keeps its own `/dashboard` url_path either way
  (`st.Page`'s `default=True` maps a page to root regardless of its own
  url_path, so both routes coexist correctly). Verified the flag-setting
  logic by code review; couldn't empirically re-trigger "second visit
  shows Dashboard at root" through the browser tool available here, since
  a raw URL navigate() in this harness starts a fresh Streamlit session
  (confirmed earlier, in the §15 note) — only in-app link clicks preserve
  session state, and the logo's own link always targets Home explicitly
  regardless of default state, so it can't be used to observe this
  specific behavior either.
- **"Every ticker links to a Company page"** wasn't actually true —
  signal cards' "Related: DEMO" text and watchlist-row ticker symbols were
  plain text. Made both real links (`company?symbol=...`), plus Company's
  own "Related peers" list. Verified by clicking through.
- **Panels had a visible 1px border** via Streamlit's native
  `st.container(border=True)` default, contradicting §5 ("Panels have no
  outer border; separation is by surface value") — confirmed via computed-
  style inspection, then overrode to `border: none` + `--r-md` radius,
  background-only separation. Two bordered containers had no `card-`
  prefixed key (so the override wouldn't have reached them) — gave both
  explicit keys.
- **Not every empty state had an action** — added sensible ones (View all
  signals / Open Dashboard / Read Methodology / Clear all filters, the
  last backed by giving the four Signals multiselects explicit keys so a
  callback can actually reset them) to every empty state on a routed page.
  Left two without an action on purpose: Themes' top-level "No themes
  loaded" (a data-load failure, not a "here's what to do next" state) and
  capital_rotation.py's (unrouted, not reachable).
- Fixed leftover round-2 accent-color hex values (green/rose) in
  `charts.py`'s Altair rotation chart — unreachable today (Capital
  Rotation is unrouted) but a literal grep-based "no hardcoded hex, no
  red/green" audit would still have flagged it, so brought it to the
  grayscale token palette for consistency.
- Verified via computed-style/JS checks (not just code review): spine
  correctly collapses to 2 columns with the chip moving inline below
  860px; layout has zero horizontal overflow at 1440px, 1280px, and
  1024px; no uppercase+mono section-header combination exists anywhere
  (the uppercase rules that do exist are all Inter, not mono).

## UX-refinement pass (post-restructure): navigation, Dashboard/Themes/
Signals/Research rework, copy layering, visual refinement

- **Copy-swap scope**: the brief gave five exact string replacements
  (`Demo placeholder interpretation text` → `Illustrative interpretation
  for this sample signal`, `Demo signal:` → `Sample signal:`, `View
  details` → `Review evidence`, `Open theme` → `Explore [Theme]`, `No
  research yet` → `Start a research thread`). Applied those exactly, plus
  a small number of directly-analogous instances not literally on the
  list but using the same "demo" vocabulary in the same visible surfaces
  (`company.py`'s bare badge → `demo_badge("Sample")`, watchlists.py's
  intro line, signal_drawer.py's "N demo evidence item(s)" line,
  research.py's "no sources attached" caption). Deliberately did **not**
  extend the swap to: the three sibling Signal fields
  (`contrary_evidence`/`validation_criteria`/`invalidation_criteria`,
  still "Demo placeholder ... — not real."), `chat_demo_answers.json`'s
  own placeholder prose (`what_happened`/`why_it_matters`/etc.), or the
  Live/Stale/Demo freshness-state vocabulary in `freshness.py` and
  methodology.py (that's a real 3-state system name, not throwaway
  copy). Also left `signal_drawer.py`'s "EevaResearch Demo Data"
  attribution string untouched — it's the tested source-safeguard
  string, not placeholder copy.
- **Streamlit's native page_link "current page" highlight matches by
  Page object, not query string** — discovered because the four
  Watchlist quick-filter links (`signals?watchlist=X`) all point at the
  same underlying Signals `Page`. Being anywhere on Signals lit up all
  four simultaneously plus the real Signals nav item, falsely implying
  every watchlist filter was active at once. Fixed by wrapping each in
  its own keyed container and stripping Streamlit's native highlight via
  CSS (`ui.py::render_sidebar`, `styles.css`) back to the plain nav-link
  look; hover still works.
- **`st.columns` stacks to a single column below ~640px** — this dropped
  the Signals unread-count badge (rendered via `st.columns([5, 1.4])`
  beside the page_link) onto its own row under the sidebar's narrow
  mobile width, since Streamlit's flex-wrap is `wrap` by default.
  Verified via computed-style inspection, then forced `flex-wrap:
  nowrap !important` on that one container's key
  (`.st-key-navitem-signals`) so the badge stays inline at every width.
- **Pre-existing bug found and fixed, unrelated to this pass's own
  edits**: three of the five canned Research answers
  (`chat_demo_answers.json`) had a `Fact`-type claim with empty
  `evidence`, which crashes `evidence_chips.UnlinkedFactChipError` (a
  guardrail requiring every Fact chip to cite a source) — so three of
  five suggested questions threw on click. These three claims are
  self-referential statements about where the app's own structured data
  lives ("The Memory theme page's Catalysts tab lists...") rather than
  sourced market facts, so reclassified them `Interpretation` instead of
  fabricating evidence — matches the existing working answer's pattern
  exactly. Verified by clicking all five suggested questions after the
  fix.
- **Button-styling inconsistency**: watchlists.py's "Remove" button was
  a bare `st.button` (Streamlit's own default look) while "Add" right
  next to it was wrapped in the app's `cta-secondary` styled-pill
  container. Wrapped Remove the same way so both share identical height/
  padding/radius.
- **Tab-jump-links dropped, not fake-implemented**: `st.tabs` can't be
  pre-selected from an external link/button click (confirmed hard
  Streamlit limitation, re-confirmed this pass). Themes' Theme Summary
  names which tab to check in prose ("Check the Rotation tab for the
  read...") instead of linking to it — user's explicit call over faking
  jump-buttons or rearchitecting tabs into session-state-driven
  segmented controls.
- Watchlists restored as a real standalone page (was folded into
  Signals-as-filters in the prior phase's plan) — user's explicit call;
  sidebar's "My Watchlists" group header is a real `st.page_link` to it,
  styled to read as a label via the same keyed-container CSS-targeting
  technique used elsewhere in this codebase for the same problem
  (Streamlit can't nest a widget inside a raw markdown div).

## Small-fix follow-up: sidebar visibility, content width, scan cues, footer/CTA consistency

- **Root cause of "sidebar not visible by default"**: Streamlit persists
  the sidebar's collapsed/expanded state in the browser's own
  localStorage, independent of Python session state, and it outlives
  `initial_sidebar_state="expanded"` — a sidebar collapsed once (in any
  earlier, unrelated visit to this origin) stays collapsed on every
  future fresh open, including at desktop widths. `initial_sidebar_state`
  only governs the very first visit ever to that browser origin. Fixed
  with a once-per-session check (`ui.py::_correct_sidebar_state_for_width`)
  that forces the sidebar to match the current viewport on load —
  expanded at ≥768px, collapsed below it — without re-forcing on every
  rerun, so a user who deliberately toggles it mid-session isn't fought.
  Verified by deliberately leaving the browser's localStorage in the
  "wrong" state for the next width tested and confirming the fresh load
  corrects it both directions (mobile→desktop and desktop→mobile).
- Also raised the collapse/expand control's contrast — Streamlit's
  default renders it at 60% text opacity, easy to miss against `--bg`.
- Widened `.block-container` from 1240px → 1360px (~10%) — kept short of
  a radical reflow; column/card layouts are unchanged, just less side
  margin at large widths.
- Theme Health cards gained a thin top rail in the same restrained
  pos/neg/mix accent as the status tag already below it (second, faster
  scan cue, not a replacement) — same per-instance injected-`<style>`
  technique `signal_card`/`priority_signal_row` already use to override
  the global `border: none` card rule.
- Capital Rotation: zero baseline bumped from `--hairline-2` (nearly
  invisible against the track) to `--text-4` at 2px; bars now tint
  pos/neg by sign via inline `style=` (wins over the class's plain
  `--text-2` without needing `!important`, since inline always beats an
  external class of equal specificity); added the
  "Relative performance · sample data" label under the section header.
  Underlying rotation-metric data/ranking logic untouched.
- Priority Signals: added the one-line subheading beneath the section
  header, no new scoring/filtering logic.
- **CTA sizing bug found and fixed**: `st.page_link`'s `<a>` and
  `st.button`'s `<button>` have different native padding/line-height, so
  the same "primary"/"secondary" tier rendered ~11-15px taller as a
  button than as a page_link, and a tertiary link sitting beside a
  secondary button in the same action row (e.g. cards.py's action_cols)
  looked vertically offset. Standardized both realizations of primary and
  secondary to one explicit box (`min-height`/`padding`/flex-centering);
  gave tertiary the same row height without giving it a border/pill, so
  it still reads as the lighter-weight action.
- Footer: full text now renders only on Methodology/Disclaimer (which
  already carry the same content in their own page body); every other
  page gets a one-line `"Evidence-first research · Sample data only ·
  Not investment advice"` summary instead, with the Disclaimer link still
  attached. `with_chrome` now threads `nav_key` into `render_footer` to
  make the branch. Split the old single `test_primary_page_renders_footer`
  parametrized test into two (full-footer pages vs. compact-footer pages)
  rather than weakening the assertion, so both variants stay covered.

## Final polish pass: spacing scale, action hierarchy, Dashboard → Market Overview

- Added a shared `--space-1`(4px) through `--space-8`(48px) scale in
  `:root` and rewired existing ad hoc margins (section labels, page title,
  footer, sidebar groups, metric label/value pairs, rotation rows, row
  padding) to reference it, per the user's explicit "use the design
  system, not per-page hard-coded margins" instruction.
- Card padding (the shared `[class*="st-key-card-"]` rule, so every card
  app-wide) tightened from a uniform 14px to `--space-3 --space-4`
  (12px/16px) — Today's Read specifically asked to not "consume
  unnecessary height," but a one-off override there would violate the
  same instruction, so the shared rule moved instead.
- **"Moving against thesis" treatment** — user gave an explicit
  clarification mid-pass after the first approval: not tiny low-contrast
  rose text alone, must use a rail/tag/dot + readable near-white text, no
  large or bright block. Implemented as `.er-alert-neg`: a 3px rose left
  rail + the existing `--neg-dim` tint (already used for status-tag pills
  elsewhere, so not a new color application) as the block background, a
  small rose dot + rose label, and the quoted invalidation note itself in
  `--text` (near-white) rather than muted. Verified at both 1280px and
  375px.
- Priority Signals' "01"/"02"/"03" order markers and the compact Review
  Evidence button are scoped to that one call site
  (`priority_signal_row`'s `order` param; a CSS rule keyed to
  `st-key-cta-secondary-priority-`) — Signals page's full `signal_card`
  and Watchlists' Add/Remove buttons, which reuse the same secondary-tier
  CSS, are intentionally unaffected.
- Catalyst row date badges gained a fixed `min-width` (`.er-date-badge`)
  so "Sep 5" and "Dec 25" align the same — shared by `catalyst_timeline_row`,
  so Dashboard's Next Catalysts, Themes' Catalysts tab, and Company's
  catalyst list all picked this up from one change.
- Sidebar: watchlist quick-filter entries get a scoped smaller/dimmer
  treatment (`text-3` + smaller font vs. Workspace's `text-2`/0.83rem) so
  they read as secondary to Workspace pages, per the brief; REFERENCE
  (Methodology, About) and all other IA left untouched, per explicit
  instruction not to move/hide/rename nav items this pass.
- "Dashboard" stays the sidebar nav label; only the on-page `<h1>`-style
  title changed to "Market Overview," matching the brief's own distinction
  between the nav item and the page heading.
- Skipped Theme Health's optional "why now" driver hint — no existing
  demo field supports it without inventing a fact, and the user's
  follow-up approval explicitly confirmed skipping it was correct.

## Korea DART radar pilot — milestone 1 (tracked-company registry + corp_code resolution)

First real-data phase of the app (Samsung Electronics + SK Hynix,
OpenDART/DART only, Memory + AI Buildout themes). Full pipeline is: raw
disclosure -> deduplicated FilingEvent -> rule-based CandidateSignal ->
human-reviewed status -> optional promotion to the existing curated Signal
model. Milestone 1 is scoped to the registry and the corp_code lookup
only — no scanning, no candidate rules, no translation, no UI yet; those
are later milestones once the user has added real API keys.

- **Caught a real contradiction before building anything**: the user's
  first answer's "DO NOT ADD" list explicitly excluded "Automated
  translation / External translation APIs," while their detailed
  translation answer in the same turn described a full machine-
  translation pipeline. Flagged it explicitly rather than guessing which
  instruction won — resolved in favor of building translation now
  (DeepL), confirmed by direct follow-up.
- **Verified every DART endpoint/field/status-code against OpenDART's own
  docs via WebFetch before writing client code** — not from training-data
  memory. This caught real details that would've been wrong guesses:
  `corpCode.xml` returns a ZIP on success but a plain XML *error* body
  (not a non-200 HTTP status) on failure, so `DartClient` distinguishes
  the two by checking for a ZIP-file signature (`b"PK"`) rather than
  trusting the HTTP status code alone. Status codes (000/010/011/012/013/
  014/020/021/100/101/800/900/901) are DART's own documented set, not
  guessed HTTP-style codes.
- **`corp_code` is deliberately never hardcoded anywhere in the
  registry** — `TrackedCompany.corp_code` defaults to `None`; it's filled
  in only by `corp_code_resolver.resolve_and_cache()` against a real
  OpenDART bulk-lookup call, cached to `data/cache/dart_corp_codes.json`
  (gitignored — added `data/cache/` to `.gitignore`). An ambiguous match
  (more than one bulk-file row for a given KRX code) is treated the same
  as "not found" — left unresolved rather than picking one arbitrarily,
  per the user's explicit "do not guess" instruction.
- `resolve_and_cache()` never raises — any `DartError` is captured into
  `ResolutionResult.error` and the function falls back to whatever was
  already cached, so one company's resolver failure can't wipe out a
  previously-resolved company.
- New models (`FilingEvent`, `CandidateSignal`, `Translation`,
  `CandidateStatus`) live alongside the existing demo models in
  `models.py` rather than a separate module — they're real dataclasses
  the rest of the type system should see, not a bolted-on side system.
  `CandidateSignal.excerpt_original` defaults to `None` (not `""`)
  specifically so the UI can distinguish "not parsed yet" from "genuinely
  no excerpt" — the None case is what triggers the required "Document
  available; excerpt parsing pending" message later.
- Added `requests` to `requirements.txt` (was only present as a
  transitive dependency of Streamlit before — pinning it directly since
  the DART client now depends on it explicitly, not incidentally).
- All 32 new tests (registry, client, resolver, models) are fully mocked
  — zero network calls, zero API key required, verified by running the
  suite with both `EDGE_DART_API_KEY`/`EDGE_TRANSLATION_API_KEY` unset.
- **Live-verified against the real API once keys were added**: resolved
  both companies against real OpenDART data — Samsung Electronics
  (005930) → `corp_code 00126380`, SK Hynix (000660) → `corp_code
  00164779` — cached to `data/cache/dart_corp_codes.json` (confirmed
  untracked by `git status`). Never printed either API key; only printed
  whether each was configured (True/False) and the resolution result.

## Korea DART radar pilot — milestone 2 (bounded scan + deterministic candidate rules)

- **Real correction, caught by pulling live data before writing the rule
  engine**: the original plan called for a "disclosure-type allowlist"
  keyed on `pblntf_ty`/`pblntf_detail_ty`. A live 90-day pull for both
  companies showed DART's `list.json` response does **not** echo either
  field per row — they're documented as search *filters*, not response
  fields. Rule-matching is keyword-driven against `report_nm` instead;
  `FilingEvent.pblntf_ty`/`pblntf_detail_ty` now default to `""` rather
  than being required fields. A type-filtered sweep (one search per
  `pblntf_ty` value) remains possible later if that granularity turns
  out to matter, at the cost of more API calls per scan.
- **Second correction from the same live pull**: DART returns status
  `"013"` ("no data found") for a search that legitimately matched
  nothing — not only for real errors. `search_disclosures` now returns
  an empty result for that status instead of raising, so a quiet 30-day
  window reads as "0 filings," not a false API-failure state. Every
  other non-`"000"` status still raises.
- **Keyword lexicon (`dart_rules.py`, `LEXICON_VERSION = "v1-2026-08"`)
  built primarily from that live pull**, not recalled from memory —
  every keyword is commented "observed live" or "standard, not observed"
  (a documented statutory major-event-report category that didn't happen
  to appear in the 90-day window) so the provenance of each entry is
  traceable. Ten categories: earnings, guidance, capex/facility
  investment, supply/sales contract, equity/JV investment, financing,
  listing/market event, ownership change, risk disclosure, market-rumor
  response — plus a routine-filing exclude list (insider ownership
  reports, IR-event announcements) that suppresses promotion regardless
  of any other match, since live volume showed these are procedurally
  constant and never material alone.
- Confidence is purely a count of independent matched categories (2+ =
  High, 1 = Moderate, 0 = None/stays a FilingEvent) — never a market
  judgment. An amendment marker (`[기재정정]`) is recorded as its own
  rule but can't push confidence up on its own, only alongside a real
  category match.
- Every promoted `CandidateSignal` lands as `NEEDS_TRANSLATION` (not
  `NEW_FILING` or straight to `NEEDS_REVIEW`) — this milestone has no
  translation step yet (that's the next one), so "needs translation" is
  the honest current state rather than implying it's ready for human
  review.
- `scan_service.scan()` retries only `DartRateLimitError`/
  `DartTimeoutError` (transient), bounded to 2 retries with linear
  backoff — a `DartParseError`/`DartApiError` fails immediately, since
  retrying the identical malformed request wouldn't help. Retry sleeps
  are monkeypatched to no-ops in tests so the suite stays fast.
- Idempotency is by DART's own `rcept_no` against an on-disk
  `seen_receipt_numbers` set (`data/cache/dart_filing_events.json`,
  gitignored) — a second scan of the same window produces zero new
  `FilingEvent`/`CandidateSignal` objects and reports the prior count via
  `already_seen_count` instead.
- `MAX_PAGES_PER_COMPANY = 5` (500 disclosures/company/scan ceiling) and
  `MAX_LOOKBACK_DAYS = 90` are grounded in real observed volume (SK
  Hynix: 58 total disclosures over a live 90-day window) rather than
  arbitrary round numbers.
- 35 new tests, all mocked (`unittest.mock`), zero network, zero API key
  — covering both real fixture-shaped scenarios and the specific
  failure modes above (malformed response, rate limit + retry, timeout +
  give-up, empty/"013" result, within-page duplicate receipt number,
  cross-scan idempotency, max-lookback clamping, per-company error
  isolation, unresolved-corp_code skip).

## Korea DART radar pilot — milestone 3 (document retrieval, extraction, translation)

- **Verified DART's real document package structure with one bounded live
  fetch before writing the parser** (SK Hynix, rcept_no 20260807000537 —
  a real treasury-stock-disposal major-event report): the ZIP holds
  exactly one UTF-8 `{rcept_no}.xml` file in DART's own DART4 schema
  (`<SECTION-1>` blocks, heavy `<TABLE>`/`<TR>`/`<TD>` nesting, not
  flowing prose). The first `<SECTION-1>` was the cover-page/company-info
  block; the second held the substantive content — that's the basis for
  `document_extractor.py`'s "skip section 1, extract from section 2
  onward" heuristic, documented in its module docstring as grounded in
  one real observation, not a guaranteed DART-wide schema promise, with
  every failure mode degrading to an explicit `ExtractionState` rather
  than a wrong guess.
- **Verified DeepL's real API shape via its own docs**, not memory:
  `POST /v2/translate`, `Authorization: DeepL-Auth-Key <key>` header, and
  — the detail that would've been easy to get wrong — free-tier keys
  carry a documented `:fx` suffix and *must* use `api-free.deepl.com`
  rather than the pro `api.deepl.com` host. `DeepLProvider` detects this
  from the key itself rather than needing a separate "which tier" field.
- **`ExtractionState` added as its own explicit field** on
  `CandidateSignal` (not left implicit in whether `excerpt_original` is
  `None`) — six states: Not fetched / Document available, extraction
  pending / Extracted / Unsupported format / Parse failed / Retrieval
  failed. `CandidateSignal` also split the single `translation` field
  into `title_translation` and `excerpt_translation` — different source
  texts with independent cache keys and failure states, so one can
  succeed while the other hasn't run or failed.
- Every retrieval/translation call in this milestone is for **one
  explicitly selected receipt number** — `document_service.py` and
  `translation_service.py` both cache by that ID (translation additionally
  by an excerpt hash) so a second request for the same filing/text never
  re-fetches, re-parses, or re-translates. A previously-*failed*
  retrieval is also cached (not just successes) so a known-unparseable
  document isn't retried on every view — but a previously-failed
  *translation* is deliberately **not** cached, so a transient DeepL
  failure can succeed on a later retry rather than being stuck.
- Bounded and defensive by construction: 8MB hard ZIP-size ceiling
  (rejected before parsing, not truncated), excerpts capped at 600
  characters, retry/backoff (2 retries, linear) only for genuinely
  transient failures (rate limit, timeout) on both the document and
  translation paths, and no code path that loops over multiple receipt
  numbers automatically — every call site takes exactly one ID.
- **End-to-end verified against the real pipeline once, bounded**: the
  same real filing fetched → extracted → translated through DeepL,
  confirming the whole chain (not just each mocked unit) works together.
  Never printed either API key; only printed the resulting Korean excerpt
  and English translation, which are legally-required public disclosure
  text, not sensitive data. Cache used a temporary directory for this
  check — nothing persisted to the real `data/cache/`.
- 36 new tests (extractor, document_service, DeepL provider, translation
  service, plus one models test), all mocked, zero network, zero API key.

## Korea DART radar pilot — milestone 4 (bounded orchestration pipeline)

- **`CandidateStatus` expanded from 7 to 16 values** to become the
  single authoritative lifecycle field the orchestrator advances through
  (New filing event → Candidate detected → Queued → Retrieval in
  progress → Extracted/Parse failed/Retrieval failed → Translation
  pending → Needs review → ... → Processing deferred). `extraction_state`
  and the new `translation_state` stay separate fields on
  `CandidateSignal` per the explicit "keep these concepts separate"
  instruction — `status` is the one-glance summary, the other two are
  the detailed sub-states. Added `ExcerptQuality` (descriptive shape
  metadata only, never materiality) and `StateTransition` (append-only
  audit trail, `CandidateSignal.state_history`).
- **Confidence labeling**: added `dart_rules.format_confidence_label()`
  (`"Detection confidence: Moderate"` rather than a bare `"Moderate"`) as
  the seam a future UI must call — no UI exists yet to consume it, so
  this is a documented contract, not yet exercised end-to-end.
- **Processing policy**: only candidates at Moderate/High detection
  confidence enter the document/extraction/translation pipeline (today
  this is every candidate the rule engine creates, since it never
  promotes below that bar — kept as an explicit, testable filter for
  forward-compatibility rather than assumed). Budget defaults to 5
  candidates/run, hard-clamped to a ceiling of 10
  (`clamp_max_candidates`, same pattern as `scan_service`'s lookback
  clamp). Candidates beyond the budget become `PROCESSING_DEFERRED`, not
  dropped — a new `candidate_store.py` persists every detected
  candidate's current state so a *later* pipeline run can find and
  finish a deferred one without needing scan_service to "rediscover" it
  as new (which it structurally can't, since dedup is by receipt
  number).
- **A real bug found and fixed via live verification, not a mock**:
  running the orchestrator against real current Samsung/SK Hynix filings
  (not just fixtures) showed 3/3 processed candidates landing in
  `PARSE_FAILED` — the DART4-schema extractor built in milestone 3 was
  verified against exactly one document type and didn't generalize.
  Investigation traced it to a 최대주주등소유주식변동신고서
  (major-shareholder-change report, real rcept_no 20260721801260):
  DART returns it as loosely-formatted HTML with a genuine mismatched
  closing tag, which `xml.etree.ElementTree`'s strict parser rejects
  outright. Fixed by adding a lenient fallback using Python's stdlib
  `html.parser.HTMLParser` (deliberately forgiving of malformed markup,
  skips `<script>`/`<style>` contents) when strict XML parsing fails —
  re-verified against the same real failing document, which now extracts
  correctly, then re-ran the full live pipeline end-to-end to confirm
  (3/3 extracted, 0 errors). `document_extractor.py`'s module docstring
  now documents both real cases explicitly, including which one required
  the fallback and why.
- **A second, smaller bug caught while investigating the first**:
  `candidate_store._candidate_from_dict` was reconstructing
  `state_history` entries by blindly splatting the raw JSON dict into
  `StateTransition(**h)`, leaving `status` as a plain string instead of
  converting it back to a `CandidateStatus` enum member — harmless
  within a single process (candidates are never reloaded mid-run) but
  would have broken on any future reload across separate runs. Fixed to
  explicitly reconstruct each transition's `status` via
  `CandidateStatus(h["status"])`.
- Cleared local `data/cache/dart_candidates.json`,
  `dart_document_excerpts.json`, `dart_filing_events.json`, and
  `translation_cache.json` after the bug above corrupted them with stuck
  `PARSE_FAILED` records (kept `dart_corp_codes.json`, expensive to
  regenerate and unaffected) — gitignored local pilot cache, not
  committed data, cleared as part of fixing the bug that corrupted it,
  then re-verified clean.
- Idempotency verified live, not just in mocks: running the same 30-day/
  2-company scan twice back-to-back showed `new_filing_events: 0`,
  `already_seen_count: 520` on the second run, with 3 of the 20
  previously-deferred candidates correctly picked up and processed
  (`candidates_deferred` dropping from 20 → 17) — confirming the
  "deferred candidate found by a later run" design works against real
  data, not only the mocked pipeline tests.
- 43 new tests (candidate_store, radar_pipeline's full scenario matrix,
  plus the extractor's new fallback-path tests), all mocked, zero
  network, zero API key.

## Korea DART radar pilot — milestone 5 (Radar Inbox UI)

- **New WORKSPACE sidebar page**: "Radar Inbox", positioned directly
  after Dashboard (`src/ui/ui.py`'s `PRIMARY_NAV`). It is the only page
  in the app backed by real, live data — every other page keeps reading
  from the demo `AppContext`. Kept deliberately separate wiring
  (`src/data_access/dart/radar_service.py`) rather than merged into
  `container.py`, so the live/demo boundary stays explicit and the rest
  of the app's data source is untouched.
- **Radar-specific status vocabulary** (`src/ui/components/radar_status.py`):
  "New filing" / "Candidate signal" / "Needs review" / etc — deliberately
  different wording and visual language from the curated Signal Board's
  own badges, per explicit instruction that a Radar item is a
  filing-driven research lead under review, never a completed market
  read. Two new CSS classes (`er-tag-neutral`, `er-tag-info`) added to
  `assets/styles.css`, built only from existing neutral tokens — no new
  hues, staying inside the zero-accent-color rule.
- **Three small, additive backend seams**, each filling a gap the UI
  genuinely had no way around (no rules/model/policy logic changed):
  - `scan_service.load_filing_events()` — reads back the full scanned-
    filing cache (not just candidates), needed for the "New filing"
    bucket (a filing the rule engine looked at and did not flag).
  - `radar_pipeline.process_single_candidate()` — an on-demand, single-
    explicit-candidate processing entry point for "Process now"/"Retry
    processing"; `_process_candidate` renamed to `process_candidate`
    (pure rename, same behavior) so both the budgeted `run_pipeline`
    loop and this new manual seam share one implementation. Deliberately
    bypasses `_ELIGIBLE_STATUSES` and the confidence filter — a manual
    click is an explicit user override, not a re-run of automatic
    eligibility policy.
  - `src/data_access/dart/retry_policy.py` — pure functions deriving
    retry eligibility (cooldown + max-attempt cap) entirely from
    `CandidateSignal.state_history`, which was already a complete
    timestamped audit trail — no new persisted field needed. Per
    explicit instruction, failed candidates are never auto-retried by a
    later scan; only a manual, capped, cooldown-gated click can retry
    them, addressing the milestone-4 retry limitation without widening
    `_ELIGIBLE_STATUSES`.
  - One naming reconciliation worth recording: the milestone brief's
    three retry-target statuses include `CandidateStatus.TRANSLATION_UNAVAILABLE`,
    which exists on the enum but the pipeline never actually sets as a
    candidate's status — a translation failure with successful
    extraction still lands at `NEEDS_REVIEW` with
    `translation_state=UNAVAILABLE`. `retry_policy.is_retryable()`
    checks that combination directly rather than a status neither
    pipeline stage ever produces.
- **Manual-only actions**: `Scan DART now` (bounded to the existing
  default/ceiling candidate budget), `Process now` (a deferred
  candidate), `Retry processing` (a failed one, gated by
  `retry_policy`) — no background jobs, no auto-refresh, no automatic
  retry. Every result renders as a safe counts-only summary
  (`ScanReport`'s own fields) — never raw provider responses or
  credentials.
- **Filters** (company/theme/status/date range/language/detection
  confidence) run entirely over the already-cached, already-persisted
  data (`scan_service.load_filing_events` + `candidate_store.load_candidates`)
  — no new live query capability. `FilingEvent.rcept_dt` is DART's raw
  `YYYYMMDD` string (confirmed by re-reading the real client/scan_service
  code, not assumed from the field's stale "ISO 8601" comment) — the
  date-range filter parses it explicitly as `%Y%m%d`.
- **Live verification note**: keys and cache data left over from
  milestones 1–4 were still present, so the page rendered real DART
  data (520 real filing events; 6 Needs review / 497 New filing / 17
  Processing deferred) in the Browser pane — confirmed the missing-
  configuration state, the live/demo indicator, real Korean titles +
  DeepL English translations, "Why flagged" rule phrases, and
  Process now/Retry button rendering, all against real cached data.
  Interactive filter-click verification in that same browser session
  was inconclusive: the browser's WebSocket to the local dev server
  intermittently disconnected (`Cannot send rerun backMessage when
  disconnected from server`), so a click's frontend-visible chip
  selection sometimes couldn't be confirmed reaching Python's
  `session_state`. The underlying filter logic itself was independently
  verified correct twice — a standalone script run directly against the
  real 520-item cache (producing the exact 6/497/17 split) and the
  fixture-driven `AppTest`-based render tests (a real Streamlit script
  execution harness, just without the browser/WebSocket layer) — so this
  is recorded as an unresolved *environment* verification gap, not a
  known defect.
- 8 new tests (`load_filing_events`, `process_single_candidate`,
  `retry_policy`'s cooldown/attempt-cap matrix, `radar_service`'s
  readiness/company-resolution checks, plus 2 AppTest-based Radar Inbox
  page render tests — missing-configuration state and a fully-seeded
  populated-list state), all mocked/fixture-based, zero network, zero
  API key.

## Korea DART radar pilot — milestone 6 (Radar Calibration: ownership materiality gate)

- **New, narrowly-scoped gate**: `src/data_access/dart/ownership_materiality.py`.
  Applies only to candidates whose `matched_rules` include an
  `ownership_change:` entry, and only after document extraction succeeds
  (it reads `excerpt_original`, which doesn't exist before that point) —
  wired into `radar_pipeline.process_candidate()`'s existing
  `extraction_state == EXTRACTED` branch, not into `dart_rules.py` or
  `scan_service.py` (title-only keyword detection is unchanged; the gate
  is strictly a post-extraction refinement of what happens next).
- **Two extraction patterns, both grounded in real cached excerpts**
  (Samsung rcept_no `20260724000625` and `20260721801260` — the exact
  two "probable false positive" candidates the Milestone 5 calibration
  report flagged): `_extract_daeryang_bogyu_delta` for
  대량보유상황보고서(일반)'s "직전 보고서 {n} {p} 이번 보고서 {n} {p}"
  shape, `_extract_choedae_jujoo_delta` for 최대주주등소유주식변동신고서's
  self-reported "증감 ... 합계 {n} {p}" delta line. Both real fixtures
  confirmed the two known false positives resolve to 0.00pp and 0.01pp —
  correctly below the 0.05pp pilot threshold.
- **Pilot threshold, explicitly not a financial rule**:
  `OWNERSHIP_MATERIALITY_THRESHOLD_PP = 0.05`, documented in the module
  docstring as a calibration setting, configurable via a parameter on
  `assess_ownership_materiality()`.
- **Material-marker exceptions — 4 of the 6 requested categories
  implemented, 2 deliberately omitted rather than guessed**:
  `controlling_shareholder_change` (최대주주변경, 경영권변동),
  `tender_offer` (공개매수), `pledge_or_collateral` (질권설정, 질권해지),
  `compulsory_acquisition_or_merger` (합병, 주식의포괄적교환, 완전자회사)
  — all standard, documented Korea securities-regulation terms, same
  "standard, not observed" convention as `dart_rules.py`'s own lexicon.
  `strategic_investment` and `major_new_beneficial_owner` were **not**
  added: the most obvious candidate term for the former, 제3자배정
  (third-party share allotment), is a capital-raise mechanism that
  would actually surface under the existing `financing` category, not
  `ownership_change`, so including it here risked a category-mismatched
  false grounding rather than a real one; no equally solid, unambiguous
  term was found for the latter either. Documented as an open gap rather
  than filled with a guess, per the milestone's own "do not guess
  Korean terms" instruction.
- **Terminal status reuse, not a new enum value**: routine ownership
  candidates now resolve to the existing (previously unused)
  `CandidateStatus.NOT_MATERIAL` instead of `NEEDS_REVIEW` — no new
  `CandidateStatus` value needed, keeping the change additive to the
  16-value lifecycle rather than expanding it.
- **New `CandidateSignal.materiality_assessment: str = "Not assessed"`
  field** — deliberately a narrow string note tied only to this one
  gate, never a general numeric materiality score, and left untouched
  for every non-ownership candidate (earnings/capex/financing/rumor-
  response) — confirmed via regression test.
- **UI**: `NOT_MATERIAL` gets a dedicated low-emphasis status-pill label
  ("Not material · routine ownership update", neutral/gray bucket,
  already-established from milestone 5); surviving ownership candidates
  show a "Potential materiality: {value}" secondary line in
  `radar_card.py` only when the field isn't at its default. No new
  filters, charts, or sections added — the existing dynamic Status
  filter picks up the new label automatically.
- 18 new tests (`test_ownership_materiality.py`'s full scenario matrix
  using both real cached excerpts and clearly-labeled constructed
  fixtures for the threshold-crossing/marker cases no real filing in
  this cache happens to exercise; `radar_pipeline` integration tests;
  a `CandidateSignal` field-default test; a Radar Inbox display test),
  all mocked/fixture-based, zero network, zero API key. Full suite:
  269/269 passing.

## Korea DART radar pilot — milestone 7 (one-candidate manual-processing validation)

- Used the existing `radar_service.process_candidate_now()` seam (the
  same function the Radar Inbox's "Process now" button calls) to process
  exactly one real, previously-`Processing deferred` Samsung ownership
  candidate (`cand-20260731801296`, 최대주주등소유주식변동신고서) end to
  end — one bounded, explicit real DART document fetch + one real DeepL
  translation call, no scan, no other candidate touched.
- **A real bug found and fixed via this validation, not a mock**: this
  filing's ownership *decreased* (증감 section: `-171,178 -0.01`), and
  `_extract_choedae_jujoo_delta`'s original regex only matched unsigned
  digits — it silently returned `None` on any decrease, falling through
  to the gate's "ambiguous extraction" default rather than actually
  parsing the real -0.01pp delta. The final classification for *this*
  candidate was accidentally still correct (both the real path and the
  fallback path land on "not material" for a 0.01pp change), which is
  exactly why a live end-to-end check — not just the unit tests, which
  had no negative-delta fixture — was needed to surface it: a real
  divestiture filing large enough to be genuinely material (e.g. -5pp)
  would have been silently misclassified as "ambiguous → not material"
  instead of correctly promoted. Fixed in two places: the regex now
  accepts an optional leading `-` on both the count and percentage
  groups, and `extract_ownership_delta_pp` now applies `abs()` once at
  its single dispatch point so every caller downstream always compares
  against the threshold by magnitude, never raw sign. 3 new regression
  tests added, including the exact real excerpt that exposed the bug.
- Confirmed via this same live run: idempotency (single read-modify-
  write into `candidate_store`, no duplicate `FilingEvent`/
  `CandidateSignal` created — 520/23 counts unchanged before and after),
  full state-history preserved and appended-to (not overwritten), and
  no other page's data touched (Dashboard/Signals/Themes/Capital
  Rotation/Watchlists all read exclusively from the demo `AppContext`,
  entirely separate from `data/cache/`).

## SEC EDGAR pilot — milestone 8 (second source, five-company cohort)

- **Second source, parallel module tree**: `src/data_access/edgar/`
  mirrors `src/data_access/dart/`'s shape file-for-file (`client.py`,
  `errors.py`, `cik_resolver.py`, `edgar_rules.py`, `scan_service.py`,
  `document_extractor.py`, `document_service.py`, `edgar_pipeline.py`,
  `edgar_service.py`) — DART's own modules are completely untouched in
  behavior; every DART call site keeps its exact existing signature.
- **Shared-model reuse, zero new fields where existing ones already
  fit**: `FilingEvent.source_name`/`original_language` already existed
  (unused, defaulting to `"OpenDART / DART"`/`"Korean"`) from an earlier
  milestone — reused directly for EDGAR (`"SEC EDGAR"`/`"English"`)
  rather than adding a duplicate field. `corp_code` holds a CIK for
  EDGAR records, `stock_code` holds the ticker, `rcept_no` holds the
  canonical dashed SEC accession number — documented as a dual-meaning
  invariant in `FilingEvent`'s own docstring, no field renamed. One
  genuinely new additive field, `primary_document: str = ""`, since
  EDGAR has no DART analog for "which file in this filing to fetch"
  (stays empty for every DART record, zero behavior change there).
  `TrackedCompany.corp_code` reused the same way for CIK; `krx_code`
  reused for ticker.
- **`candidate_store.py` and `dart/radar_service.py` each got one
  additive, DART-preserving change**: `candidate_store.py`'s four public
  functions gained an optional `filename` parameter defaulting to
  `dart_candidates.json` (DART's existing calls are byte-for-byte
  unchanged); EDGAR passes `edgar_candidates.json` explicitly so the two
  sources' candidate stores never mix on disk.
  `radar_service.get_radar_companies()` was changed to filter
  `get_tracked_companies()` down to `source == "OpenDART / DART"` only —
  necessary because the shared `TRACKED_COMPANIES` registry now also
  contains the 5 EDGAR entries; without this filter a DART scan would
  have started iterating EDGAR companies too. Caught via the full test
  suite (`test_tracked_companies.py`'s exact-cohort assertion failing)
  before it could reach any real behavior.
- **Real EDGAR API facts, verified via cross-confirming web search**
  (SEC.gov 403'd this session's direct-fetch tooling — see
  `client.py`'s module docstring): no API key, mandatory identifying
  User-Agent (`EDGE_EDGAR_USER_AGENT`, format `"AppName contact@email"`,
  else 403 + possible temporary IP block), `data.sec.gov/submissions/
  CIK##########.json`, and — the one real structural surprise —
  `filings.recent` is **columnar** (parallel arrays indexed by position),
  not an array of filing objects. `scan_service.normalize_recent_filings()`
  zips and validates this shape explicitly, failing safely (empty rows +
  a warning) on any missing/misaligned column rather than guessing.
- **Two-stage 8-K classification**, a real structural difference from
  DART: DART's title keyword match happens entirely at scan time (the
  full title is in the list response). EDGAR's filing-list metadata
  gives the form type but not which 8-K item(s) are present — those only
  exist inside the document text. So an 8-K gets a coarse
  `material_event_8k_pending_items` Moderate-confidence candidate at
  scan time, then `edgar_pipeline.process_candidate()` parses "Item
  X.XX" headers out of the extracted excerpt post-extraction
  (`edgar_rules.extract_item_numbers`/`refine_8k_evaluation`) and
  upgrades matched_rules/confidence — never demoting if no item number
  is found in the text.
- **CIK resolution is stricter than DART's corp_code resolution**:
  `cik_resolver.resolve_and_cache()` cross-checks each bulk-file
  candidate CIK against that CIK's own real submissions metadata (the
  ticker must appear in the filing's own reported `tickers` list) before
  accepting it — a candidate that fails this cross-check is left
  unresolved, never guessed forward. Required explicitly by the
  milestone-8 brief; DART's `corp_code_resolver.py` has no equivalent
  second-check step.
- **No ownership-materiality gate for EDGAR** (explicit instruction):
  `SC 13D`/`SC 13G` candidates are detected and routed like any other
  category, always reaching `NEEDS_REVIEW` on successful extraction —
  `ownership_materiality.py` is DART/Korean-document-shape-specific and
  is never called from `edgar_pipeline.py`.
- **No translation step at all**: EDGAR filings are native English —
  `translation_state` stays `TranslationState.NOT_REQUESTED` for the
  full lifetime of every EDGAR candidate; `title_translation`/
  `excerpt_translation` stay `None`. The Radar Inbox's "Machine
  translation" chip is already conditional on `title_translation is not
  None`, so this falls out for free with no UI branching needed.
  `dart_rules.format_confidence_label()` is reused as-is for EDGAR
  confidence labels — it's a plain string formatter with no DART-
  specific logic, despite living in that module.
- **Rate limiting**: pilot default 2 req/sec (well under SEC's published
  10/sec, more conservative than the DART pilot's own pacing), enforced
  as a blocking minimum-interval throttle inside `EdgarClient` itself so
  every caller gets it automatically. Retry/backoff for transient
  failures (429/timeout) lives one layer up (`scan_service.py`,
  `document_service.py`), bounded to 2 retries, exponential with jitter
  (`base * 2^attempt + random.uniform(0, 0.5)`) — DART's own retry was
  linear with no jitter; EDGAR's is deliberately more conservative per
  the milestone-8 brief's explicit instruction.
- **Radar Inbox**: two independently-bounded, separately-gated actions
  ("Scan DART now" / "Scan EDGAR now" — never a merged "scan
  everything"), a real populated Source filter, and
  `radar_card.py`/`radar_status.py` updated to read `filing.source_name`/
  `original_language` instead of a hardcoded `"OpenDART / DART"` string
  (a latent gap flagged during milestone-8 planning, fixed as a
  byproduct of this integration). The page now gracefully degrades:
  renders normally if *either* source is ready, only shows the
  missing-configuration empty state if *both* are unconfigured.
- **No live EDGAR verification performed this milestone**:
  `EDGE_EDGAR_USER_AGENT` is not present in the local `.env` (confirmed
  via `grep -c`, value never read/printed) — every EDGAR code path was
  exercised only via the 97 new fully-mocked tests. CIK resolution for
  the 5-company cohort, and the real `filings.recent` JSON shape, still
  need one live confirming pull once the User-Agent is configured — same
  "verify before trusting" step every DART milestone took before
  calling a new endpoint's behavior calibrated.
- 97 new tests across 9 new test files (`test_edgar_client.py`,
  `test_cik_resolver.py`, `test_edgar_rules.py`,
  `test_edgar_scan_service.py`, `test_edgar_document_extractor.py`
  — one real bug caught here: an all-empty-tags HTML document was
  incorrectly falling back to raw-markup-as-excerpt, fixed by gating the
  plain-text fallback on the absence of any `<` character —
  `test_edgar_document_service.py`, `test_edgar_pipeline.py`,
  `test_edgar_service.py`, plus dual-source additions to
  `test_tracked_companies.py` and `test_radar_inbox_page.py`), all
  mocked/fixture-based, zero network, zero User-Agent value required.
  Full suite: 373/373 passing (276 carried forward + 97 new); the 190
  DART-specific tests re-run in isolation all pass unchanged.

## SEC EDGAR pilot — Gates 1–4 (live verification + two real adapter fixes)

Four bounded, user-authorized live SEC passes followed milestone 8's
fixture-complete approval, each scoped to the minimum real requests
needed. Together they caught two genuine defects no fixture had
exercised — exactly the pattern the DART pilot's own live-verification
steps established repeatedly.

- **Gate 1 (CIK verification, 6 real requests)**: resolved and
  cross-checked all 5 cohort tickers against real SEC data — 100%
  success, no mismatches. Real confirmed CIKs recorded in
  `data/cache/edgar_ciks.json` (gitignored): NVDA `0001045810`, MU
  `0000723125`, COHR `0000820318`, ROK `0001024478`, RKLB `0001819994`.
- **Gate 2 (MU scan, 1 real request)**: MU's real 30-day window
  contained only Form 4 (insider transaction, ×3) and Form 144 (notice
  of proposed sale, ×2) — both correctly produced zero candidates
  (neither form is a configured category). Confirmed the columnar
  parser, dedup, and per-company isolation all work against real data
  with zero drift from the mocked tests.
- **Gate 3 (NVDA discovery, 1 real request)**: found a real 8-K
  (accession `0001045810-26-000069`, filed 2026-08-17) and, in the same
  pull, two real defects:
  1. `filings.recent` actually includes an `items` column per filing
     (verified value for this exact accession: `"1.01,2.03,7.01"`) —
     contradicting `edgar_rules.py`'s original documented assumption
     that item numbers only exist inside document text.
  2. SEC's real Schedule 13G value is `"SCHEDULE 13G"` (spelled out),
     not the abbreviated `"SC 13G"` `FORM_TYPE_CATEGORIES` was keyed on
     — a real NVDA SCHEDULE 13G in this same pull was silently missed
     as a result.
  Both were documented and left unfixed during the live pass itself
  (network access was already closed by then), per the user's explicit
  "stop and report, don't patch live" instruction.
- **Gate 4 (narrow fixture-backed repair, zero network calls)**: fixed
  both defects precisely:
  - `scan_service._OPTIONAL_COLUMNS` gained `"items"`; a new
    `edgar_rules.parse_items_metadata()` parses the real comma-separated
    format, preserving absence/malformed input as absence (never
    guessing) — reuses `EIGHT_K_ITEM_CATEGORIES` as the same allow-list
    `extract_item_numbers` already uses, no new categories invented. A
    new `scan_service._evaluate_row()` uses `refine_8k_evaluation()`
    directly at scan time when `items` is present and well-formed,
    falling back to the original coarse `evaluate_form_type()` path
    otherwise. `edgar_pipeline.py`'s existing post-extraction refinement
    step was deliberately left untouched — it's now an idempotent
    consistency check/fallback (re-applying the same items from document
    text is a no-op; it still helps when scan-time metadata was
    missing), not the only path to a refined classification.
  - New `edgar_rules.normalize_form_type()` + `_FORM_ALIASES` canonicalize
    both the abbreviated and spelled-out Schedule 13D/13G forms to the
    same lookup key — `FORM_TYPE_CATEGORIES`'s existing keys stay
    unchanged (abbreviated form remains canonical), so this is a pure
    input-normalization fix, not a lexicon rewrite.
  - The existing live-detected NVDA candidate
    (`edgar-cand-0001045810-26-000069`) was reclassified **in place**
    using the real `items` value already observed in Gate 3 (no new SEC
    request) — `Moderate` → `High` confidence,
    `material_event_8k_pending_items:8-K` →
    `material_agreement:8-K item 1.01` / `financing_or_debt:8-K item
    2.03` / `regulation_fd_disclosure:8-K item 7.01`. Status stayed
    `Candidate detected`; a new state-history entry documents the
    reclassification reason, appended (not replacing) the original
    entry. No duplicate FilingEvent/CandidateSignal created.
  - 26 new tests across `test_edgar_rules.py` (parse_items_metadata's
    full scenario matrix, normalize_form_type aliases, idempotency),
    `test_edgar_scan_service.py` (scan-time items wiring: valid/empty/
    missing/malformed/multi-item/no-duplication-on-rescan, real
    SCHEDULE 13G end-to-end), and `test_edgar_pipeline.py` (post-
    extraction idempotency both when scan-time already refined and when
    it fell back to coarse). Full suite: 399/399 passing; 190
    DART-specific tests re-run in isolation, unchanged.
- DART counts held at 520 FilingEvents / 23 CandidateSignals across all
  four gates. EDGAR ended at 10 FilingEvents / 1 CandidateSignal (MU's 5
  + NVDA's 5 filing events; the one NVDA 8-K candidate, now correctly
  classified). Demo pages never touched.
- **Next natural gate** (not yet authorized): one-candidate manual
  document processing for `edgar-cand-0001045810-26-000069` — the same
  "Process now"/"Retry processing" seam already built and tested for
  DART, applied to a real, now-correctly-classified EDGAR candidate for
  the first time.

## SEC EDGAR pilot — Gates 5–6 (real document processing + excerpt repair)

- **Gate 5**: `edgar_service.process_candidate_now()` invoked for real
  against `edgar-cand-0001045810-26-000069` — 1 real request, `200`, to
  the correctly-constructed archive URL
  (`.../data/1045810/000104581026000069/nvda-20260817.htm`). Extraction
  succeeded, translation stayed `NOT_REQUESTED`, no duplicate created.
  Surfaced a real evidence-quality gap: the 600-char excerpt captured
  only the 8-K's cover page (registrant name/address/state of
  incorporation) — zero Item 1.01/2.03/7.01 content — because a
  real 8-K's cover section alone can exceed the generic excerpt bound.
- **Gate 6 (EDGAR-only excerpt repair, no DART change, no size-constant
  increase)**: `document_extractor.extract_excerpt()` gained an
  additive, optional `expected_items: tuple[str, ...] = ()` parameter.
  When non-empty (8-K candidates with known items — from
  `edgar_rules.items_from_matched_rules()`), a new
  `_item_anchored_excerpt()` finds the first *expected* item header
  (via new `edgar_rules.iter_item_header_positions()`) and starts the
  excerpt there instead of the document start, under a new, separate
  `EIGHT_K_ITEM_EXCERPT_CHARS = 1200` cap — `MAX_EXCERPT_CHARS` (600)
  itself never changed, and every non-8-K/no-expected-items call keeps
  the exact original prefix-from-start behavior. Ends before the next
  Item header that is **not** itself one of the expected items — a real
  bug caught by the fixture suite before shipping: an earlier version
  stopped at *any* next header, truncating a multi-item filing
  (1.01/2.03/7.01 covered in adjacent sections) down to just the first
  item's text and silently dropping the confidence from High back to
  Moderate. Falls back to the first Item header of any kind if none of
  the expected ones are found (`"Expected item header not found..."`
  detail), and falls back further to the original prefix behavior if no
  Item header exists anywhere (`"Substantive excerpt unavailable..."`
  detail) — never guesses.
- **Reprocessing the real NVDA candidate hit a real architectural
  ceiling, disclosed rather than routed around**: this pipeline has
  never cached raw document bytes, only the already-bounded excerpt (see
  `document_service.py`'s own docstring) — so "reprocess the cached
  document" could only mean re-running the new logic against the
  already-cached 600-char text, which is 100% cover page with zero Item
  headers. Applying the fix there correctly and honestly falls to its
  own documented fallback path and changes nothing — verified this
  produces byte-identical output to before. The excerpt was left
  unchanged (per instruction: only update if genuinely improved); a new
  state-history entry documents the attempt and its outcome instead. A
  genuine improvement for this specific candidate needs one new bounded
  document fetch, not authorized this pass.
- 21 new tests (`test_edgar_document_extractor.py`'s full anchoring
  matrix — cover-page skip, EDGAR-cap bound, multi-item non-truncation,
  next-*unexpected*-item boundary, missing-expected-header fallback,
  no-header-at-all fallback, malformed spacing/casing, determinism —
  plus `items_from_matched_rules`/`iter_item_header_positions` unit
  tests in `test_edgar_rules.py`). Full suite: 413/413 passing; 190
  DART-specific tests re-run in isolation, unchanged.

## SEC EDGAR pilot — Gate 7 (real evidence-quality confirmation, zero code changes)

- One real request to the already-known primary document URL
  (`.../data/1045810/000104581026000069/nvda-20260817.htm`, `200`) —
  the Gate 6 fix, run for the first time against the real full document
  rather than a fixture, worked exactly as designed: found the real
  `Item 1.01` header at character 15309 (past ~15KB of front matter —
  far more than a typical cover page, a real reminder that "past the
  cover page" can mean a lot more than the cover page alone), extracted
  a genuinely substantive 1200-character excerpt — NVIDIA's real
  announced partnership with SB Energy Corp for an AI data-center
  campus in Portsmouth, Ohio (OpenAI as tenant), residual value
  guaranties capped at $105B — replacing the prior 600-character
  cover-page-only excerpt entirely.
- **A second real interaction surfaced, deliberately not fixed this
  pass**: the new 1200-char excerpt's own window only re-confirms Item
  1.01 (Items 2.03/7.01 sit further into the real document, past the
  cap). Running the existing post-extraction refinement
  (`extract_item_numbers` + `refine_8k_evaluation`) against this excerpt
  would have overwritten the candidate's correct 3-item/High
  classification (from Gate 4's complete real scan-time metadata) with
  an incomplete 1-item/Moderate one — a regression caused entirely by
  the excerpt's own bound, not a real change in what the filing
  contains. Avoided by updating only `excerpt_original` directly rather
  than routing through `edgar_pipeline.process_candidate()`'s full
  refinement step — `matched_rules`/`confidence`/`status` were left
  exactly as Gate 4 set them. This scan-time-metadata-vs-bounded-
  excerpt interaction is a real, now-documented gap for a future
  narrow fix (post-extraction refinement should probably only
  *add* categories found in the excerpt, never *remove* ones already
  confirmed from complete metadata) — flagged, not addressed, per this
  gate's explicit no-code-change scope.
- Both `data/cache/edgar_document_excerpts.json` (document_service's own
  cache) and `edgar_candidates.json` (the candidate's own
  `excerpt_original`) were updated consistently, so a future lookup of
  this same accession number won't silently revert to the stale
  boilerplate excerpt from either persisted view.
- Zero code/test changes this pass (confirmed via `git diff --stat`
  matching the pre-gate state exactly) — pure data validation.
- **EDGAR pilot status**: CIK resolution, scan-time classification (both
  fixes), the processing pipeline, translation isolation, dedup, DART
  isolation, and now evidence-excerpt quality are all real,
  live-verified, and correct for this one candidate. The one remaining,
  explicitly non-blocking-for-freeze item is the refinement/excerpt-
  bound interaction just described — a real but narrow, already-scoped
  fix for a later gate, not a reason to keep EDGAR unfrozen.

## SEC EDGAR pilot — Gate 8 (monotonic category merge, closes the last known gap)

- Closed exactly the gap Gate 7 flagged. New
  `edgar_rules.merge_8k_item_evaluation(scan_time_items, excerpt_items)`:
  `final_categories = scan_time_items UNION excerpt_items` — SEC
  scan-time item metadata (already reflected in a candidate's
  `matched_rules` entering `process_candidate`) is authoritative and is
  only ever *added to* by what a bounded document excerpt reaches,
  never replaced or shrunk by it. Reduces to the pre-existing
  document-only behavior when `scan_time_items` is empty (still coarse,
  or malformed scan-time metadata) — no regression for that path.
- `edgar_pipeline.process_candidate()` now captures `scan_time_items`
  from the candidate's own matched_rules *before* extraction, computes
  `excerpt_items` after, and merges — never a blind overwrite. Provenance
  is recorded in the final state-history transition's `detail` (at
  minimum, per the brief): which items came from scan-time metadata vs.
  were newly confirmed by the excerpt, or (rare) neither existed and the
  document alone drove classification. `matched_rules`' own string shape
  (`"category:8-K item X.XX"`) was deliberately left unchanged — no
  format migration, no knock-on test changes beyond the new scenarios.
- 11 new tests (6 unit tests on `merge_8k_item_evaluation` in
  `test_edgar_rules.py` covering the exact superset/subset/union/empty/
  order-independence/idempotency matrix the brief specified, plus 2
  integration tests in `test_edgar_pipeline.py` — one reproducing the
  real NVDA shape end-to-end confirming High confidence and all three
  categories survive a 1-item-only excerpt, one confirming reprocessing
  causes no category growth or duplicate records). All 413 pre-existing
  tests passed with zero modification — the merge is a strict
  generalization of the old behavior, not a breaking change. Full suite:
  421/421 passing; 190 DART-specific tests re-run in isolation,
  unchanged; `git diff --stat -- src/data_access/dart` empty (confirmed
  zero DART files touched).
- **Re-verified the real NVDA candidate directly against the new merge
  function, using only already-stored data (its own `matched_rules` and
  its own cached 1200-char excerpt) — no fetch, no re-run through the
  pipeline.** Result: identical to what was already stored (all three
  categories, High confidence) — Gate 7 had already avoided the bug by
  hand for this one candidate, so there was nothing to correct. No
  state-history entry appended (nothing to correct — an entry restating
  an already-accurate prior explanation would itself have been the kind
  of misleading transition the brief asked to avoid). Zero new
  FilingEvent/CandidateSignal; DART/EDGAR counts unchanged (520/23,
  10/1).
- **EDGAR pilot: all previously-identified gaps are now closed.**
  CIK resolution, both scan-time classification fixes (items metadata,
  form normalization), the processing pipeline, translation/DART
  isolation, dedup, real evidence-excerpt quality, and now monotonic
  category-merge correctness are all live-verified. No further
  known-but-deferred correctness issues remain on record for this
  5-company cohort.

## EDINET (Japan) pilot — planning Gate 0 (documentation verification only)

- SEC EDGAR frozen at its Gate 8 state (520/23 DART FilingEvents/
  CandidateSignals, 10/1 EDGAR); DART untouched throughout. EDINET
  scoped as the next source; TDnet deferred entirely pending a separate,
  explicit commercial-access/licensing decision — no TDnet code,
  config, env vars, UI, caches, tests, or tracked companies exist or are
  proposed anywhere in this project.
- Gate 0 was documentation-reading only: zero credential use, zero
  authenticated requests, zero files created/modified/deleted. Facts
  below are recorded exactly as the user approved them, split by
  provenance.
- **Confirmed directly from an official source** (Japan's e-Gov API
  catalog page): EDINET is operated by Japan's Financial Services Agency
  (FSA). EDINET is a REST API. Official response formats include JSON,
  ZIP, and PDF. The official guide lists EDINET API Specification
  Version 2 as updated **June 20, 2025** — this is the settled project
  fact; no other date (including this session's own earlier, incorrect
  "June 2026" search result) is recorded as fact or as "disputed."
- **Provisional — cross-confirmed from two independent secondary
  developer sources only, not read directly from the official spec PDF**
  (that PDF returned as a non-extractable compressed stream to this
  session's tooling): the `Subscription-Key` credential's naming and
  transport; the document-list endpoint and its `date`/`type`
  parameters; response-field shape (`results`, `docID`, `docTypeCode`,
  `ordinanceCode`, `formCode`, `filerName`, `docDescription`);
  document-retrieval type values and format mapping; the code-list
  endpoint/file shape; rate/fair-use limits, pagination, and the full
  error envelope. Every one of these is treated in code as "ready to use,
  not yet confirmed" — see Gate 1 below.

## EDINET (Japan) pilot — planning Gate 1 (fixture-complete adapter, zero live calls)

- Built the full parallel `src/data_access/edinet/` module tree,
  mirroring EDGAR's/DART's independence exactly: `__init__.py`,
  `errors.py`, `client.py`, `edinet_code_resolver.py`, `edinet_rules.py`,
  `scan_service.py`, `document_extractor.py`, `document_service.py`,
  `edinet_pipeline.py`, `edinet_service.py`. Zero live network calls,
  zero credential reads/validation, zero DART/EDGAR/TDnet files touched,
  zero companies added to `tracked_companies.py`.
- `EdinetClient` sends the `Subscription-Key` as a **query parameter**
  (the Gate-0-confirmed distinction from `EdgarClient`'s header-based
  `User-Agent`), maps HTTP 401/403/404/429/5xx/timeout to typed errors
  (`EdinetUnauthorizedError` and `EdinetNotFoundError` are new relative
  to EDGAR's own error set, since EDINET authenticates via a rejectable
  key rather than a header EDGAR never individually validates), and
  keeps document retrieval format-agnostic (`fetch_document` returns raw
  bytes, never asserting ZIP vs. PDF vs. CSV). `DEFAULT_MIN_INTERVAL_SECONDS
  = 3.0` is explicitly documented as provisional (sourced from a
  secondary developer's own self-imposed delay, not an official number).
- `edinet_code_resolver.py` and `edinet_rules.py` both hold a hard
  discipline line the user's approved plan drew explicitly: the
  code-list file's real URL/shape and any real EDINET
  ordinanceCode/formCode-to-category mapping were **not** confirmed even
  provisionally by Gate 0, so neither module hardcodes a guessed real
  value as fact. `edinet_code_resolver.py`'s URL/column-map constants
  and `edinet_rules.py`'s `DEFAULT_CODE_CATEGORY_MAP` (intentionally
  empty) are explicit, clearly-labeled placeholders; with the real
  empty default, `scan()` today produces FilingEvents but zero
  CandidateSignals from any real EDINET data — the honest Gate 1
  behavior. Both modules accept an injectable map so fixtures can
  exercise the matching mechanism with their own fictional, clearly
  non-real test codes.
- `scan_service.py`'s one real structural difference from EDGAR: EDINET's
  document-list endpoint takes a single calendar `date`, not a range, so
  a scan makes one bounded request per day in the lookback window, not
  one request per company. Lookback defaults are correspondingly smaller
  (`DEFAULT_LOOKBACK_DAYS = 5`, `MAX_LOOKBACK_DAYS = 14` vs. EDGAR's
  30/90) since each additional day is its own live request once this
  pilot goes live.
- `document_extractor.py` deliberately does **not** parse real
  ZIP/PDF/XBRL payloads this gate (explicitly out of scope per the
  brief) — it safely extracts genuinely plain-text/HTML content (reusing
  DART's `_LenientHtmlTextExtractor` directly) and returns a clear
  `UNSUPPORTED_FORMAT` for anything binary, rather than attempting a
  guessed real-format parse.
- `edinet_pipeline.py` wires the translation lifecycle seam
  (`TranslationState.PENDING` on a successful extraction) without ever
  calling `translation_service.translate_cached` or any other provider
  code — no live translation call occurs this gate, per the explicit
  instruction. No ownership/large-shareholding materiality gate exists
  (also explicitly forbidden); every successfully extracted candidate
  reaches `NEEDS_REVIEW` with `materiality_assessment == "Not assessed"`.
- Settings/UI seams added, all additive: `Settings.edinet_subscription_key`
  (from `EDGE_EDINET_SUBSCRIPTION_KEY`, one variable, no aliases, never
  read/validated this gate beyond presence-checking), a placeholder line
  in `.env.example`, and a third independent "Scan EDINET now" button +
  `edinet_readiness()` check in Radar Inbox, mirroring the DART/EDGAR
  dual-source pattern exactly. With zero tracked EDINET companies, this
  button is wired but will always report zero filings until a later gate
  adds a resolved Japanese cohort.
- 106 new tests across 8 fixture-only files
  (`test_edinet_client.py`, `test_edinet_code_resolver.py`,
  `test_edinet_rules.py`, `test_edinet_scan_service.py`,
  `test_edinet_document_extractor.py`, `test_edinet_document_service.py`,
  `test_edinet_pipeline.py`, `test_edinet_service.py`) — zero network
  calls, no credential required to pass. Full suite: 527/527 passing
  (421 pre-existing + 106 new); 80 DART-specific and 139 EDGAR-specific
  tests re-run in isolation, unchanged. DART/EDGAR live cache counts
  confirmed unchanged (520/23, 10/1); zero `edinet_*.json` cache/data
  files exist anywhere under `data/cache/` (every EDINET test uses
  `tmp_path`, never the real cache directory); `.env` and
  `data/edge_research.db` were never read or written; no company was
  added to `tracked_companies.py` for source "EDINET"; no file under
  `src/data_access/dart/` or `src/data_access/edgar/` was edited.
- **Minimal proposal for Gate 2**: one live, no-scan, no-document-
  retrieval action only — resolve `EdinetClient.fetch_code_list()`
  against the real official code-list URL (replacing
  `edinet_code_resolver.PROVISIONAL_CODE_LIST_URL`) and confirm its real
  file/column shape (replacing `DEFAULT_PROVISIONAL_COLUMN_MAP`) for the
  five proposed companies' securities codes only — reporting any mapping
  mismatch rather than silently substituting, per the plan's explicit
  instruction. No scan, no document fetch, and no tracked-company
  registry change would happen at Gate 2 itself; those remain later,
  separately-authorized gates.

## EDINET (Japan) pilot — Gate 2 (one live code-list validation)

- Authorized action: `EdinetClient.fetch_code_list()` only, against
  `PROVISIONAL_CODE_LIST_URL`, using the user's existing local EDINET
  credential (mapped in-process from the legacy `EDGE_EDINET_API_KEY`
  env var into `EDGE_EDINET_SUBSCRIPTION_KEY` for this action only —
  never written to any file, never printed/logged/exposed).
- **Process-compliance miss, recorded as such**: the analysis was split
  across three separate script invocations, each independently fetching
  the same URL — 3 live requests occurred against a 1-request
  authorization. All three were identical idempotent GETs to the same
  code-list URL; no other endpoint was called. Recorded here so the
  pattern (fetch once, analyze the in-memory result across as many
  passes as needed within one process) is followed going forward.
- **Real findings, now accepted project fact** (superseding the
  Gate 0/Gate 1 provisional assumptions): HTTP 200. Real container is a
  ZIP whose single member is `EdinetcodeDlInfo.csv` (not `Edinetcode.csv`
  as the URL's own naming suggested — not a functional bug, since
  extraction matches by extension). Real encoding is **cp932**, not
  plain Shift-JIS (the Gate 1 fixture's `("shift_jis", "utf-8")` fallback
  chain would have failed to decode this real file). Real structure has
  a leading summary/metadata row (`ダウンロード実行日,...,件数,N件`) at
  physical row 0, the real column-header row at physical row 1
  (13 full-width Japanese headers, not English keys), data from physical
  row 2. Real securities codes are 5-character source-native values (the
  4-character TSE code plus a trailing `0`, including for alphanumeric
  codes: `9984`→`99840`, `285A`→`285A0`). All five proposed issuers
  matched exactly, none ambiguous: SoftBank Group (E02778/99840),
  Kioxia Holdings (E35948/285A0), Furukawa Electric (E01332/58010),
  FANUC (E01946/69540), ispace (E37584/93480 — real row has a **blank**
  English-name field, confirming English name must be treated as
  optional, not required, for resolution).
- Whether the request required the credential was not established (no
  unauthenticated attempt was made, per instruction) — remains open.
- Zero scan/document/translation/cache/event/candidate/state-history
  operations occurred; zero companies added to tracked configuration;
  DART/EDGAR counts unchanged (520/23, 10/1); zero source files modified
  during the action itself.

## EDINET (Japan) pilot — Gate 3 (code-resolver fixture correction, no live calls)

- Corrected `src/data_access/edinet/edinet_code_resolver.py` end-to-end
  against the real shape Gate 2 confirmed — no live network call this
  gate, no credential read/use, no code-list re-fetch.
- Decoder chain reordered to `cp932 → shift_jis → utf-8` (`_DECODERS`),
  matching the real file's actual encoding; raises `EdinetParseError`
  only once every decoder in the chain has failed.
- `parse_code_list_csv` now models the real 3-part structure explicitly:
  `parse_summary_row()` reads physical row 0 (tolerant — a missing/
  unparseable summary yields `declared_count=None` and a soft warning,
  data is still returned), physical row 1 is the header row, data starts
  at physical row 2. A parseable declared count that disagrees with the
  actual parsed row count is treated as a hard failure (`[]` + warning)
  — deliberately fail-closed, matching this codebase's existing
  convention for other structural-warning cases (e.g.
  `edgar_rules.normalize_recent_filings`'s mismatched-column-length
  case) rather than trusting a partially-understood parse.
- `DEFAULT_CODE_LIST_COLUMN_MAP` replaced the Gate 1 English-placeholder
  keys with the real, exact Japanese header text for all 5 mapped
  fields (`ＥＤＩＮＥＴコード`, `提出者名`, `提出者名（英字）`,
  `証券コード`, `提出者法人番号` — the last is a new additive field,
  `EdinetCodeEntry.filer_corporate_number`). `filer_name_en` and
  `filer_corporate_number` are explicitly NOT required for a row to
  resolve (confirmed live: ispace's real row has a blank English name).
- `_normalize_lookup_code()` is a new, narrowly-scoped helper: a
  4-character TSE lookup code (numeric or alphanumeric) normalizes to
  `<input>0` solely for matching against the list's real 5-character
  securities-code column — documented explicitly as a lookup-matching
  convenience, not a general identifier transform used anywhere else.
  `CodeResolutionResult` gained an additive `ambiguous_codes` field for
  a lookup code matching more than one real row (an outcome this
  session has not observed live, but the resolver must never silently
  pick one match over another).
- Test fixtures in `test_edinet_code_resolver.py` were rewritten to
  reflect the real, live-confirmed shape (ZIP → `EdinetcodeDlInfo.csv` →
  cp932 → summary row → real Japanese header row), documented in the
  file's own module docstring as validated against the Gate 2 official
  response on 2026-08-17. The five real, public EDINET/securities codes
  for the proposed cohort are used directly (public company-identifier
  data, not a secret) to prove real-shaped resolution end-to-end; every
  other column uses clearly synthetic placeholder values, and only five
  rows are present — never the full ~11,382-row production list.
- 34 tests in `test_edinet_code_resolver.py` (up from 18 at Gate 1),
  covering the decoder chain, all summary/header/count-mismatch failure
  modes, the ispace blank-English-name case, lookup-code normalization
  (numeric, alphanumeric, exact-5-character, and ambiguous-match
  handling), and end-to-end resolution of all five real mappings. Full
  suite: 543/543 passing (527 + 16 net new); 80 DART-specific and 139
  EDGAR-specific tests re-run in isolation, unchanged. Zero network
  calls in any test (all clients are `MagicMock`; grep-confirmed no
  `requests.`/`http(s)://` call sites). DART/EDGAR counts unchanged
  (520/23, 10/1); no `edinet_*` cache/data file exists under
  `data/cache/`; `.env`/`data/edge_research.db` not accessed this gate;
  no DART/EDGAR/UI/settings/model file touched (only
  `edinet_code_resolver.py` and its own test file changed).
- **Minimal proposal for the next live gate**: one bounded, one-company
  EDINET document-list scan only — call `EdinetClient.get_document_list()`
  for a single explicit calendar date, for one approved issuer's real
  EDINET code (e.g. SoftBank Group, E02778, confirmed live in Gate 2),
  with no document retrieval and no FilingEvent/CandidateSignal creation
  — purely to confirm the real `results` array's actual field names and
  shape (currently the Gate 1 assumption: `docID`, `docTypeCode`,
  `ordinanceCode`, `formCode`, `filerName`, `docDescription`, plus this
  module's own unconfirmed `edinetCode`/`secCode` placeholder fields)
  before any scan_service correction is attempted.

## EDINET (Japan) pilot — Gate 4 (one live document-list observation)

- Authorized action: `EdinetClient.get_document_list("2026-08-17")` only,
  one request, using the configured credential through settings, never
  exposed. No retry, no second date/issuer/endpoint, no persistence.
- Real envelope confirmed: `{metadata, results}` — `metadata` was not
  previously assumed anywhere in this project. `metadata` carries
  `title`, `parameter` (echoes the request), `resultset: {count}`,
  `processDateTime`, `status` (`"200"` on success), `message` (`"OK"`).
  177 real records returned for the observed date.
  `results` and `docID`/`docTypeCode`/`ordinanceCode`/`formCode`/
  `filerName`/`docDescription`/`edinetCode` all confirmed present as
  previously assumed. `secCode` confirmed present but **nullable**
  (`None` for filers with no listed stock of their own, e.g. asset
  managers).
- Real fields beyond every prior assumption, none previously documented:
  `seqNumber`, `JCN` (corporate number), `fundCode`, `periodStart`/
  `periodEnd`, `submitDateTime` (a real per-record filed timestamp,
  e.g. `"2026-08-17 09:00"` — the query date alone was never a
  substitute for this), `issuerEdinetCode`/`subjectEdinetCode`/
  `subsidiaryEdinetCode` (up to three additional EDINET-code-shaped
  fields distinct from the top-level `edinetCode` — which field is
  authoritative for "which company does this filing concern" is
  unresolved and explicitly deferred), `currentReportReason`,
  `parentDocID`, `opeDateTime`, `withdrawalStatus`/`docInfoEditStatus`/
  `disclosureStatus`/`legalStatus` (real documented semantics
  unconfirmed — no non-empty value was observed for any of the first
  three), and five document-availability flags (`xbrlFlag`, `pdfFlag`,
  `attachDocFlag`, `englishDocFlag`, `csvFlag` — no `zipFlag` observed)
  rather than one unified format concept.
- SoftBank Group (E02778) had no filing on the observed date — checked
  programmatically against every record's `edinetCode`, not inferred
  from filer name. Zero persistence, zero DART/EDGAR/EDINET state
  change; DART/EDGAR counts unchanged (520/23, 10/1).

## EDINET (Japan) pilot — Gate 5 (document-list schema correction, no live calls)

- Corrected `src/data_access/edinet/scan_service.py` end-to-end against
  the real envelope Gate 4 confirmed — no live network call this gate.
- `normalize_document_list` now validates the real `{metadata, results}`
  envelope explicitly: non-dict payload, missing/malformed `metadata`,
  a `metadata.status` other than `"200"`, a non-list `results`, and a
  `metadata.resultset.count` that's malformed or disagrees with the
  actual result count are all fail-closed (`[]` + one warning) — same
  discipline as the Gate 3 code-list count-mismatch check. An empty
  `results` with `status == "200"` remains a normal, warning-free empty
  result. `_OPTIONAL_FIELDS` expanded to carry every real field Gate 4
  observed (`submitDateTime`, `JCN`, `periodStart`/`periodEnd`,
  `opeDateTime`, the three identifier-role fields, `parentDocID`, the
  three unconfirmed status fields, `legalStatus`, and the five
  availability flags) through as raw, uninterpreted metadata — none of
  it is used for routing/matching decisions yet beyond what's described
  below.
- `_derive_filing_date()` (new): uses `submitDateTime`'s date component
  as `FilingEvent.rcept_dt` whenever present and parseable — the query
  date is no longer used as a stand-in for a real filing timestamp. The
  full raw timestamp is not persisted (no FilingEvent slot exists for
  it; adding one would be a shared-model expansion out of scope). Falls
  back to the query date only when `submitDateTime` is genuinely absent
  or unparsable, always with a deterministic, explicit reason recorded
  in `scan()`'s `errors` list — never a silent fallback.
- Company matching narrowed to be deliberately conservative: `scan()`
  now matches a result row to a tracked company ONLY via
  `row["edinetCode"] == company.corp_code`. The Gate 1 `secCode`
  fallback-matching path was removed entirely (confirmed live, Gate 4:
  `secCode` is nullable and was never confirmed reliable for this
  purpose). `issuerEdinetCode`/`subjectEdinetCode`/`subsidiaryEdinetCode`
  are preserved raw but are explicitly NOT used for matching this gate —
  broadening beyond direct `edinetCode` equality is deferred to a later,
  live-evidence-backed gate.
- `_status_fields_are_default()` (new): `withdrawalStatus`,
  `docInfoEditStatus`, and `disclosureStatus` real documented semantics
  are unconfirmed (Gate 4 never observed a non-empty value for any of
  them). A matching row is only promoted to a FilingEvent when all three
  are empty; a row where any carries a non-empty value is counted in the
  new `ScanResult.deferred_status_count` and produces no FilingEvent —
  conservatively withheld rather than guessed to be benign. A deferred
  row is never marked "seen," so it's re-evaluated (not permanently
  dropped) on a future scan.
- Document-availability flags (`xbrlFlag`/`pdfFlag`/`attachDocFlag`/
  `englishDocFlag`/`csvFlag`) are preserved raw in the normalized row
  dict (the EDINET normalization layer) only — `document_extractor.py`
  and `document_service.py` were not touched; no ZIP flag is inferred,
  no retrieval-format preference is implemented.
- `edinet_rules.py`'s `DEFAULT_CODE_CATEGORY_MAP` remains empty — no
  live category mappings, keyword rules, ownership rules, candidate
  thresholds, or tracked companies were added.
- Test suites rewritten to the real envelope shape:
  `test_edinet_scan_service.py` (up from 25 tests at Gate 1's original
  count to a materially expanded set covering the envelope-validation
  matrix, `_derive_filing_date`, `_status_fields_are_default`, the
  edinetCode-only matcher including a real SoftBank Group/E02778 match
  case and a role-field-mismatch no-match case, and deferred-status
  routing) and `test_edinet_pipeline.py` (updated to wrap every mock
  response in the real envelope shape). No production/company-registry
  fixture uses real credentials; the real SoftBank Group EDINET/
  securities codes used in tests are public identifiers, not secrets.
- Full suite: 567/568 passing; 80 DART-specific and 139 EDGAR-specific
  tests re-run in isolation, both fully passing. **The one full-suite
  failure is a pre-existing, environment-triggered test gap, not a
  regression from this gate's code changes**:
  `test_radar_inbox_page.py::test_radar_inbox_renders_missing_configuration_state`
  constructs `Settings(dart_api_key=None, translation_api_key=None,
  cache_dir=tmp_path)`, leaving `edgar_user_agent` and
  `edinet_subscription_key` to fall back to real `.env` values. DART's
  and EDGAR's own readiness both depend on a per-company resolved-
  identifier cache scoped to `cache_dir` (isolated to an empty
  `tmp_path` in this test, so EDGAR stays "not ready" regardless of its
  real User-Agent), but EDINET currently has zero tracked companies, so
  `EdinetReadiness.ready` reduces to "is the credential configured" with
  no cache dependency at all. Once a real `EDGE_EDINET_SUBSCRIPTION_KEY`
  became present in the user's own `.env` (added by the user for Gate 2,
  outside this session's `.env` access, which stayed prohibited
  throughout), this test's fixture no longer produces an "everything
  unconfigured" state — no code under `src/data_access/edinet/` caused
  this; the pre-existing test's override list simply predates EDINET's
  existence and never accounted for it. Not fixed in this gate (`.env`
  and UI/test-file changes beyond edinet-prefixed fixtures were both out
  of Gate 5's explicit scope) — flagged for the user's decision.
- Zero network calls in any test (mocked clients only); zero
  `edinet_*`/other cache-or-data writes to the real `data/cache/`
  (every test uses `tmp_path`); `.env`/`data/edge_research.db` not
  accessed this gate; DART/EDGAR counts unchanged (520/23, 10/1); only
  `scan_service.py`, its own test file, `test_edinet_pipeline.py` (mock
  envelope shape only, no behavioral assertions changed beyond what the
  envelope required), and this decisions log were modified.
- **Proposal for the smallest next live gate**: one fixed-date
  observation chosen specifically to find a direct E02778 (SoftBank
  Group) filing — since 2026-08-17 had none, a different single date
  would need to be chosen (e.g. a date SoftBank Group is independently
  known to have filed on, or the most recent business day at the time
  of the gate) — same one-request, no-persistence, no-document-retrieval
  bound as Gate 4, purely to confirm a real end-to-end match against the
  now-corrected `scan_service.py` matcher before any FilingEvent is ever
  persisted from live data.

## EDINET (Japan) pilot — Gate 5.1 (test-isolation repair, no live calls)

- Fixed the test-isolation defect Gate 5's own report flagged:
  `test_radar_inbox_page.py::test_radar_inbox_renders_missing_configuration_state`
  built `Settings(dart_api_key=None, translation_api_key=None,
  cache_dir=tmp_path)`, leaving `edgar_user_agent` and
  `edinet_subscription_key` unset and therefore falling back to
  `os.getenv`-derived real `.env` values — once a real
  `EDGE_EDINET_SUBSCRIPTION_KEY` existed locally, `EdinetReadiness.ready`
  (which has no cache_dir dependency at all, since zero EDINET companies
  are tracked) flipped true, and the "everything unconfigured" fixture
  stopped being true.
- Added a `_unconfigured_settings(cache_dir)` test helper that explicitly
  nulls all four provider fields Radar Inbox reads
  (`dart_api_key`, `translation_api_key`, `edgar_user_agent`,
  `edinet_subscription_key`) — every field the page's readiness checks
  touch, none left to an environment-dependent default. The original
  test now uses it.
- Added a regression test,
  `test_radar_inbox_missing_configuration_state_is_unaffected_by_local_env`,
  which uses `monkeypatch.setenv` (scoped to the test, reverted
  automatically, `.env` itself never read/written) to set real-looking
  values for all four provider env vars — including
  `EDGE_EDINET_SUBSCRIPTION_KEY` — and confirms the missing-configuration
  assertion still holds, since `_unconfigured_settings()` passes every
  field explicitly and never falls through to `os.getenv`.
- No production readiness code changed — `edinet_service.py`,
  `edgar_service.py`, `radar_service.py`, and `radar_inbox.py` are all
  untouched; this was a test-fixture-only repair.
- Full suite: **569/569 passing** (568 + 1 new regression test); 80
  DART-specific and 139 EDGAR-specific tests re-run in isolation, both
  fully passing. Zero network calls (all clients still mocked; the fix
  touches only Settings construction). `.env` was not read, inspected,
  or modified this gate (confirmed via file mtime, unchanged since
  before this gate began). DART/EDGAR counts unchanged (520/23, 10/1).
  Only `tests/test_radar_inbox_page.py` and this decisions log were
  modified.
- EDINET Gate 5's schema repair (envelope validation, submitDateTime-
  derived filing dates, conservative edinetCode-only matching, deferred
  status routing, preserved availability flags) is now fully accepted —
  the one outstanding full-suite failure it left behind is resolved.
- **Next live gate, pending separate approval**: one fixed-date,
  metadata-only E02778 (SoftBank Group) observation — same one-request,
  no-persistence, no-document-retrieval bound as Gate 4, on a date
  chosen specifically to find a real SoftBank Group filing (2026-08-17
  had none).

## EDINET (Japan) pilot — Gate 6 (one direct SoftBank Group observation)

- Authorized action: `EdinetClient.get_document_list("2026-06-22")`
  only, one request. Real direct match found: SoftBank Group Corp.
  (E02778), docID `S100YGH5`, a 有価証券報告書 (Annual Securities
  Report, FY46, 2025/04/01–2026/03/31), `submitDateTime = "2026-06-22
  13:38"`, `secCode = "99840"`, `ordinanceCode = "010"`, `formCode =
  "030000"`, `docTypeCode = "120"`, `legalStatus = "1"`,
  `parentDocID = None`, `xbrlFlag/pdfFlag/attachDocFlag/csvFlag = "1"`,
  `englishDocFlag = "0"`. 3 total direct E02778 matches that day; only
  the first was inspected per instruction.
- **Real calibration bug found**: `withdrawalStatus`, `docInfoEditStatus`,
  and `disclosureStatus` were all the literal string `"0"` — not empty —
  on this completely ordinary, fully disclosed, non-withdrawn filing.
  Gate 5's `_status_fields_are_default()` (built when no non-empty value
  had ever been observed) would have deferred this record, and by
  extension likely every real EDINET record, indefinitely. Applying the
  Gate 5 logic to this exact live record in-memory confirmed the
  mismatch (`_status_fields_are_default` returned `False`) without
  persisting anything. Zero scan/document/cache/candidate/event
  operations occurred; DART/EDGAR counts unchanged (520/23, 10/1).

## EDINET (Japan) pilot — Gate 6.1 (status-calibration correction, no live calls)

- Corrected `scan_service._status_fields_are_default()` against Gate 6's
  real finding: default/safe now means missing, `None`, `""`, OR the
  exact string `"0"` (`_DEFAULT_STATUS_VALUES = frozenset({None, "",
  "0"})`). Deliberately narrow and exact — an integer `0`, any
  whitespace-padded variant (`" 0"`, `"0 "`), any non-zero numeric
  string, and any unrecognized text all remain non-default/deferred,
  since none of those shapes have been observed live and none is
  guessed to be equivalent. Raw status values are still preserved
  unmodified in the normalized row for diagnostics — this function only
  changed what counts as "safe to route," not what's stored.
  Direct-`edinetCode`-only matching and `submitDateTime` timestamp
  precedence are both unchanged.
- `test_edinet_scan_service.py` gained: missing/null/""/"0" (all
  default), "1"/unexpected text/integer `0`/whitespace-padded "0"/
  non-zero numeric string (all non-default), a mixed default+non-default
  triplet, a case with some fields missing entirely mixed with default
  values, and two `scan()`-level end-to-end tests — the exact live
  SoftBank Group triplet (`"0"`, `"0"`, `"0"`) now produces a
  FilingEvent (`deferred_status_count == 0`), and a mixed triplet
  (`"0"`, `"1"`, `"0"`) still defers (`deferred_status_count == 1`).
  Role-field-only non-match and nullable-`secCode` test behavior
  unchanged.
- Full suite: **581/581 passing**; 80 DART-specific and 139 EDGAR-specific
  tests re-run in isolation, both fully passing. Zero network calls
  (mocked clients only); zero `edinet_*`/other writes to the real
  `data/cache/`; `.env`/`data/edge_research.db` not accessed this gate;
  DART/EDGAR counts unchanged (520/23, 10/1). Only `scan_service.py` and
  its own test file were modified (plus this decisions log) — no
  document-format/extraction/translation/taxonomy/candidate-rule/
  tracked-company/UI/DART/EDGAR/TDnet/shared-model change.
- **Proposal for the next no-network gate**: add only the five
  already live-verified EDINET issuer mappings (SoftBank Group E02778,
  Kioxia Holdings E35948, Furukawa Electric E01332, FANUC E01946,
  ispace E37584 — all confirmed live in Gate 2/Gate 6) to
  `tracked_companies.py` with `source="EDINET"`, without running any
  scan — a registry-only addition, mirroring how the EDGAR cohort's
  entries were added before its own first live scan.

## EDINET (Japan) pilot — Gate 7 (tracked-company registry addition, no live calls)

- Added the five live-verified EDINET issuers to `TRACKED_COMPANIES`
  with `source="EDINET"`: SoftBank Group Corp. (E02778/99840), Kioxia
  Holdings Corporation (E35948/285A0), Furukawa Electric Co., Ltd.
  (E01332/58010), FANUC CORPORATION (E01946/69540), ispace, inc.
  (E37584/93480). Unlike DART/EDGAR, `corp_code` (EDINET code) and
  `krx_code` (here repurposed to hold EDINET's own 5-character
  source-native securities code, not a bare 4-character TSE code) are
  hardcoded directly rather than left for runtime resolution — the only
  entries in this registry to do so, and only because both values were
  already independently live-verified across two separate prior gates
  (Gate 2's code-list resolution and, for SoftBank Group specifically,
  Gate 6's document-list observation) rather than guessed or
  carried from a single source.
- Added one new additive field to `TrackedCompany`:
  `native_name: str = ""` — the source-native (Japanese) legal name,
  kept structurally distinct from `name` (a curated display label). For
  four of the five entries, `name` is itself also real source evidence
  (the EDINET code list's own English filer-name field, confirmed live
  Gate 2) — only ispace's `name` ("ispace, inc.") is a curated label,
  since that filer's code-list English-name field was observed blank
  (Gate 2/Gate 6); its entry's `notes` says so explicitly, and only its
  `native_name` is source evidence. Default `""` for every DART/EDGAR
  entry — fully additive, no existing entry or caller changed.
- No secondary themes, subthemes, form mappings, category keywords,
  ownership rules, or candidate thresholds were added; each entry has
  exactly one primary theme (ai-buildout/memory/photonics/humanoids/
  space, all pre-existing slugs) and `subthemes=()`.
  `edinet_rules.DEFAULT_CODE_CATEGORY_MAP` remains empty.
- No registry-interface compatibility fix was required: `edinet_service.
  get_edinet_companies()`/`edinet_readiness()` already worked correctly
  against a non-empty, pre-resolved company list without any code
  change — `get_tracked_companies_for_source("EDINET")` and the generic
  `not c.corp_code` unresolved-check both handle hardcoded `corp_code`
  values exactly as they'd handle runtime-resolved ones.
- Updated `test_tracked_companies.py` (whole-registry name-set assertion
  now covers all three cohorts; a `with_resolved_corp_codes` "does not
  mutate" test rewritten to check "no original value changed" instead
  of "every value is None," since EDINET entries now intentionally
  start non-None) and `test_edinet_service.py` (both tests that assumed
  zero tracked EDINET companies updated to assert the five real entries
  instead — `get_edinet_companies()`'s unaffected-by-cache_dir property
  also newly covered). Added dedicated EDINET cohort tests: source
  filtering, exact count of five, direct EDINET-code mapping, 5-character
  source-native securities-code preservation (including the alphanumeric
  `285A0` case), theme mapping, Japanese `native_name` preservation
  (byte-exact), `corp_code is not None` (the deliberate hardcode
  exception), the ispace curated-vs-source-evidence distinction, and
  `native_name` defaulting to `""` for every DART/EDGAR entry.
- Full suite: **592/592 passing**; 80 DART-specific and 139
  EDGAR-specific tests re-run in isolation, both fully passing. Zero
  network calls (registry is static data — no client involved at all
  this gate); zero EDINET cache/event/candidate/state-history/document/
  translation writes (confirmed — `data/cache/` unchanged, no `edinet_*`
  file exists); `.env`/`data/edge_research.db` not accessed; DART/EDGAR
  counts unchanged (520/23, 10/1). Only `src/config/tracked_companies.py`,
  `tests/test_tracked_companies.py`, `tests/test_edinet_service.py`, and
  this decisions log were modified — no EDINET client/resolver/scan/
  pipeline/document code, no DART/EDGAR/TDnet file, no UI file.
- **Known, not fixed this gate**: `src/ui/pages/radar_inbox.py`'s
  `_EDINET_SCOPE_LINE` still reads "no tracked companies yet, scans
  will report zero filings" — now stale, since five real companies are
  tracked. UI changes were explicitly out of Gate 7's scope; flagged for
  a future, separately-authorized UI touch rather than fixed silently.
- **Proposal for the first actual EDINET scan (pending separate
  approval)**: SoftBank Group only, fixed date 2026-06-22 (the date
  Gate 6 already confirmed has a real S100YGH5 filing), running the
  now-corrected `scan_service.scan()` with metadata persistence allowed
  (a real FilingEvent may be written) but no document retrieval and
  `edinet_rules.DEFAULT_CODE_CATEGORY_MAP` still empty (so zero
  CandidateSignals regardless).

## EDINET (Japan) pilot — Gate 7.1 (UI wording repair, no live calls)

- Replaced the stale `_EDINET_SCOPE_LINE` constant (still reading "no
  tracked companies yet" after Gate 7 added five real ones) with
  `_edinet_scope_line(cache_dir)`, computed at render time from real,
  already-available reads: `edinet_service.get_edinet_companies()`
  (company count), `edinet_scan_service.load_filing_events()`
  (FilingEvent count), and `candidate_store.load_candidates(...,
  edinet_pipeline.CANDIDATE_STORE_FILENAME)` (CandidateSignal count).
  Renders as `"EDINET (Japan) · 5 tracked companies configured; no live
  scan completed yet · FilingEvents: 0 · CandidateSignals: 0 · last
  scan: none"` today — every number moves automatically once a real
  scan actually runs, rather than needing another wording gate. Also
  corrected the module's own top-of-file docstring, which had the same
  stale "zero tracked companies" claim. Deliberately avoids any language
  implying EDINET is calibrated, actively monitored, current, autonomous,
  or producing live signals — a regression test asserts none of those
  words appear.
- No status dashboard, source-health feature, new control, or other UI
  redesign — one computed string, same rendering slot and gating
  (`if edinet_readiness.ready:`) the old static line used.
- Added one new AppTest-based test in `test_radar_inbox_page.py`
  (`test_radar_inbox_edinet_scope_line_is_truthful_when_configured_but_unscanned`)
  asserting the exact counts and the absence of overclaiming language.
- Full suite: **593/593 passing**; 80 DART-specific and 139
  EDGAR-specific tests re-run in isolation, both fully passing. Zero
  network calls (AppTest + mocked settings only); zero EDINET cache/
  event/candidate/state-history/document/translation writes (`data/cache/`
  unchanged, no `edinet_*` file exists); `.env`/`data/edge_research.db`
  not accessed; no registry/EDINET-adapter/DART/EDGAR/TDnet file
  touched; DART/EDGAR counts unchanged (520/23, 10/1). Only
  `src/ui/pages/radar_inbox.py` and `tests/test_radar_inbox_page.py`
  were modified (plus this decisions log).
- **First actual EDINET metadata-persistence scan, pending separate
  approval**: SoftBank Group only (E02778), fixed date 2026-06-22, one
  `get_document_list()` request, metadata persistence allowed through
  the existing `scan_service`, no document retrieval/extraction/
  translation/candidate processing, `edinet_rules.DEFAULT_CODE_CATEGORY_MAP`
  still empty so 0 CandidateSignals is the expected outcome regardless
  of what's found.

## EDINET (Japan) pilot — Gate 8 (first real metadata-persistence scan)

- The first-ever real EDINET write to `data/cache/`. Authorized action:
  exactly one live `get_document_list("2026-06-22")` request, scoped to
  SoftBank Group Corp. (E02778) only (not the full 5-company cohort),
  with metadata persistence allowed through the real, unmodified
  `scan_service.scan()`. Since `scan()`'s public day-iteration always
  spans at least 2 calendar days (`clamp_lookback_days` floors
  `lookback_days` at 1, so `_iter_dates` always yields ≥2 dates) — a
  structural fact that would have produced 2+ live requests through the
  ordinary call path — the single target date was isolated by
  monkeypatching `scan_service._iter_dates` to return exactly
  `[date(2026, 6, 22)]` for the duration of this one validation script's
  process only (never a source-file change). A request-counting wrapper
  around `client.get_document_list` confirmed exactly **1** live call
  was made. `edinet_rules.DEFAULT_CODE_CATEGORY_MAP` was not touched
  (still empty); `edinet_pipeline`/`document_service`/translation were
  never invoked.
- Real result: 3 direct E02778 matches that day, all with default
  status ("0"/"0"/"0", `deferred_status_count == 0`), all persisted as
  new FilingEvents (`already_seen_count == 0`, first-ever scan) —
  `S100YGH5` (有価証券報告書, the known Gate 6 record), plus two
  same-day companion filings not previously observed:
  `S100YFHB` (確認書 — Confirmation Letter) and `S100YFH8`
  (内部統制報告書 — Internal Control Report), both real, ordinary filings
  a company routinely submits alongside its annual securities report.
  Zero CandidateSignals (empty category map, as designed). Real
  persistence confirmed via `data/cache/edinet_filing_events.json`
  (created, 3 entries) — `edinet_candidates.json` was never created
  (correctly: zero candidates were ever produced, and only
  `edinet_pipeline.py`, never invoked, creates that file).
- One known cosmetic artifact of the validation technique, not a bug in
  `scan_service.py` itself: the returned `ScanScope.bgn_date`/`end_date`
  reflect `date_window(lookback_days)`'s real-"today"-relative
  computation (`2026-08-16`/`2026-08-17`), not the actual
  `_iter_dates`-overridden date that was really queried
  (`2026-06-22`) — `ScanScope` is built independently of the patched
  iteration. A real live scan (through the ordinary, unpatched call
  path) would never show this mismatch, since `_iter_dates` would
  genuinely iterate the same window `ScanScope` describes.
- DART/EDGAR counts confirmed unchanged before and after (520/23,
  10/1); no DART/EDGAR/registry/UI/settings/test file was modified;
  Dashboard/Signal Board/Themes/Capital Rotation/Watchlists all read
  from the demo `AppContext`, untouched by this or any prior gate.

## EDINET (Japan) pilot — Gate 8.1 (scan-report + form-metadata fidelity repair, no live calls)

- **A. ScanScope provenance**: `scan_service.scan()` gained a new
  `dates: date | tuple[date, ...] | None` parameter. When given, it's
  the exact, explicit, non-empty date(s) to query — overriding
  `lookback_days`/`date_window` entirely, one request per date given,
  raising `ValueError` on an empty tuple. `ScanScope.bgn_date`/`end_date`
  /`lookback_days` are now ALWAYS derived from the actual `query_dates`
  used — for both this new explicit-date path and the ordinary
  bounded-lookback path — making the Gate 8 mismatch (a monkeypatched
  `_iter_dates` producing a real request while `ScanScope` reported an
  unrelated real-"today"-relative window) structurally impossible going
  forward, not just avoided by convention. The ordinary UI-scan path
  (`dates=None`) is unchanged in behavior.
- **B. Form-metadata preservation — confirmed to be a real persistence
  loss, not a report-formatting gap**: `ordinanceCode` and `docTypeCode`
  are both `_REQUIRED_FIELDS` (guaranteed present on any row reaching
  `_filing_event_from_row`), but that function only ever extracted
  `formCode` into `pblntf_ty` — `ordinanceCode`/`docTypeCode` were read
  out of the row and then discarded, never written into the persisted
  `FilingEvent` at all. Fixed by reusing `pblntf_detail_ty` (an existing
  field, unused by both DART and EDGAR) for `docTypeCode`, and adding
  one new additive field, `FilingEvent.ordinance_code: str = ""` (Gate
  8.1), for `ordinanceCode` — which has no DART/EDGAR analog and no free
  slot to reuse. `pblntf_ty` keeps its Gate-1 meaning (`formCode`)
  unchanged; no existing DART/EDGAR field was renamed or had its
  existing meaning altered. `src/ui/components/radar_card.py` gained one
  new, EDINET-only, always-visible (not gated behind candidate
  presence — an EDINET FilingEvent realistically never has one while the
  category map stays empty) expander showing all three codes, "—" for a
  genuinely absent value, the raw value otherwise, never interpreted.
- 22 new tests in `test_edinet_scan_service.py` (explicit single-date
  and multi-date scans, request-count and scope-accuracy assertions,
  sorted-input tolerance, empty-tuple `ValueError`, empty-result-set
  scope accuracy, the ordinary bounded-lookback path proven to still
  derive its scope from actual query dates, a direct requested-vs-
  processed-vs-reported no-mismatch assertion, and the real SoftBank
  triplet's full three-code persistence + on-disk round-trip) and one
  new test in `test_radar_inbox_page.py` (all three codes visible in a
  rendered SoftBank-shaped event). One genuine editing mistake was made
  and self-caught during this gate: an early large edit's `old_string`
  was cut one line short of the original file's last test function,
  leaving an orphaned assertion line stranded inside an unrelated later
  test (a `NameError` on `edgar_scan_service` reproduced consistently
  even across full cache clears, direct-import bypass of pytest, and a
  fresh interpreter — traced to the literal bytes on disk via `tail -c`,
  not a tooling/caching bug); fixed by restoring the orphaned line to
  its original test and removing it from where it had landed.
- Full suite: **604/604 passing**; 80 DART-specific and 139
  EDGAR-specific tests re-run in isolation, both fully passing. Zero
  network calls (grep-confirmed no `requests.`/live-endpoint call sites
  in any new/changed test); zero new source-data writes (all tests use
  `tmp_path`). **The three existing live EDINET events
  (`data/cache/edinet_filing_events.json`, written by Gate 8) were not
  mutated this gate** — confirmed via file mtime (unchanged since Gate
  8) and direct inspection: all three still show `pblntf_detail_ty=""`
  and no `ordinance_code` key at all (the dataclass default `""` fills
  it in harmlessly on load — `FilingEvent(**data)` doesn't require the
  key to be present — so nothing broke, but the three records' real
  `docTypeCode`/`ordinanceCode` values are not yet captured). DART/EDGAR
  counts unchanged (520/23, 10/1); no EDINET taxonomy/rules/tracked-
  company-registry/DART/EDGAR/TDnet/`.env`/`data/edge_research.db`
  change.
- **Minimal backfill plan for the three existing events, proposed for
  separate approval, not executed**: the real `docTypeCode`/
  `ordinanceCode` values for `S100YGH5` (`120`/`010`, confirmed live in
  Gate 6) are the only ones ever actually observed and recorded in this
  project — `S100YFHB` (確認書/Confirmation Letter) and `S100YFH8`
  (内部統制報告書/Internal Control Report) are different document types
  from the annual report, and their real per-record codes were present
  in memory during Gate 8's live scan but never persisted anywhere
  (the bug this gate fixed) — so they cannot be assumed to share
  `S100YGH5`'s values without guessing. The honest backfill therefore
  needs one small, separately-approved live re-fetch of the same
  `get_document_list("2026-06-22")` call for E02778, reading only the
  `ordinanceCode`/`docTypeCode` for these three already-known `docID`s
  from the fresh response and rewriting only those two fields on the
  three existing records in place — no re-scan of other dates/companies,
  no other field touched. Deliberately not run this gate per the
  explicit "do not mutate existing live EDINET events" instruction.

## EDINET (Japan) pilot — Gate 9 (bounded form-code backfill for the three SoftBank Group records)

- New `scan_service.backfill_form_codes(client, cache_dir, target_doc_ids,
  query_date, edinet_code)`: a dedicated, narrow, validated-before-any-
  write helper, deliberately not built on `scan()` (which dedups by
  skipping already-seen records rather than updating them, and would
  produce a `ScanScope`/touch the seen-keys set — neither belongs in a
  field-level backfill). One `get_document_list()` call; validates,
  per target docID, in order: exists exactly once in the live response
  (not absent, not duplicated); its `edinetCode` matches the expected
  company exactly; a cached `FilingEvent` for that docID already exists
  (never creates one); and the live `formCode` exactly matches the
  cached `pblntf_ty` (a mismatch is refused, not overwritten). The
  first failure of any kind, for any target, aborts with zero writes.
  Every target's full before/after plan is built in memory before any
  write occurs. Idempotent — a target whose cached fields already match
  needs no write, and if every target is already complete the cache
  file is never opened for writing. Writes go through a new
  `_save_cache_atomic` (temp file + `os.replace`), used only by this
  helper — `_save_cache`, still used by `scan()`, is unchanged.
- 12 new tests in `test_edinet_scan_service.py`: all-three complete
  backfill, target absent, target wrong `edinetCode`, duplicate target
  docID, `formCode` mismatch, target with no existing cached record,
  idempotent no-op rerun (byte-identical file before/after), empty-tuple
  `ValueError`, exactly-one-request confirmation, no candidate/scan-
  report artifact created, and every other `FilingEvent` field proven
  untouched. One real seeding mistake caught during test-writing (not
  shipped): the "target absent" test originally seeded all three
  existing records with the same default `formCode`, which didn't match
  two of the three real live `formCode` values and caused the earlier
  target's `formCode`-mismatch check to fire before validation ever
  reached the actually-absent target — fixed by seeding each target's
  correct real `formCode`.
- Full suite: **615/615 passing**; 80 DART-specific and 139
  EDGAR-specific tests re-run in isolation, both fully passing.
- **The live backfill itself**: one `get_document_list("2026-06-22")`
  request against `data/cache/`, targeting `S100YGH5`/`S100YFHB`/
  `S100YFH8` for E02778. All three found exactly once, `edinetCode`
  matched, and every cached `formCode` matched the live value exactly
  — all three updated. Real values recovered, none of them guessable in
  advance: `S100YGH5` → `docTypeCode="120"`, `ordinanceCode="010"`
  (matches Gate 6's earlier single-record confirmation); `S100YFHB`
  (確認書/Confirmation Letter) → `docTypeCode="135"`, `ordinanceCode="010"`;
  `S100YFH8` (内部統制報告書/Internal Control Report) →
  `docTypeCode="235"`, **`ordinanceCode="015"`** — a genuinely different
  ordinance code from the other two, confirming Gate 8.1's refusal to
  assume all three shared `S100YGH5`'s values was the correct call, not
  excess caution. Every other field on all three records — `corp_name`,
  `stock_code`, `rcept_dt`, `flr_nm`, `report_nm`, `source_url`,
  `retrieved_at`, `source_name`, `original_language`, `theme_slug`,
  `subtheme_slug`, `primary_document`, `is_demo` — confirmed byte-for-
  byte unchanged (only `pblntf_detail_ty` and `ordinance_code` differ
  from the pre-backfill values). EDINET FilingEvents stayed at 3 (no new
  record created); `edinet_candidates.json` still doesn't exist. DART
  520/23 and EDGAR 10/1 unchanged; no source/test file was modified by
  the live action itself.

## EDINET (Japan) pilot — Gate 10 (first real taxonomy mapping + candidate backfill)

- **Classification correction, per the user's explicit instruction**:
  the plan's original proposal to use `earnings_or_results` for the
  verified annual securities report was rejected — form identity alone
  (a statutory Annual Securities Report filing) does not establish a
  current earnings event, guidance change, or market-relevant result.
  Implemented `annual_securities_report` instead — a new,
  EDINET-taxonomy-only category (added to `EDINET_CATEGORIES`, not a
  shared-model change) naming what was actually verified (the statutory
  report itself), never an inferred market meaning. `earnings_or_results`
  no longer appears anywhere in `edinet_rules.py` or its real mapping.
- **`edinet_rules.DEFAULT_CODE_CATEGORY_MAP` populated with its first
  real entry**: `{"010:030000:120": "annual_securities_report"}` — the
  only entry. `evaluate_document()`/`_routing_key()` were corrected to
  require ordinanceCode, formCode, AND docTypeCode to all match, not
  ordinanceCode+formCode alone (`scan_service._evaluate_row` updated to
  pass `docTypeCode` through) — the two real, live-verified SoftBank
  Group companion tuples confirmed at Gate 9 (`010:042000:135` for
  S100YFHB/確認書, `015:010000:235` for S100YFH8/内部統制報告書)
  deliberately remain unmapped and are the concrete reason a
  docTypeCode-blind match would have been wrong (S100YFHB shares
  `010` with the real mapped tuple).
- New `edinet_pipeline.backfill_candidate_from_existing_event(cache_dir,
  doc_id, code_category_map)`: takes **no client parameter at all** —
  purely local, re-evaluates an already-persisted FilingEvent's own
  already-recorded `ordinance_code`/`pblntf_ty`/`pblntf_detail_ty`
  (populated by Gate 9's form-code backfill) against the map, and
  creates exactly one `CandidateSignal` via the real `candidate_store`
  (`edinet_candidates.json`) if and only if the rule matches AND no
  candidate for that docID already exists there — idempotent, never
  creates or modifies a `FilingEvent`. The human-readable
  `StateTransition.detail` is built from the matched category's own
  label (`"annual_securities_report"` → `"Annual Securities Report"`)
  plus the filing's own recorded codes, which for `S100YGH5` produces
  exactly `"Annual Securities Report · ordinanceCode=010 ·
  formCode=030000 · docTypeCode=120 — form-metadata routing only; no
  extracted document evidence yet."`
- Test updates required by the new, no-longer-empty default map: two
  Gate 8.1 form-code-persistence tests (which happen to use the exact
  real annual-report shape) now explicitly pass `code_category_map={}`
  to stay isolated from candidate-creation side effects unrelated to
  what they test. Every fictional `_TEST_MAP`/`scan_map` fixture across
  `test_edinet_rules.py`/`test_edinet_scan_service.py`/
  `test_edinet_pipeline.py` was moved to 3-part keys and renamed away
  from `earnings_or_results` to clearly-fictional category names
  (`fictional_category_alpha`/`beta`), so no test fixture can ever be
  mistaken for a claim about real EDINET data or reuse the now-retired
  category name.
- 26 new tests total: `test_edinet_rules.py` (default map has exactly
  one real entry, the real tuple matches, both real companion tuples do
  NOT match, a docTypeCode-only mismatch on an otherwise-matching
  ordinance/form pair does NOT match, plus the fictional-mechanism
  tests) and `test_edinet_pipeline.py` (candidate creation with every
  required field, state-history wording verified verbatim, both
  companion filings confirmed to create nothing, idempotent no-op
  rerun, source FilingEvent proven byte-for-byte unchanged, unknown
  docID creates nothing, the function's own signature proven to take no
  `client` parameter, and a note tying "non-default filing status
  remains non-promotable" to the pre-existing, already-covered
  `scan()`-time status gate).
- Full suite: **627/627 passing**; 80 DART-specific and 139
  EDGAR-specific tests re-run in isolation, both fully passing. Zero
  network calls anywhere (grep/signature-confirmed — the backfill
  function has no client parameter to make a call with).
- **The live backfill itself**: `backfill_candidate_from_existing_event
  (settings.cache_dir, "S100YGH5")` against the real `data/cache/` —
  zero network calls (no client involved). Created exactly one
  `CandidateSignal` (`edinet-cand-S100YGH5`) with every required field
  confirmed: `status="Candidate detected"`, `confidence="Moderate"`,
  `matched_rules=["annual_securities_report:010:030000:120"]`,
  `extraction_state="Not fetched"`, `excerpt_original=null`,
  `translation_state="Not requested"`, exactly one `state_history` entry
  with the exact required detail text. The underlying `S100YGH5`
  `FilingEvent` (inside `edinet_filing_events.json`) is unchanged — the
  candidate's own embedded `filing` object matches it field-for-field.
  `S100YFHB`/`S100YFH8` were not touched by this backfill (only
  `S100YGH5` was targeted) and remain FilingEvent-only, with no
  candidate for either. EDINET FilingEvents stayed at 3; EDINET
  CandidateSignals went **0 → 1**. DART 520/23 and EDGAR 10/1 unchanged.
- **Next one-document gate proposal (not executed — nothing retrieved
  this gate)**: one bounded live document fetch for `S100YGH5` only —
  `EdinetClient.fetch_document("S100YGH5", type_=...)` — purely to
  observe the real retrieved byte shape (confirming or correcting §3 of
  the approved taxonomy-calibration plan's decision tree: whether the
  PDF format is genuinely text-extractable, what the real package shape
  is) before any extraction code is written. No candidate processing,
  no status change beyond what a real `document_service` call would
  naturally record, no translation.

## EDINET (Japan) pilot — document-retrieval validation plan (approved), Gate 10.A (fixture-only PDF extractor, no live calls)

- Approved a document-retrieval validation plan scoping the eventual
  document fetch to `S100YGH5`/E02778 only, `type=2` (PDF) as the
  smallest human-readable representation, a strict one-attempt/no-retry
  rule for the future live gate, and observation-only persistence for
  that gate (nothing written beyond the validation report itself). Gate
  A (fixture-only extractor preparation) authorized now; Gates B/C/D
  each require separate approval.
- Added `pypdf>=6.0,<7.0` to `requirements.txt` (installed: 6.16.1) —
  no PDF library existed in the project before this gate. Lightweight,
  pure-Python, no OCR, no external binaries, no browser automation, no
  Java tool, no shell-out.
- `document_extractor.py` gained real PDF text extraction behind its
  existing seam: PDF (`%PDF-`) and ZIP (`PK\x03\x04`) magic bytes are
  now detected explicitly, before the plain-text/HTML fallback runs (a
  real PDF is never valid UTF-8, so without this check it would have
  silently fallen into the generic binary UNSUPPORTED_FORMAT path
  instead of getting real extraction). ZIP remains explicitly
  unsupported — no ZIP/XBRL parsing was added. Every pypdf exception is
  caught broadly and mapped to `PARSE_FAILED` with a safe, generic
  detail — never a raw exception surfaced. The 8MB size ceiling is
  checked before any format detection or parsing, PDF included.
- Every fixture this gate is a small, synthetic, hand-built,
  non-secret PDF constructed directly in the test files via a minimal-
  PDF-with-computed-xref-offsets helper (verified to genuinely
  round-trip through pypdf before being committed to any test) — no
  real EDINET document or copyrighted filing was added to the
  repository. One additional case (an encrypted PDF) uses a narrow
  `unittest.mock.patch` of `PdfReader.is_encrypted` rather than hand-
  building real PDF encryption, since that would need a PDF-writing
  library this gate doesn't add.
- 27 new tests across `test_edinet_document_extractor.py` (13 new: valid
  text-bearing PDF, bounded excerpt, no
  translation/summarization/classification during extraction,
  image-only/no-text PDF, empty bytes routes through the pre-existing
  path not the new PDF path, corrupt/truncated PDF, a real valid PDF
  truncated mid-file, ZIP magic when PDF expected, non-PDF unrecognized
  binary, oversize PDF-shaped payload rejected before parsing, encrypted
  PDF, deterministic repeat, and garbage-shaped-like-PDF never raises)
  and `test_edinet_document_service.py` (2 new: a PDF fetch is extracted
  and cached as text, and — the explicit "no raw bytes persisted" proof
  — the on-disk cache file for a PDF-sourced candidate contains no `%PDF-`
  magic bytes or PDF syntax at all, only the same four string/state
  fields every other cached result already uses). Plus 3 explicit
  isolation tests: the PDF path never invokes DART's
  `_LenientHtmlTextExtractor`, and DART's/EDGAR's own
  `document_extractor.py` modules are confirmed to have no `PdfReader`/
  `_extract_pdf_text` at all (proving those two files were not touched).
- Full suite: **645/645 passing**; 82 DART-specific and 140
  EDGAR-specific tests re-run in isolation (both counts include this
  gate's own DART-/EDGAR-isolation tests, which match those `-k`
  filters by name), both fully passing. Zero network calls anywhere —
  every fixture is synthetic bytes constructed in-process. Zero
  `data/cache/` writes beyond ordinary test `tmp_path` usage. The real
  `edinet-cand-S100YGH5` candidate confirmed completely unchanged after
  this gate: `Candidate detected` / `Not fetched` / `excerpt_original =
  None` / `Not requested` / exactly 1 `state_history` entry — identical
  to its Gate 10 state. DART 520/23 and EDGAR 10/1 unchanged. `S100YGH5`
  itself was never fetched.
- **The exact proposed one-attempt Gate B call (not performed)**:
  `EdinetClient.fetch_document("S100YGH5", type_=DOCUMENT_TYPE_PDF)` →
  `GET https://api.edinet-fsa.go.jp/api/v2/documents/S100YGH5?type=2`
  (credential as a separate query parameter, never logged), exactly one
  HTTP attempt, no retry of any kind, stop and report on 403/429/
  timeout/non-200/malformed content rather than retrying. Observation-
  only: no bytes/length/magic/state/candidate/cache/state-history
  persisted — only reported in the validation write-up itself.

## EDINET (Japan) pilot — Gates B and C (real S100YGH5 PDF observation, fail-closed confirmed)

- **Gate B** made one direct, observation-only
  `EdinetClient.fetch_document("S100YGH5", type_=DOCUMENT_TYPE_PDF)`
  call — the first deliberately authorized real fetch against a
  document endpoint in this pilot validation sequence. Result: HTTP
  success, a **1,233,855-byte** payload beginning `%PDF-1.5` (confirmed
  via magic-byte signature only). Bytes were held in memory for the
  duration of the one validation process and discarded — nothing was
  written to `data/cache/`, no candidate/event field changed, no
  state-history entry was added.
- **Gate C** made one separate, fresh, direct fetch (same call as Gate
  B; the Gate B bytes were never retained) and passed the in-memory
  result to the production `extract_excerpt()` public interface
  (`src/data_access/edinet/document_extractor.py`) — no
  `DocumentService`, no retry wrapper, no cache, no candidate mutation.
  Result: `ExtractionState.PARSE_FAILED`, `excerpt_original=None`, no
  unhandled exception at either the fetch or the extraction layer.
  Offline code inspection (no further live call) confirmed that
  `ExtractionState.PARSE_FAILED` is a controlled, tested outcome for the
  PDF extractor. In particular, a valid PDF with no extractable embedded
  text takes the `_PDF_NO_TEXT_DETAIL` branch and returns a normal
  `ExtractionResult` rather than raising. Gate C did not capture
  `result.detail`, so the precise cause for this specific document's
  `PARSE_FAILED` outcome—encrypted, parser-level failure, or no
  extractable text—was not established. The payload's size and
  `%PDF-1.5` header make the no-text-layer explanation a plausible but
  unconfirmed hypothesis.
- **No state changed in either gate**: `edinet-cand-S100YGH5` remains
  exactly as backfilled at Gate 10 (`Candidate detected` / `Not
  fetched` / `excerpt_original=None` / `Not requested` / one
  state-history entry). No database, cache file, translation record,
  signal, alert, scheduler entry, or Radar Inbox publication state
  changed as a result of Gates B or C. EDINET remains 3 FilingEvents /
  1 CandidateSignal; DART 520/23 and EDGAR 10/1 unchanged.
- **Current policy, explicit**: fail closed. A PDF without usable
  native (embedded) text does not produce an excerpt, does not advance
  `extraction_state` past what the extractor reports, and triggers no
  downstream automated enrichment (no translation, no candidate
  finalization, no classification). `PARSE_FAILED` is the correct,
  final, human-reviewable outcome for this shape of document under the
  current pilot scope.
- **OCR is explicitly out of scope** pending a separate evidence,
  attribution, cost, and quality policy — not a technical gap to be
  quietly closed, a scope boundary requiring its own review before any
  image-to-text pipeline is considered for this pilot.
