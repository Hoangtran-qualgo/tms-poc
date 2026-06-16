# 09 · Scenario Outline in test runs — per-example run items

_Status: **Shipped Jun 16, 2026** (decisions D1–D7 + DQ1; DO-1..DO-6). See
the as-built summary at the foot of this file and `DONE.md`._

## Scope

Represent **Scenario Outline example rows** as distinct run items in a test
run, for both entry paths:

1. **Import test run** (Allure HTML, feature-15): the report renders one
   outline as N leaves `"<base> -- @<n>.<m> "`. Keep the suffix; create **one
   `RunResult` per example row**, all pointing at the single outline case.
2. **Manually add an outline case to a run** (run editor, feature-10): adding
   an outline case expands into **N items** (one per Examples data row).

Display (run editor): the `file_path` link still navigates to the case detail;
the scenario-name cell shows the base scenario name plus the matched Examples
header + data row, e.g.

```
user can access admin page
| username | pwd |
| admin1 | pwdad1 |
```

**Out of scope:** import **test case** of an outline — already correct (1 file,
`Examples` preserved as import source; `split_feature_source` splits per
scenario, not per example row). No change there.

## Depends on / builds on

- **feature-15** (import test run): parser `app/allure_io.py`, resolver
  `Storage.resolve_scenarios`, route `app/server/routes_runs.py`, UI
  `app/static/04_run_create.js`.
- **tech-05** (run-detail scenario name): display-only **live** read of
  scenario name in `ui_run` + `run_editor.html` + `06_run_editor.js`
  `_fillScenarioName`. The Examples-row display reuses this live-read seam.

## Current state (grounded by `.smoke-scratch/_investigate/outline-import/`)

- **Parser** keeps the full Allure leaf name; example rows have distinct
  case-folded keys, so they stay 2 scenarios (no retry-collapse). [repro `01`]
- **Real suffix format** (sample report): `"...count -- @1.1 "` and
  `"...count -- @1.2 "` — note the **trailing space**. `n` = Examples-table
  index (1-based), `m` = data-row index (1-based). Trim must be
  whitespace-tolerant. [repro `04`]
- **Resolver** (`_search.py:171-220`) matches by exact case-folded
  `feature.scenario.name`, so suffixed names resolve **unmatched** → all-or-
  nothing abort. The trimmed base matches the single case. [repro `02`]
- **Run model** (`_run.py`): `RunResult` is `{file_path, result, remark}`;
  `validate_run` rejects duplicate `file_path` (uniqueness `seen` set at
  `:120-135`). Two example rows → same path → rejected; no per-example
  identity exists. [repro `03`]

## Locked decisions

- **D1 — identity shape: structured `{table, row}` ints** (1-based) on
  `RunResult.example`; `None` for non-outline. Parsed from ` -- @<n>.<m>`
  (whitespace-tolerant); base name = text before the token, rstripped.
- **D2 — uniqueness key** becomes `(file_path, example)`. Two `None`-example
  results on the same path are still a duplicate (rejected); two different
  `{table,row}` on the same path are allowed.
- **D3 — display-only, read live.** The Examples header/data rows are NOT
  snapshotted into the run YAML (consistent with tech-05 / feature-12 D6). The
  run YAML/API carries only `example: {table, row}`; the editor maps it to the
  live feature's Examples for rendering. Tolerant-blank when the case changed,
  the row is out of range, or the case is not an outline.
