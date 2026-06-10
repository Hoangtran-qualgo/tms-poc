# 02 · UI/UX styling & detailing enhancements

_Tech spec. Filed Jun 10, 2026 (Investigate phase; promoted from_
_`IN-PROGRESS.md` § Must have); **Plan + Do shipped Jun 10, 2026** — all_
_five enhancements (E1–E5) + the shared palette foundation are implemented_
_and verified (full smoke suite **244/244**; see `DONE.md` for the as-built_
_breakdown). Five UI/UX styling + detailing enhancements, each explicitly_
_**Must have** and investigated / shipped **individually**. Tracks tech_
_movement of the UI surface — presentation + freshness polish, not a new_
_product feature. Investigation grounded against the live code Jun 10, 2026 —_
_each enhancement below carries current-state findings (with file:line refs),_
_a proposed approach, and a **confidence** level; cross-cutting choices_
_are collected under § Decisions (**D1–D4 all resolved**), and assumptions_
_are audited under § Assumptions & risk register (A1–A8; one earlier E5_
_claim corrected on review)._

## Summary

A batch of detailing enhancements to the **test-run results** and
**test-report** detail views, plus one **freshness** fix so newly-created
artifacts appear in their sidebar tree without a manual refresh. The
through-line is consistency: a single shared **status palette/style**
should drive both the run-results list and the report detail views, and
key report factors should be visually emphasised.

These are presentational/UX changes (one is a tree-refresh behaviour fix);
there is **no data-model or on-disk change**. Each enhancement is
independent and can be specced → built → verified on its own; this doc is
the shared source of truth so the five do not drift apart (especially the
two that share the status palette). **Implementation must stay consistent
with this spec**: the palette colour codes and the per-enhancement
touchpoints below are authoritative — update this doc in the same change
if the code diverges.

## Scope

In scope:

- Run-results detail: `Result` column width, folder grouping of rows, and
  per-status colour/style.
- Report detail: status colour/style consistent with the run-results list,
  and visual emphasis of each report type's key factors.
- A single shared status palette / style tokens reused across run + report
  surfaces.
- Auto-refreshing the relevant sidebar tree after a successful create
  (test case / test run / test report).

Out of scope:

- New report types, new run semantics, or any change to `RUN_RESULTS`.
- Data-model, on-disk, or HTTP-contract changes.
- Reworking the watcher / SSE pipeline itself (the create-refresh item
  only closes any gap in how the **client** consumes the existing
  `sse:change` event).

## Status palette — single source of truth (drives E3 + E4)

**Decision (D1 — resolved Jun 10, 2026): `SKIPPED` = purple.** The five
result statuses have exactly **one** canonical colour, defined in **one**
place and referenced by every surface (run-editor `Result`, report
`case_trend` cells, report `status` params). No surface may inline its own
colour map.

**Canonical palette (the source of truth):**

| Status | Colour | CSS value | Tailwind equiv. |
|---|---|---|---|
| `PASSED` | green | `#059669` | `emerald-600` |
| `FAILED` | red | `#e11d48` | `rose-600` |
| `EXECUTING` | blue | `#0284c7` | `sky-600` |
| `SKIPPED` | **purple** | `#9333ea` | `purple-600` |
| `PENDING` | orange | `#d97706` | `amber-600` |

**Where it lives (single definition):** `app/static/app.css`, as five
`data-status` attribute selectors. `app.css` is otherwise empty and there
is **no Tailwind build** (CDN browser build only — `base.html:8`), so raw
CSS here is the only cross-consumer home that both server-rendered Jinja
and JS-set elements can share verbatim:

```css
[data-status="PASSED"]    { color: #059669; }
[data-status="FAILED"]    { color: #e11d48; }
[data-status="EXECUTING"] { color: #0284c7; }
[data-status="SKIPPED"]   { color: #9333ea; }
[data-status="PENDING"]   { color: #d97706; }
```

**How consumers reference it (no duplicated colours):**

- Server-rendered cells emit `data-status="{{ value }}"` — e.g. the report
  `case_trend` Result cell (`report_detail.html:161`), **replacing** the
  current inline `result_colors` Jinja map (`report_detail.html:136-142`),
  which is deleted as part of E4.
