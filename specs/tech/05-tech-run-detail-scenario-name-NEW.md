# 05 · Test-run detail — scenario-name column + remark resize

_Status: **Shipped Jun 13, 2026** (decisions RD-1b + RD-2a). Small,
self-contained enhancement to the run editor (`feature-10`). See the
as-built summary at the foot of this file and `DONE.md`._

## Scope

The main-pane run editor only: `app/templates/run_editor.html` and its
server context builder `ui_run` (`app/server/routes_ui.py:215-248`). Two
asks:

1. Add a **Scenario name** column → table becomes
   `Test case | Scenario name | Result | Remark | ×`.
2. **Remark** column: reduce width; auto-resize height for multi-line
   content up to **2 lines**, then scrollable.

Out of scope: anything that writes scenario name into the run YAML — it is
**display-only**, read live from each `.feature` (consistent with
feature-12 D6 "enums/tags are read live, never snapshotted").

## Depends on

- **tech-04 migration** (scenario name populated on existing files);
  otherwise the new column is mostly blank for legacy runs.

## Current state (grounded)

- Table header `Test case | Result | Remark | (×)`
  (`run_editor.html:78-84`); rows keyed by `r.file_path`, with `r.result`,
  `r.remark`, `r.missing` (`:114-141`).
- Folder-group heading spans the table: `colspan="4"`
  (`run_editor.html:102`, and the clone template `:186`).
- Remark cell: `<textarea class="run-remark … resize-y" rows="1">`
  (`:134`, and the add-row template `:171`).
- Server enrichment loop already annotates each result with `missing`
  (`routes_ui.py:239-240`) — the natural seam to also attach
  `scenario_name`.
- Dirty tracking snapshots `{name, description, results:[{file_path,
  result, remark}]}` from the **live DOM** (feature-10 spec § "Dirty
  tracking"); `tmsRunEditor` clones `run-result-row-template` for
  `+ Add test case` and reads `data-file-path` per row.

## Proposed approach

### A. Server: attach `scenario_name` per result (display-only)

- In `ui_run`, extend the existing `for r in run_dict["results"]` loop:
  read the case via `read_feature` best-effort; set
  `r["scenario_name"] = feature.scenario.name` on success, `""` on
  `FileNotFoundError` / `GherkinParseError` / missing. (Mirrors the
  tolerant pattern in `_listing.py:246-256`.)

### B. Template: new column + colspan bump

- Add `<th>Scenario name</th>` after Test case; rebalance widths (e.g.
  Test case `w-1/4`, Result `w-40`, Remark narrower).
- Render `r.scenario_name` as a **plain `<td>` text** (truncate +
  `title`), NOT an input — so the DOM dirty-snapshot never picks it up.
- **Bump the folder-group heading `colspan="4"` → `5`** in both the
  server row (`:102`) and the clone template (`:186`).

### C. Remark resize

- `run-remark` textarea: give it a fixed ~1.5-line height (`h-10`) +
  `overflow-y-auto`; reduce the cell/column width. CSS-only — no auto-grow
  JS. A *fixed* height (not just `max-height`) is what makes a 2nd line
  peek through the clip, cueing the user there's more to scroll; with the
  original `rows="1"` + `max-height` the box silently stayed one line.

## Decisions (resolved Jun 13, 2026)

- **RD-1 — Newly-added rows' scenario name → (b) fetch on add.** A
  freshly-cloned row asynchronously fetches its scenario name from the
  **existing** `GET /api/files/<path>` (which returns `feature.to_dict()`,
  including `scenario.name`) and fills the display-only cell once resolved.
  No new endpoint, and crucially **no per-feature parsing was added to
  `list_tree`** (the sidebar SSE hot path). On any fetch failure the cell
  stays blank (folds into RD-4).
- **RD-2 — Remark resize → (a) CSS-only.** No auto-grow JS. Final form is a
  fixed ~1.5-line height (`h-10`) + `overflow-y-auto` so a clipped 2nd line
  cues "there's more" (per the USER's follow-up); column narrowed (`w-1/4`).

## Assumptions / blindspots

- **RD-3 (firm).** Scenario name must stay out of the dirty snapshot and
  the PATCH payload — render it as non-input text. Verified the snapshot /
  comparator projection is exactly `{file_path, result, remark}`
  (`F10_12_get_run_shape.py:42-48`, `F10_69_editor_banner_branches.py`),
  and the JSON API explicitly must not leak UI-only fields (`F10_12:47-48`).
- **RD-4.** Tombstoned (`r.missing`) / unreadable cases → blank scenario
  name.
- **RD-5 (test impact).** Verify/re-pin `F10_29_tombstone_render.py` (its
  `<tr data-file-path=…>` row regex + the `run-remark` textarea capture
  must still match with the extra `<td>`), and any smoke asserting the
  group-head `colspan="4"` (now `5`) or the add-row/clone template shape
  (`F10_28_editor_addcase_remove_wiring.py` covers the delegation wiring).
- **RD-6.** Per-row `read_feature` adds I/O on render; runs are capped
  small in practice and this mirrors the report engine's live reads.

## As-built (shipped Jun 13, 2026)

- **DO-1 — server.** `ui_run` (`app/server/routes_ui.py`) extends the
  per-result loop: tombstoned cases get `scenario_name = ""`; otherwise it
  reads the case live via `read_feature(...).scenario.name`, catching
  `(GherkinParseError, OSError, UnicodeDecodeError)` → `""` (RD-4). Imports
  `GherkinParseError` from `..errors`.
- **DO-2 — template** (`app/templates/run_editor.html`). New
  `<th>Scenario name</th>`; widths rebalanced (Test case `w-1/4`, Result
  `w-40`, Remark `w-1/4`). Each result row gains a plain
  `<td class="run-scenario-name … truncate" title=…>` (no input). Folder-
  group `colspan` 4→5 in both the server row and the
  `run-group-head-template` clone. Remark textarea is `h-10`
  (~1.5 lines) + `overflow-y-auto` (live row + `run-result-row-template`).
- **DO-1b — JS** (`app/static/06_run_editor.js`). `_createResultRow` calls
  the new `_fillScenarioName(cell, file_path)`, which GETs
  `/api/files/<path>`, reads `data.scenario.name`, and fills the cell;
  errors leave it blank. `_readCurrent` is unchanged, so the display-only
  cell never enters dirty tracking.
- **CHECK.** New `tech-05/` smokes `T05_01`..`T05_04` (+`COVERAGE.md`). No
  feature-10 smoke needed re-pinning — the extra `<td>` / colspan bump
  broke no existing regex. Full suite **279/279 PASS** (was 275).
- **ACT.** `DONE.md` entry added; backlog item cleared from
  `IN-PROGRESS.md`; this spec marked shipped.