- **D4 — import:** each report row trims to base, resolves to one case, and
  attaches its `{table,row}`. Repeated base names (the outline's rows) are
  **distinct items**, NOT "ambiguous" (ambiguous = 2+ *different* cases).
- **D5 — manual add:** picking an outline case expands into N items, one per
  Examples data row, each tagged `{table,row}`.
- **D6 — single Examples block only (Jun 16).** This version supports outlines
  with **one** `Examples:` block. `{table,row}` is parsed/stored generically,
  but only `table == 1` is tested/guaranteed; a `@n.m` with `n>1` maps
  best-effort and falls into the D3 tolerant-blank path. No multi-block fixture.
- **D7 — removed-case tombstone is per-example (Jun 16; resolves BS-A/A3).**
  When the underlying `.feature` is removed, **every** per-example run item on
  that path tombstones (strikethrough filename + a "file has been removed" line)
  via the existing `ui_run` `missing` mechanism (`routes_ui.py:240-243`); the
  user keeps or removes each invalid item. (Distinct from D3's dangling-row
  case, where the file still exists — that stays a silent blank, A2 approved.)

## Detailed plan (DO steps)

### DO-1 — suffix parser helper (`app/allure_io.py`)

- Add a pure helper, e.g. `split_example_suffix(name) -> (base, example|None)`:
  - regex ` -- @(\d+)\.(\d+)\s*$` (whitespace-tolerant, trailing space seen in
    the sample); on match return `(name[:match.start()].rstrip(), {"table":n,
    "row":m})`; else `(name.strip(), None)`.
- Decide where it is applied: **at the resolver/route boundary** (DO-3), not in
  `parse_allure_report` — the parser should keep reporting raw leaf names so
  retry-collapse and other logic stay unchanged. Export the helper for reuse.
- **D6:** parse `{table,row}` generically (the regex already captures `n`); only
  single-block (`table == 1`) is tested. No special-casing of `n>1` — it just
  flows to the D3 tolerant-blank mapping if the block is absent.
- **Verify:** smoke — `"a -- @1.2 "` → `("a", {table:1,row:2})`; `"a -- @10.3"`
  → `("a", {10,3})`; `"plain name"` → `("plain name", None)`; non-suffix `@`
  text untouched.

### DO-2 — `RunResult.example` + uniqueness (`app/models/_run.py`)

- Add field `example: dict | None = None` to `RunResult` (`:27-29`). Extend
  `to_dict` (`:31-36`) to include `"example": self.example` **only when not
  None** (keep legacy YAML/API shape for plain results — avoids churn in
  existing runs and feature-10/tech-05 smokes). `from_dict` (`:38-44`) reads
  `payload.get("example")` (validate it's `{table:int,row:int}` or None).
- Change the uniqueness check (`:120-135`): key the `seen` set on
  `(r.file_path, _example_key(r.example))` where `_example_key` is e.g.
  `None` or `(table, row)`. Update the duplicate message to mention the example
  when present.
- **Verify:** smoke — two results same path + different `{table,row}` pass;
  same path + same example (or both None) rejected; `to_dict` omits `example`
  when None and includes it otherwise; round-trip `from_dict(to_dict())`.

### DO-3 — import resolver/route (`_search.py` + `routes_runs.py`)

- Keep `resolve_scenarios` matching **base** names (no signature change).
- In the import route (`routes_runs.py` preview + commit helpers):
  1. For each report scenario, `split_example_suffix(name)` → `(base, example)`.
  2. Resolve the **set of distinct base names** via `resolve_scenarios`.
  3. Re-expand per report row: build a `RunResult(file_path=matched[base],
     result=…, remark=…, example=example)`; rows whose base is unmatched/
     ambiguous keep producing the existing blocking error lines (keyed on the
     **original suffixed** name so the user sees what failed).
  4. Repeated base names (outline rows) are expected and must NOT be treated as
     ambiguous (D4); only 2+ *different* cases for one base is ambiguous.
- Preview payload: include `example` per row so the UI can show it.
- **Review fixes (Jun 16, grounded against `routes_runs.py:44-61,155-232`):**
  - `_classify_scenario` matches `name in resolution["matched"]` — classify
    **per row on the trimmed base name**, but keep the **suffixed** name for
    the `_import_error_line` text.
  - Preview `counts` use `len(resolution["matched"|...])`; `resolve_scenarios`
    keys `matched` **by name**, so the outline's rows collapse to one entry.
    Recompute counts + the per-row tally **per report row**, not from the
    resolution-dict lengths.
  - Commit builds `RunResult(file_path, result=sc.result)` — Allure carries
    **no remark**; do not set one.
- **Verify:** smoke — sample report (`@1.1`/`@1.2`) imports to 2 results on the
  one `count.feature` path with `{1,1}`/`{1,2}`; mixed outline + plain rows;
  unmatched suffixed row still aborts all-or-nothing with a readable name.

### DO-4 — run editor display (`routes_ui.py` + `run_editor.html` + `06_run_editor.js`)

- `ui_run` per-result loop (the tech-05 seam): when `r["example"]` is set, read
  the case live and resolve `feature.scenario.examples[table-1]` → header +
  `rows[row-1]`; attach `r["example_header"]` / `r["example_row"]` (display-
  only). Tolerant-blank on parse error / index out of range / not an outline.
- `run_editor.html`: in the scenario-name cell, render base name then (if
  present) the header + matched data row as small monospace lines (the
  `| a | b |` form). Keep it a plain `<td>` (never an input → stays out of the
  dirty snapshot, per tech-05 RD-3). The cell must drop `truncate` and allow
  the multi-line block (BS-D).
- **Three display states (D3 + D7):**
  - **live + example present** → base name + matched header/data row.
  - **case removed (`r.missing`)** → strike the filename (Test-case column,
    as today) and render a **"file has been removed"** sub-line **under the
    filename** in the Test-case column (DQ1=b). **Remove** the old remark-column
    `run-remark-override` ("test case was removed", `run_editor.html:137`) —
    this is a **global tombstone change for all runs**. Scenario-name cell is
    blank when missing.
  - **case exists but row out of range / not outline** → base name only,
    blank example (A2 approved silent blank).
- `06_run_editor.js` `_fillScenarioName`: when a row carries an example, also
  fetch/render the matched Examples row (`GET /api/files/<path>` already returns
  `feature.to_dict()` incl. examples).
- **Verify:** smoke — `{1,2}` renders base + 2nd data row; removed case →
  "file has been removed" + struck filename; out-of-range / non-outline → base
  only (blank example); cell is not an input.

### DO-5 — manual add-to-run expansion (`06_run_editor.js`)

- When the user adds an outline case (case has ≥1 Examples row), expand into N
  rows, each cloned from `run-result-row-template` with `data-example` set to
  `{table,row}`; non-outline cases add one row as today.
- `_readCurrent` / dirty snapshot must include `example` so the PATCH payload
  carries it (mirror the `{file_path, result, remark}` projection + `example`).
- **Review fixes (Jun 16, grounded against `06_run_editor.js:58-92,252-302`):**
  - `_readCurrent` reads `tr.dataset.filePath` only — add `data-example`.
  - `_compareJson` **sorts results by `file_path` alone**; extend the sort key
    to `(file_path, example)` or same-path rows break order-insensitive dirty.
  - **BS-F (normalize `example` representation).** Baseline/live come from
    `_readCurrent` (DOM `data-example`), but `onExternalChange` builds the
    disk projection from the **API** (`rr.example`, an object). All three must
    serialize `example` identically (same keys/order, ints not strings) or the
    editor will false-flag dirty / external-change. Store it on the row as a
    simple scalar (e.g. `data-example="<table>.<row>"` or two int attrs) and
    normalize to one canonical `{table,row}` shape before stringify.
  - `_onAddCaseClicked` builds `existing` as a Set of **file_paths** and the
    picker excludes them + returns **feature paths** (not rows). Expansion must
    fetch each selected feature, detect `kind==="outline"`, read
    `examples[0].rows` (D6: single block), and create N rows.
  - **A4 (apply current logic):** keep the exclude-by-path rule and the
    folder-grouping/order logic unchanged. Adding an outline expands to all N
    rows at once; once present, the path is excluded from further adds (no
    per-row re-add in this version). New rows land in their folder group as
    today.
- **Verify:** smoke — adding an outline case yields N rows with distinct
  `{table,row}`; saving round-trips through the API; non-outline unaffected.

### DO-6 — end-to-end + UI (`04_run_create.js` import preview)

- Import-run preview table shows the example identity / matched row; commit
  writes the per-example results; open the imported run and confirm the editor
  renders the Examples rows.
- **Verify:** API+UI smoke against `specs/sample-data/allure-report-single/`
  (the `@1.1`/`@1.2` outline) end-to-end.

## Risks / re-pin notes

- **R1 — legacy YAML/API shape.** `example` must be **omitted when None** so
  existing runs and feature-10 / tech-05 / feature-12 smokes that assert the
  exact `{file_path, result, remark}` projection don't break. Re-pin any smoke
  that snapshots `RunResult` shape if it now must tolerate an optional key.
- **R2 — dirty tracking.** Adding `example` to the DOM snapshot (DO-5) must not
  make existing plain rows flip dirty; non-outline rows carry no `data-example`
  and project to the same shape as today.
- **R3 — Examples model shape. RESOLVED (Jun 16).** `ExamplesTable` =
  `{tags, name, header: list[str], rows: list[list[str]]}` (`_feature.py:77-105`);
  `{table,row}` → `examples[table-1].rows[row-1]` + `examples[table-1].header`.
  Multi-block (`@n.m`, n>1) ordering is the index order of `scenario.examples`.
- **R4 — whitespace.** The sample's trailing space proves names need
  `.rstrip()` after suffix removal and `\s*$` in the regex. **Pre-existing
  risk:** the parser does NOT strip leaf names, so a trailing space on a
  *plain* scenario name would already silently fail `resolve_scenarios`'
  exact casefold match — consider stripping all report names.

## Review findings (Jun 16, 2026) — blindspots + unresolved

Grounded against the live code/smokes. The save path is the key enabler:
**the run editor saves via a full-run PATCH** (`06_run_editor.js.save()` →
`PATCH /api/runs/...` → `TestRun.from_dict` → `write_run`), so per-example
identity round-trips through the model — the editor does NOT use the per-case
endpoints.

Blindspots (folded into DO scope):

- **BS-A — per-case endpoints are path-keyed. RESOLVED as a known limitation
  (D7/A3).** `add_run_case` / `remove_run_case` / `update_run_result`
  (`_runs.py:382-491`) match `r.file_path == case_path` and are **not made
  example-aware** this version. The **editor full-PATCH is the only supported
  edit path** for outline runs (per-row × removal works because it is DOM-row,
  not path, based). The REST endpoints stay path-keyed; document that calling
  them on a per-example run is undefined-but-existing behaviour.
- **BS-B — editor identity is `file_path`-only** (DO-5 covers; see fixes).
- **BS-C — add-case picker excludes by path + picks features** (DO-5 fixes; A4).
- **BS-D — scenario-name cell is single-line `truncate`, `w-1/4`**
  (`run_editor.html:128`, template `:168`). Drop `truncate`, allow the
  multi-line block; keep it a non-input cell (tech-05 RD-3). DO-4 covers.
- **BS-E — preview counts collapse duplicate base names** (DO-3 fixes).
- **BS-F — `example` must serialize identically across DOM-read, API-read, and
  PATCH** or dirty/external-change flaps (DO-5 fix above).
- **D7 visual consequence (accept).** When a removed outline case tombstones,
  all N rows show the *same* struck filename + "removed" line and the example
  detail is unreadable (file gone) — the rows are visually indistinguishable.
  Accepted: the user keeps/removes them as a group or individually.

Decisions locked (Jun 16) — formerly unresolved:

- **A1 — multi-block NOT supported (→ D6).** Single `Examples:` block only;
  `{table,row}` parsed generically, only `table==1` tested. No multi-block
  fixture needed.
- **A2 — dangling example = silent blank. APPROVED.** Case exists but the row
  index is out of range → base name only, no example, no tombstone. (Consequence
  to accept: an over-shot `@1.<m>` import silently shows no example row.)
- **A3 / BS-A — full-PATCH only (→ D7).** See BS-A above.
- **A4 — apply current add/grouping logic, no change.** Outline expands to all
  N rows at once; exclude-by-path + folder-grouping/order unchanged.

Resolved sub-decision:

- **DQ1 — removed-case cue → MOVE (option b, Jun 16).** Show a **"file has
  been removed"** sub-line under the filename in the Test-case column and
  **remove** the remark-column `run-remark-override` (`run_editor.html:137`).
  This changes the tombstone for **all** runs (not just outline), so the
  remark-column override smokes must be updated, not just re-verified.

Smoke re-pin impact (refines R1):

- **Update:** `F10_43_validate_duplicate_filepath` (key → `(file_path,
  example)`), `tech-05/T05_02` (snapshot projection gains `example`).
- **Update (DQ1 global tombstone):** `F10_29_tombstone_render`,
  `F10_33_tombstone_strikes_filename`, `F10_75_tombstone_endtoend` — assert the
  new under-filename "file has been removed" line and the **absence** of the
  remark-column override.
- **Tolerate optional `example`:** `F10_12_get_run_shape`,
  `F10_47_schema_keys_block_scalar`, `F10_56_list_runs_shape`.
- **Re-verify regex:** `F10_16/31` (row/template gains `data-example` +
  multi-line cell).

## Test plan (smokes)

- New `tech-09/` smokes T09_01..T09_06 mapped 1:1 to DO-1..DO-6 (+`COVERAGE.md`).
- Investigation repros live in `.smoke-scratch/_investigate/outline-import/`
  (01 parser, 02 resolver, 03 run-model, 04 sample-suffix) — run individually
  with `PYTHONPATH=. .venv/bin/python <file>`; not auto-discovered by `run.py`.

## As-built (shipped Jun 16, 2026)

- **DO-1 — suffix parser.** `split_example_suffix(name)` (`app/allure_io.py`,
  `_EXAMPLE_SUFFIX_RE = r"\s+--\s+@(\d+)\.(\d+)\s*$"`) returns
  `(base, {"table", "row"})` with 1-based ints when the canonical suffix is
  anchored at the end, else `(name.strip(), None)`. Base is fully stripped
  (both ends). Applied at the route boundary (DO-3), not in
  `parse_allure_report`.
- **DO-2 — `RunResult.example` + uniqueness.** `RunResult`
  (`app/models/_run.py`) gains `example: dict | None = None`; `to_dict` emits
  `example` **only when not None** (legacy `{file_path, result, remark}` shape
  preserved); `from_dict` coerces via `_coerce_example` (`{table:int,row:int}`
  or None). `validate_run` keys the `seen` set on
  `(r.file_path, _example_key(r.example))` and names the example in the
  duplicate message.
- **DO-3 — import route.** `_classify_report` (`app/server/routes_runs.py`),
  shared by preview + commit: `split_example_suffix` per scenario → resolve the
  **distinct base names** via `resolve_scenarios` (unchanged) → re-attach each
  row's `example`. Counts tally **per report row** (not `len(resolution[...])`);
  an outline's repeated base stays distinct and is never flagged ambiguous;
  error lines keep the **suffixed** name. Commit builds
  `RunResult(file_path, result=sc.result, example=…)` — no remark.
- **DO-4 — editor display.** `ui_run` + `_resolve_example`
  (`app/server/routes_ui.py`) attach `example_header` / `example_row` from the
  **live** feature (tolerant-blank on parse error / out-of-range / not an
  outline). `run_editor.html`: result row gains `data-example="<t>.<r>"`; the
  scenario cell drops `truncate` and appends a monospace Examples block. **DQ1
  (global):** removed-case cue is now a `run-removed-note` "file has been
  removed" sub-line under the filename; the remark-column `run-remark-override`
  was removed for all runs.
- **DO-5 — manual add.** `06_run_editor.js`: `_expandCasePaths` fetches each
  picked feature and emits one row per `examples[0].rows` entry for outlines
  (else one row); `_createResultRow(file_path, example=null)` stamps
  `data-example`; `_readCurrent` carries `example`; `_compareJson` rebuilds
  results in canonical key order + sorts on `_sortKey` `(file_path, example)` so
  same-path rows never false-flag dirty. The full-run PATCH round-trips
  `example` through `TestRun.from_dict` + `validate_run` (no server change).
- **DO-6 — end-to-end.** `tech-09/T09_06` drives DO-1→DO-5 against the real
  bundled report (`specs/sample-data/allure-report-single/`, the `@1.1`/`@1.2`
  outline): preview 9/9 matched + per-row counts, commit writes 2 same-path
  example results + 7 plain (sample `created_at` preserved), editor renders the
  Examples rows. Pure verification — no app code changed.
- **Import-modal width (USER follow-up).** `tmsOpenModal`
  (`app/static/03_folder_actions.js`) gained a `2xl` (`max-w-6xl`) size; the
  Import-test-cases modal switched to it and now shows up to **50 chars** of a
  scenario name on one (`whitespace-nowrap`) line. Re-pinned `F14_04`.
- **CHECK.** New `tech-09/T09_01..T09_06` (+`COVERAGE.md`); re-pinned `F10_29`,
  `F10_32`, `F10_75` (DQ1 / `_createResultRow` signature), `T05_04`
  (`_createResultRow` signature), and `F14_04` (modal width / 50-char name).
  Full suite **301/301 PASS** (was 295 at DO start).
- **ACT.** `DONE.md` entry added; the Scenario-Outline backlog item cleared
  from `IN-PROGRESS.md` (the project-level scenario-name uniqueness item stays
  open); this spec marked shipped.