- The run-editor `Result` is a `<select>`; JS sets `el.dataset.status =`
  `el.value` on render and on `change` (`06_run_editor.js`) so the same
  CSS colours it (E3).
- An absent / em-dash (`—`) value carries no `data-status`, so it falls
  back to the default text colour (preserves today's muted em-dash in
  `case_trend`, `report_detail.html:161`).

Net: the colour code lives in exactly one file; E3 and E4 only attach the
`data-status` hook, never a colour. (Tailwind-equivalent names above are
for reference only — the authoritative values are the hex codes in
`app.css`.)

## Enhancements

### E1 — Widen the run-editor `Result` column to fit the longest status

- **Current state**: the results table is `table-fixed` with the `Result`
  header at `w-32` (8rem/128px) — `run_editor.html:78` (live rows) and
  `:149` (clone template). The report `case_trend` `Result` column is also
  `w-32` (`report_detail.html:149`). `EXECUTING` is the widest value.
- **Approach (A4 resolved)**: let the browser render; size the status
  element so its width fits the **longest defined status** (`EXECUTING`).
  Apply in both the run table and the report trend table for consistency.
- **Confidence: HIGH** — exact locations known; pure presentational.

### E2 — Group run-editor results by folder

- **Current state**: rows are a flat `{% for r in run.results %}`
  (`run_editor.html:84`); each row already masks the path — muted folder
  span + emphasised filename (`:96-108`), full path on `<tr
  data-file-path>` for serialize/click. New rows are cloned client-side
  from `#run-result-row-template` by `_createResultRow`
  (`06_run_editor.js:110`); ordering is append/insertion via
  `_afterRowsChanged`.
- **Approach (D2 resolved — server-side grouping)**: group `run.results` by
  folder in the Jinja loop (`file_path.rsplit('/',1)[0]`), preserving
  first-seen folder order and within-folder order; emit one **plain heading
  row** per group — `<tr class="run-group-head" data-group-folder="…">`
  `<td colspan="4">…</td></tr>` — and render each result row
  **filename-only** (drop the muted folder span; the heading now carries
  the folder). `_createResultRow` drops the folder span too; "+ Add case"
  inserts each new row **after the last row of its folder group** (creating
  a heading if the folder is new) instead of `tbody.appendChild`.
- **Serialize/dirty integration (verified — this *was* the MEDIUM risk)**:
  heading rows are the only complication and every touch-point is small and
  known. `_readCurrent` (`06_run_editor.js:58`) and the add-flow `existing`
  de-dupe (`:159`) → query `#run-results tbody tr[data-file-path]` so
  headings are skipped (one-token change each); `_afterRowsChanged`
  (`:136-137`) → count `tbody.querySelectorAll("tr[data-file-path]")` for
  the empty-state toggle; the remove handler (`:88-92`) → after removing a
  result row, drop its group heading when that group has no remaining
  `tr[data-file-path]`. The `<select>` options stay server-rendered from
  the same `<template>` (`run_editor.html:139`), so the E3 palette hook is
  unaffected.
- **Order-sensitivity (found + solved)**: grouping reorders the baseline
  DOM relative to on-disk order, and both the dirty check (`liveJson` vs
  `baselineJson`, `:198-199`) and `onExternalChange` (`diskJson` vs
  `baselineJson`, `:315-340`) compare **order-sensitively** — so, left
  as-is, merely opening an ungrouped run could flash a false "changed
  externally" banner on the next `sse:change`. **Fix**: normalise the
  *comparison* projection only — sort results by `file_path` before
  `JSON.stringify` for the baseline / live / disk comparisons — while the
  **Save** payload keeps the visual (grouped) DOM order via `_readCurrent`.
- **Persistence**: Save serialises results in DOM (grouped) order;
  `patch_run` → `TestRun.from_dict` → `write_run` preserves array order
  verbatim (`routes_runs.py:112-116`; `validate_run` only checks
  no-duplicate `file_path`). The grouped order is therefore persisted
  **only when the user actually saves an edit** — opening a run never
  rewrites disk. Deterministic and non-surprising.
