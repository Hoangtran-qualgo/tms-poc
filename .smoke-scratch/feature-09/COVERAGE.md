# Feature 09 — Search — coverage matrix

Spec source: `specs/features/09-feature-search-NEW.md`
Source files in scope:
- `app/storage.py` — `Storage.search` (~85 LOC) + `_scope_to_segments` + `_iter_feature_files`.
- `app/server.py` — `GET /api/search` (`search`, ~14 LOC) + `GET /ui/search` (`ui_search`, ~30 LOC).
- `app/templates/search_results.html` — three-variant result partial (59 LOC).
- `app/templates/base.html` — top-bar `#search-form` widget (lines 21–51).
- `app/static/app.js` — `tmsWireSearch` (~45 LOC, lines ~1451–1495).

## Method

Same as previous features:

- Enumerate rules from the spec with a stable ID per rule.
- One smoke per rule (or per tightly-coupled cluster) under
  `.smoke-scratch/feature-09/F09_<MM>[a-z]?_<slug>.py`.
- Each smoke prints `PASS <id>: <invariant>` and is independently
  runnable.
- Rules headed `## Public surface` → `RT*` (routes) / `ST*` (storage
  method) / `HS*` (hit shape) / `FM*` (base.html form) / `WS*`
  (`tmsWireSearch`).
- Rules headed `## Invariants & rules` → grouped by sub-heading:
  `MS*` (match semantics), `SF*` (scope filter), `UX*` (result UX),
  `IF*` (input firing), `TG*` (tag input convention).
- Rules under `## Acceptance criteria` → `AC*`.

