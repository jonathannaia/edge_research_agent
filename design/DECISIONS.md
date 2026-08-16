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