- **Confidence: HIGH** — structure chosen (single tbody + `run-group-head`
  rows), every JS touch-point enumerated with a concrete edit, and the one
  subtle interaction (order-sensitive compare) identified and solved.
- **Post-ship extension (Jun 10, 2026, user feedback)**: the same
  folder-grouping idiom was applied to the **ranking-report bucket case
  lists** (`report_detail.html`, the shared bucket template for
  `enum_ranking` / `tag_ranking` / `tag_inventory`), which were previously a
  flat list of full paths. Each bucket now groups its cases by folder
  (first-seen order) with a **folder badge heading** + filename-only items;
  the full path stays on the `<a hx-get>` for click-through. Server-side Jinja
  grouping only — no view-model (`reporting.py`) change. Smoke: `T02_08`.
- **Folder-heading contrast (Jun 10, 2026, user feedback)**: the folder
  heading on **both** grouping surfaces is rendered as a badge — bold dark
  text on a slate-200 pill (`inline-block font-mono text-xs font-semibold`
  `text-slate-700 bg-slate-200 rounded px-1.5 py-0.5`) — to lift contrast
  against the muted case filenames. Applied to the `report_detail.html`
  bucket headings and the run-editor `run-group-head` rows (server row +
  clone template); `06_run_editor.js:_createGroupHead` writes the badge
  `<span>` so JS-created headings match.

### E3 — Colour + style the run-editor `Result` column per status

- **Current state**: the `<select class="run-result-select …">` carries no
  per-status colour (`run_editor.html:112`, `:149`). The palette currently
  exists only in report `case_trend` (above).
- **Approach (A5 resolved)**: colour the **closed `<select>` display** via
  `data-status` (no badge). JS sets `el.dataset.status = el.value` on
  render and on `change` (`06_run_editor.js`); the shared palette
  (§ Status palette) colours it. The open option-list is left native.
- **Confidence: HIGH** — mechanism + palette (D1) + closed-select choice
  (A5) all decided.

### E4 — Consistent + highlighted styling in report detail views

- **Current state**: report detail already (a) colours `case_trend`
  results via the inline map (`report_detail.html:136-161`); (b) renders a
  **muted** params line — `status / kind / tag / scope / case` as a
  `text-slate-400` label + `font-mono` value (`:43-49`); (c) shows run/
  case count muted (`view.total`, `:50`). Ranking/inventory bucket tables
  (`:77-118`) use slate bars, no status colour. View-model fields
  available (from `reporting.py`): `view.params.{status,kind,tag,scope,`
  `case_path}`, `view.total`, `view.buckets[]`, `view.trend[]`,
  `view.warnings`, `view.current_tags`, `view.current_enums`.
- **Approach (A7 + D3 resolved)**: (a) reuse the **same** single-source
  palette as E3, colouring the `status` param specifically on the
  **enum-ranking** report (A7); (b) emphasise the key factors — **bold is
  the must-have** treatment (with **status** also palette-coloured), while
  **badge** and **size** are *consider* (optional). Factors: **status**,
  **kind**, **case**, **number of run(s)**, **tag**, **scope**.
- **Confidence: HIGH** — treatment decided (D3); `view.params.status` is
  always populated by `_params` for every type (`reporting.py:54-61`),
  so no residual.

### E5 — Auto-refresh sidebar trees after a successful create