Per the **feature-04 / feature-08 Step-1 sign-off** (carried forward):
smokes do **not** spin up a JS runtime. `tmsWireSearch` rules
(debounce, Enter-cancels-debounce, change-refire) are covered by
**static regex inspection** of `app/static/app.js`. HTTP round-trips
use the Flask test client end-to-end through `/api/search` and
`/ui/search`; storage semantics are exercised end-to-end through the
JSON route (re-owning the rule from feature-09's frame) rather than by
calling `Storage.search` directly.

A row is `covered` when:
- An end-to-end render or HTTP round-trip can reach it, OR
- The pure-JS body has a tight, spec-anchored regex assertion in
  the corresponding `F09_*.py` file.

## Matrix

| # | Rule | Spec § | Smoke file | Status |
|---|---|---|---|---|
| RT1 | `GET /api/search` accepts `q`, `scope`, `match`, `case` query args (`case` truthy ∈ {true,1,yes}, case-insensitive); returns JSON `{ "hits": [SearchHit, ...] }`. | Public surface → Routes | `F09_01_api_search_shape.py` | covered |
| RT2 | `GET /ui/search` accepts the same query args, renders `search_results.html`. Empty/whitespace `q` → partial with `show_empty_state=True`, `hits=[]`, `query=""` (server short-circuits before calling `Storage.search`). | Public surface → Routes | `F09_02_ui_search_render.py` | covered |
| ST1 | `Storage.search(query, *, scope="all", match="text", case_sensitive=False) -> list[dict]`; invalid `match` (not in {text,tag}) → `ValueError`. | Public surface → Storage | `F09_03_search_errors.py` (invalid-match → 400 via API) (+ cross-credit `F02_07_search.py`) | covered |
| ST2 | `match="text"`: substring against `Feature.description`; at most one hit per file. | Public surface → Storage | `F09_04_match_text.py` (+ cross-credit `F02_07` SR1) | covered |
| ST3 | `match="tag"`: substring against each `Scenario.tags` value; one hit per matching tag, each carrying the matched tag value. | Public surface → Storage | `F09_05_match_tag.py` (+ cross-credit `F02_07` SR2) | covered |
| ST4 | `scope`: `all` \| `project:<name>` \| `module:<proj>/<mod>`. | Public surface → Storage | `F09_07/08/09_scope_*.py` (+ cross-credit `F02_07` SR3) | covered |
| ST5 | `case_sensitive` defaults `False`; case-insensitive via `str.lower()` on both sides (NOT `casefold()`) — German ß and similar fold edge cases round-trip as-is. | Public surface → Storage | `F09_06_case.py` (incl. ß quirk) | covered |
| HS1 | Hit shape `{file_path, description, matched_field, match_value}`; `matched_field ∈ {"description","tag"}`; text mode echoes the query as `match_value`, tag mode carries the matched tag. | Public surface → Hit shape | `F09_04` (text mode) + `F09_05` (tag mode) (+ cross-credit `F02_07` SR4) | covered |
| FM1 | `base.html` renders `#search-q` (input), `#search-scope` (select), `#search-match` (select: text/tag), `#search-case` (checkbox) inside `<form id="search-form" onsubmit="event.preventDefault();">`. | Public surface → Form | `F09_11_form.py` (render-and-grep) | covered |
| FM2 | The form is wired in JS (`tmsWireSearch`), NOT via HTMX trigger filters (HTMX 2.x bare-name filter quirk). | Public surface → Form | rationale; behaviour covered by WS* | n/a |
| WS1 | `q.keydown` Enter → `preventDefault`, cancel any pending debounce timer, `fire()` immediately. | Public surface → Wiring | `F09_12_wire_enter.py` (static JS body) | covered |
| WS2 | `q.input` → `scheduleFire(300)` (300 ms idle debounce). | Public surface → Wiring | `F09_13_wire_debounce.py` | covered |
| WS3 | `scope`/`match`/`case` `change` → `fire()` immediately **iff** `q.value.trim()` is non-empty. | Public surface → Wiring | `F09_14_wire_change_refire.py` | covered |
| WS4 | `fire()` builds `URLSearchParams{q,scope,match,case}` and calls `htmx.ajax("GET", "/ui/search?"+params, {target:"#main-pane", swap:"innerHTML"})`. | Public surface → Wiring | `F09_15_wire_fire_ajax.py` | covered |
| MS1 | Substring match only — no regex, no fuzzy. | Invariants → Match semantics | `F09_04_match_text.py` (+ cross-credit `F02_07` SR1) | covered |
| MS2 | Default case-insensitive via `str.lower()` on both needle and haystack. | Invariants → Match semantics | `F09_06_case.py` | covered |
| MS3 | Empty/whitespace-only `query` → `[]` at the storage layer; UI layer also short-circuits to the empty-state partial when `q` is blank. | Invariants → Match semantics | `F09_02_ui_search_render.py` (UI short-circuit) + `F09_01_api_search_shape.py` (API `[]`) | covered |
| MS4 | Files that fail to parse (`GherkinParseError`, `OSError`, `UnicodeDecodeError`) are silently skipped during the walk. | Invariants → Match semantics | `F09_10_unparseable_skip.py` (write malformed `.feature` on disk → search still returns the good hits, no raise) | covered |
| MS5 | `match="text"` matches anywhere in `Feature.description` (real-newline string, not the on-disk literal `\n`). | Invariants → Match semantics | `F09_04_match_text.py` (multi-line description, needle spanning a real newline boundary) | covered |
| MS6 | `match="tag"`: substring against each tag value (already stripped of `@`); one hit per matching tag. | Invariants → Match semantics | `F09_05_match_tag.py` (+ cross-credit `F02_07` SR2) | covered |
| SF1 | `"all"`: every `.feature` under the data root. | Invariants → Scope filter | `F09_07_scope_all.py` (+ cross-credit `F02_07` SR3) | covered |
| SF2 | `"project:<name>"`: only files whose first segment is `<name>`. | Invariants → Scope filter | `F09_08_scope_project.py` (+ cross-credit `F02_07` SR3) | covered |
| SF3 | `"module:<proj>/<mod>"`: only files whose first two segments match. | Invariants → Scope filter | `F09_09_scope_module.py` (+ cross-credit `F02_07` SR3) | covered |
| SF4 | Invalid scope syntax → `ValueError` → HTTP 400 (API) / inline 400 snippet (UI). | Invariants → Scope filter | `F09_03_search_errors.py` (malformed `scope=project:` → 400 on both routes) | covered |
| UX1 | `show_empty_state=True` → "Type a query in the search box above and press Enter." | Invariants → Result UX | `F09_16_results_empty_state.py` | covered |
| UX2 | `len(hits) == 0` → "No matches for &ldquo;{{query}}&rdquo;" + hint. | Invariants → Result UX | `F09_17_results_no_matches.py` | covered |
| UX3 | `len(hits) == 1` → inline `<script>` runs `htmx.ajax("GET", "/ui/file/<file_path>", {target:"#main-pane", swap:"innerHTML"})` — auto-navigates. | Invariants → Result UX | `F09_18_results_single_autonav.py` | covered |
| UX4 | `len(hits) >= 2` → table (File / first-line Description / Matched badge); each row `hx-get="/ui/file/<path>"`, `hx-target="#main-pane"`, `hx-swap="innerHTML"`; tag badges prefix `@`. | Invariants → Result UX | `F09_19_results_list_view.py` | covered |
| IF1 | Empty queries never fire from the input (client skips to avoid stale-flash); server still accepts them (empty-state variant). | Invariants → Input firing | `F09_14_wire_change_refire.py` (static: guard on `q.value.trim()`) + `F09_02` (server accepts) | covered |
| IF2 | Enter cancels any pending debounce and fires immediately. | Invariants → Input firing | `F09_12_wire_enter.py` (static) | covered |
| IF3 | 300 ms is the only debounce; not configurable. | Invariants → Input firing | `F09_13_wire_debounce.py` (static: literal `300`, single timer) | covered |
| TG1 | Users type tag values without `@`; the match is against the bare stored values, not the rendered `@`-prefixed chips. | Invariants → Tag input convention | `F09_05_match_tag.py` (search "needle" matches stored "needle1") (+ cross-credit `F02_07` SR2) | covered |
| AC1 | An empty query renders the "Type a query…" empty state and fires no `GET /api/search`. | Acceptance criteria | duplicates MS3 (UI half, `F09_02`) + IF1 (client-skip, `F09_14`); tracked there | n/a |
| AC2 | A query matching exactly one file auto-navigates the main pane to that file's editor without an intermediate list view. | Acceptance criteria | duplicates UX3; tracked there | n/a |
| AC3 | A `match=text` query inside a `Feature.description` emits exactly one hit for that file. | Acceptance criteria | duplicates ST2/MS5; tracked there | n/a |
| AC4 | A `match=tag` query inside two distinct tag values on the same scenario emits two hits for that file. | Acceptance criteria | duplicates ST3/MS6; tracked there | n/a |
| AC5 | Changing `scope`/`match`/`case` while the query is non-empty re-fires search immediately. | Acceptance criteria | duplicates WS3; tracked there | n/a |
| AC6 | Typing fast then pausing fires exactly one search after the 300 ms pause (not one per keystroke). | Acceptance criteria | duplicates WS2/IF3; tracked there | n/a |
| AC7 | Pressing Enter cancels the pending debounce and fires immediately. | Acceptance criteria | duplicates WS1/IF2; tracked there | n/a |

## Summary

- Total rules: **37** countable (2 RT + 5 ST + 1 HS + 2 FM + 4 WS + 6 MS + 4 SF + 4 UX + 3 IF + 1 TG + 7 AC), with **7 AC/FM2 rows** flagged `n/a` (AC1–AC7 all dedupe onto behaviour rules; FM2 is rationale).
- Distinct work units: **30** (37 − 7 `n/a`).
- `covered`: **30** (all distinct work units — Step 4 complete).
- `partial`: **0** (the 10 ex-`partial` storage/hit-shape rules are now
  re-owned end-to-end through `/api/search`; cross-credit to `F02_07`
  stays noted).
- `missing`: **0**.
- `n/a`: **8** (AC1–AC7 dedupe + FM2 rationale).
- **Smoke files: 19** (`F09_01..F09_19`) — finer-grained than the
  original 10 per the Jun 9 splitting directive (see sign-off). All 19
  pass individually and as a suite.

Map of the 30 distinct work units → 19 files (some rules share a file
when their setup + assertions overlap; AC dedupes are `n/a`):

- 4 route/error rules → `F09_01`, `F09_02`, `F09_03`.
- 6 match-semantics + 1 hit-shape + 1 case rule → `F09_04`, `F09_05`, `F09_06`.
- 3 scope rules → `F09_07`, `F09_08`, `F09_09`.
- 1 skip rule → `F09_10`.
- 1 form rule → `F09_11`.
- 4 wiring + 3 input-firing rules → `F09_12`–`F09_15`.
- 4 result-UX rules → `F09_16`–`F09_19`.

## Drifts / observations surfaced at audit

- **`#search-scope` only offers `All` in `base.html`** (line 37) and
  `tmsWireSearch` never populates project/module options. So the
  top-bar UI in v1 can only ever issue `scope=all`; the
  `project:<name>` / `module:<proj>/<mod>` scopes the storage + route
  layers fully support are reachable **only via direct query params**
  (e.g. a hand-built `/ui/search?scope=project:Alpha` link). Not a
  contradiction with the spec (which documents the scope *grammar*,
  not a populated picker), but worth a pinned note: `F09_11_form.py`
  asserts the as-shipped single-option select and flags the gap in
  its docstring. **Signed off (Jun 9): pin as a real assertion.**
- **Whitespace-only `q` divergence:** `Storage.search` returns `[]`
  for whitespace-only `q` (MS3), but `ui_search` calls `q.strip()`
  first → routes whitespace-only `q` into the `show_empty_state=True`
  branch (not the "No matches" branch). The `/api/search` route does
  NOT strip, so it delegates to `Storage.search` which returns `[]`.
  Both endpoints behave correctly per spec, just via different code
  paths; `F09_01`/`F09_02` assert each path explicitly.

## Proposed file map (Step 4)

19 files: `F09_01..F09_19`. Each is independently runnable; per the
Jun 9 splitting directive, multi-variant sections are split so each
sub-file has a distinct setup/assertion focus (duplicated setup
boilerplate is accepted).

- `F09_01_api_search_shape.py` — RT1 (`{hits:[...]}` envelope, `case`
  param truthy parsing), MS3 (API empty `q` → `[]`).
- `F09_02_ui_search_render.py` — RT2 (renders `search_results.html`),
  MS3 (UI strips → empty-state short-circuit).
- `F09_03_search_errors.py` — ST1 (invalid `match` → 400), SF4
  (malformed `scope` → 400 on both `/api/search` and `/ui/search`).
- `F09_04_match_text.py` — ST2 (≤1 hit/file), MS1 (substring not
  regex), MS5 (real-newline description), HS1 (text-mode shape).
- `F09_05_match_tag.py` — ST3 (one hit per matching tag), MS6, TG1
  (bare-value match), HS1 (tag-mode shape).
- `F09_06_case.py` — ST5 + MS2 (`str.lower()` default; `case=true`
  sensitivity; ß `lower()`-vs-`casefold()` quirk pinned).
- `F09_07_scope_all.py` — SF1 (all files under root).
- `F09_08_scope_project.py` — SF2 (`project:<name>` first-segment).
- `F09_09_scope_module.py` — SF3 (`module:<proj>/<mod>` two-segment).
- `F09_10_unparseable_skip.py` — MS4 (malformed `.feature` skipped).
- `F09_11_form.py` — FM1 (+ scope-picker single-option drift pin).
- `F09_12_wire_enter.py` — WS1 + IF2 (Enter cancels debounce, fires).
- `F09_13_wire_debounce.py` — WS2 + IF3 (300 ms idle, single timer).
- `F09_14_wire_change_refire.py` — WS3 + IF1 (change refire iff
  non-empty; empty-skip).
- `F09_15_wire_fire_ajax.py` — WS4 (`URLSearchParams` + `htmx.ajax`
  target/swap).
- `F09_16_results_empty_state.py` — UX1.
- `F09_17_results_no_matches.py` — UX2.
- `F09_18_results_single_autonav.py` — UX3.
- `F09_19_results_list_view.py` — UX4.

## Step 1 — sign-off (Jun 9, 2026)

All four decisions **approved**:

1. **Re-own storage rules via `/api/search`** — the 10 `partial`
   storage/hit-shape rules get dedicated feature-09 smokes that
   exercise them end-to-end through the JSON route; cross-credit to
   `F02_07` stays noted.
2. **Static JS inspection for `tmsWireSearch`** — no JS runtime;
   WS*/IF* asserted by regex on the `tmsWireSearch` body.
3. **Pin the scope-picker drift** — `F09_11_form.py` asserts the
   single `All` option and documents the query-param-only scopes.
4. **One file per surface/cluster** — accepted, then refined to **19
   files** per the splitting directive: "split long tests into
   smaller ones, ensure they can run individually, duplicated effort
   accepted if assertions are not fully identical."

Step 2 (restructure) is expected to be a **no-op** — no existing
smoke primary-frames feature-09 (`F02_07` is storage-core's; it stays
put and is cross-credited). Step 4 (gap-fill) writes the 19 smokes.

## Step 2 — executed (no moves)

Verification run: grepped the entire `.smoke-scratch/` tree for the
feature-09 surfaces — `/api/search`, `/ui/search`, `tmsWireSearch`,
`search_results`, `search-form`, `search-q` — across all `*.py`
smokes. **Zero matches.** No existing smoke exercises any search
route, the JS wiring, the results template, or the top-bar form.

- `feature-02/F02_07_search.py` — primary frame is **feature-02**
  (storage-core). It imports `Storage` directly and asserts
  `Storage.search` semantics (SR1–SR4: text/tag/scope/hit-shape)
  without touching Flask, the routes, or the templates. It
  cross-credits feature-09 rules (ST1–ST4, HS1, MS1, MS6, SF1–SF3,
  TG1) but stays in feature-02; feature-09 re-owns those end-to-end
  through `/api/search` in Step 4.

No files moved, renamed, or merged. Proceeding to Step 3.

## Step 3 — executed (no refines)

No moves → no refines. The cross-credit annotations in the matrix
(`+ cross-credit F02_07 ...`) already record the shared coverage;
nothing in `F02_07` needs tightening or re-scoping for feature-09's
sake. Proceeding to Step 4 (gap-fill) — 19 smokes.

## Step 4 — executed (19 smokes written, all passing)

All 19 planned smokes (`F09_01..F09_19`) written and verified:

- Individually: each `F09_*.py` runs standalone and prints its
  `PASS` line.
- As a suite: `python .smoke-scratch/run.py --filter feature-09` →
  **19/19 passed; 0 failed**.
- Full repo suite: `python .smoke-scratch/run.py` →
  **119/119 passed; 0 failed** (no regressions in features 01–08).

Notes from execution:

- `F09_04_match_text.py`: the multiline-description fixture token was
  renamed to `WRAPTOKEN` after the default case-insensitive match made
  the `needle` query collide with a `NEEDLE…`-containing fixture line.
- `F09_10_unparseable_skip.py`: the malformed `.feature` is written
  straight to disk with `pathlib.Path.write_text` (bypassing
  `Storage.write_raw`, which rejects bad Gherkin) so the walk hits a
  real on-disk parse failure; search returns only the good hit and
  does not 500.
- `F09_19_results_list_view.py`: the first-line-only assertion targets
  the rendered cell body, since the full multi-line description still
  rides along in the cell's `title=""` attribute.

Coverage: **30/30 distinct work units covered; 0 missing; 0 partial.**
Feature-09 search is fully covered.