- **Root cause (confirmed in code — corrected on review Jun 10, 2026)**: the
  watcher **suppresses `sse:change` for any path the app itself just
  wrote**, for a `RECENT_WRITE_TTL_SECONDS = 0.5s` window (`_core.py:59`;
  `watcher.py:154-158`). `_mark_write` records **both the target and its
  parent dir** (`_core.py:235-254`), and **every** in-app mutation calls it
  — files *and folders* alike (`create_folder` → `_folders.py:56-57`;
  `create_run`/group, `create_report`, `create_feature`, …). Watchdog
  latency (≪0.5s) plus the 0.1s debounce mean the suppression reliably
  wins, so **no in-app create emits `sse:change`**. Sidebar trees refresh
  *only* on `hx-trigger="sse:change"` (`base.html:115` for `#tree-pane`;
  `02_sidebar.js:68`/`:85` for the run/reports panes), and all three create
  flows refresh **only `#main-pane`** (`03_folder_actions.js:206`→`:22`,
  `04_run_create.js:489`, `05_report_flows.js:397`). → After **any** in-app
  create the relevant sidebar tree stays stale until an *external* change
  fires or the user clicks the existing manual **Refresh tree** button
  (`tree.html:75-81`, whose own comment calls it a "safety net when the
  watcher misses an event"). **Correction**: an earlier draft of this spec
  claimed folder creates already auto-refresh — they do **not**
  (`create_folder` is self-write-marked too).
- **Approach (D4 + A2 resolved)**: after a successful create, refresh
  **only the artifact's own tab's tree**, re-GETting it so it reflects the
  current on-disk state (the new artifact shows up as on local disk):
  test case → Directory tree (`#tree-pane`); test run → Test-run tree
  (`#test-run-pane`); test report → Reports tree (`#reports-pane`).
  Re-GET the pane (or `htmx.trigger(pane, 'sse:change')`) only if it is
  mounted; a not-yet-mounted pane loads fresh on first open. The
  client-side trigger is preferred over relaxing the deliberate watcher
  self-write suppression (which keeps the editor's external-change banner
  quiet during self-saves).
- **Confidence: HIGH** — root cause confirmed; refresh scope decided (D4).
- **Touchpoints**: `app/static/03_folder_actions.js` (`tmsCreateFile`),
  `app/static/04_run_create.js` (`tmsCreateRun`),
  `app/static/05_report_flows.js` (`tmsCreateReport`),
  `app/static/02_sidebar.js` (pane mount + `sse:change` wiring),
  `app/static/01_tree.js`.

## Decisions (all resolved)

- **D1 — `SKIPPED` colour. RESOLVED (Jun 10, 2026): purple (`#9333ea`).**
  `SKIPPED` is purple on every surface; the existing `case_trend`
  muted-slate rendering migrates to the canonical palette (§ Status
  palette).
- **D2 — run-editor folder grouping UX. RESOLVED (Jun 10, 2026): plain
  group labels** (non-collapsible heading per folder); a newly-added case
  lands in its folder group (re-group on add). Affects E2.
- **D3 — report key-factor emphasis. RESOLVED (Jun 10, 2026): bold = must
  have**; **badge** + **size** = *consider* (optional). Status is also
  palette-coloured. Affects E4.
- **D4 — E5 refresh scope. RESOLVED (Jun 10, 2026): only the artifact's own
  tab.** Each create reloads just its own tree to current disk state
  (test case → Directory, test run → Test-run, test report → Reports), so
  the new artifact appears as on local disk. Affects E5.

## Assumptions & risk register

Status key: ✅ verified in code or decided · ⚠️ corrected during this review.

| # | Assumption | Status | Mitigation |
|---|---|---|---|
| A1 | E5: **all** in-app creates are SSE-suppressed (files *and* folders); the 0.5s TTL reliably beats watchdog latency | ⚠️ corrected (earlier draft said folders auto-refresh; they don't) | Client-side refresh after create; do **not** weaken the deliberate suppression |
| A2 | E5: refresh = reload the artifact's **own** tab's tree to current disk state (new artifact shows as on local disk) | ✅ decided (D4) — each create re-GETs only its own pane; no dependence on `list_tree` filtering | case → `#tree-pane`, run → `#test-run-pane`, report → `#reports-pane` |
| A3 | E2: run-editor serialize/dirty assume one `tr` = one result row | ✅ resolved — every touch-point enumerated; filter reads to `tr[data-file-path]`, count by it, drop empty headings, normalise compare order | See E2 § Serialize/dirty + Order-sensitivity |
| A4 | E1: size the status element to the longest defined status | ✅ decided — let the browser render; width = longest status (`EXECUTING`) | No static clip-check needed |
| A5 | E3: a `<select>`'s status colour can be CSS-driven | ✅ decided — colour the **closed** select display via `data-status` (works cross-browser); open option-list left native, no badge | — |
| A6 | E4: the palette migration keeps the muted em-dash fallback | ✅ verified (no `data-status` on `—` → default colour) | — |
| A7 | E4: `view.params.status` is available for the **enum-ranking** report | ✅ verified — `_params` always sets `status` from `report.status` for every type (`reporting.py:54-61`,`:82`,`:182`) | — |
| A8 | Palette single source works as raw CSS (no Tailwind build) | ✅ verified (`app.css` is a plain `<link>`, `base.html:8`/`:11`) | Use hex values (done in § Status palette) |

**Status**: all product decisions (D1–D4) and assumptions (A1–A8) are
resolved, decided, or verified — **no residual open items**. A7 (the last
deferred check) is now confirmed in `reporting.py`.

## Confidence summary

| # | Enhancement | Confidence | Gated by / residual risk |
|---|---|---|---|
| E1 | Result column width | **HIGH** | width = longest status (A4 decided) |
| E2 | Group results by folder | **HIGH** | structure + all JS touch-points + order-compare fix specified (D2/A3) |
| E3 | Run Result colour/style | **HIGH** | closed-select colour (A5) + palette (D1) decided |
| E4 | Report detail consistency/highlight | **HIGH** | bold + enum-ranking decided (D3); `params.status` verified (A7) |
| E5 | Auto-refresh trees on create | **HIGH** | refresh own tab only (D4) decided |

## Acceptance criteria

- **E1**: every `RUN_RESULTS` value renders on one line in the `Result`
  column at the default editor width; no clipping/wrap for `EXECUTING`.
- **E2**: a run with multiple cases in one folder shows them under a
  single folder heading, each row labelled by file name only; add/remove
  still works and re-groups correctly.
- **E3 / E4**: run-results and report detail use the **same** status
  palette (E3 and E4 share one source of truth); report detail visibly
  emphasises status / kind / case / run-count / tag / scope as applicable
  to the type.
- **E5**: creating a case / run / report surfaces the new artifact in its
  tree without a manual reload, for both active and mounted-but-hidden
  panes.
- Each enhancement ships with its own smoke(s) under
  `.smoke-scratch/tech-02/`, suite green after each.

## Evolution / versioning

This doc is the home for **UI/UX styling & detailing** tech movement.
Following the `/specs` naming rule (`<NN>-tech-<name>-<NEW|UPDATE>.md`):

- **Small** future styling/detailing tweaks → rename this file's suffix
  `NEW` → `UPDATE` and append a new dated version section here (keep the
  prior content; do not fork a new index).
- **Large** enhancements → create a **new** separate
  `/specs/tech/<NN>-tech-<name>-NEW.md` with its own index.

## Affects

- `app/templates/run_editor.html` + `app/static/06_run_editor.js` — `Result`
  column width (E1), folder-grouped rows (E2), per-status colour/style (E3).
- `app/templates/report_detail.html` + `app/static/05_report_flows.js` +
  `app/reporting.py` — report-detail status styling + key-factor highlights
  (E4).
- `app/static/app.css` — the single shared status palette / emphasis tokens
  (E3 + E4).
- `app/static/03_folder_actions.js`, `04_run_create.js`, `05_report_flows.js`
  (the three create flows) + `app/static/02_sidebar.js` +
  `app/static/01_tree.js` — auto-refresh of the relevant tree after create
  (E5).

## Depends on

- `10-feature-test-run` — the run editor, `run_editor.html`, and the
  `RUN_RESULTS` vocabulary (E1–E3).
- `12-feature-quality-report` — report detail views and the existing
  `case_trend` status colouring this batch extends consistently (E4).
- `06-tree-pane` + `03-watcher-and-sse` — the `sse:change` → tree re-GET
  contract that E5 relies on.
- `11-feature-testcase-component` — the `kind` factor highlighted in
  report detail (E4).
- `01-tech-restructure` — the `NN_*.js` global-script layout these
  touchpoints now live in.

## Surface for follow-up

- A single shared status palette becomes reusable design tokens for any
  future status-bearing surface (dashboards, badges, filters).
- Folder grouping in the run editor (E2) is a step toward a tree-style
  case picker / nested run views.
- E5 may generalise the "create → `sse:change` → tree refresh" contract
  into a documented client-side convention, removing per-flow special
  cases.
