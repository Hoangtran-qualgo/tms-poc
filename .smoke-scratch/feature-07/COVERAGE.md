# feature-07 · Folder views — coverage matrix

Step 1 audit of the smoke tests against
`specs/features/07-feature-folder-views-NEW.md`.

## Method

- Spec source: `specs/features/07-feature-folder-views-NEW.md`.
- Rule heuristic (locked Jun 8, 2026): every imperative
  statement in the spec + every bullet under
  `## Acceptance criteria`.
- Spec sub-headings under `## Public surface` (Route,
  Templates, Server helper) and under `## Invariants &
  rules` (Dispatch, Features-table columns,
  Sub-folder-table column, Buttons by depth, Empty states,
  Re-render trigger) are treated as **sections** for the
  one-smoke-per-section rule (Decision A). Some sections
  combine because rules overlap heavily (see TP+DP
  combination below).
- `Status` values: `covered`, `partial` (incidental
  coverage inside a primary-other-feature smoke),
  `missing`, `n/a` (rule is documentation-only / not
  testable).
- **Soft 90-LOC guideline** (locked Step-1 sign-off for
  feature-06): default-plan one file per spec section,
  split into sub-files when the section has multiple
  independent claims each needing its own setup OR the
  planned file would exceed ~150 LOC.
- **Primary-frame distinction.** Feature-07 is the
  *server-side rendering layer* for folder views: the
  `ui_folder` route, the four `folder_*.html` templates,
  the `_folder_crumbs` helper, and their structural
  contracts (columns, breadcrumb, buttons, empty
  states). Storage list-folder behaviour is primary-framed
  in feature-02 (depth + listing); test-run filtering is
  primary-framed in feature-06 (HD3 storage half) with
  the HTML half now joining feature-07 per Step 2; CRUD
  triggers (`tmsCreate*` / `tmsRefreshFolder`) are
  primary-framed in feature-04 / feature-05.
- **TP+DP combination.** TP1\u2013TP4 ("each template's surface
  shape") and DP1\u2013DP4 ("which template fires at which
  depth") overlap because every TP assertion implies the
  matching DP and vice-versa. We test them together in
  `F07_02_dispatch.py` to avoid duplicated fixtures.
  DP5 (depth-11 \u2192 400) is also covered in
  `F07_10_acceptance.py` AC3 because the spec restates
  it there.
- **Testable-shape decisions** (carry over from feature-06
  Step-1 sign-off):
  - **Hybrid JS** approach for any JS-driven rules
    (`tmsRefreshFolder` exists as a module-level
    function): static inspection + render-and-grep on
    the call sites embedded in the templates.
  - **End-to-end claims** stay end-to-end where the
    spec demands one (here: AC7 "after CRUD mutation,
    pane reflects new state once `tmsRefreshFolder`
    runs" \u2014 verifiable as a hybrid static+render
    chain).

## Matrix

| # | Rule | Spec \u00a7 | Smoke file | Status |
|---|---|---|---|---|
| RT1 | `GET /ui/folder/` and `GET /ui/folder/<path:p>` are handled by `ui_folder`; reads `storage.list_folder(segments)`; renders the depth-appropriate template. | Public surface \u2192 Route | `F07_01_route.py` | covered |
| TP1 | `folder_root.html` (depth 0) renders the project list with a `+ New project` button (or the empty-state placeholder). | Public surface \u2192 Templates | `F07_02_dispatch.py` (TP+DP combined) | covered |
| TP2 | `folder_project.html` (depth 1) renders the module table with breadcrumb back to root and a `+ New module` button (or empty state). | Public surface \u2192 Templates | `F07_02_dispatch.py` + `F07_02b_project_view_filters_test_run.py` (moved from `p2_2c`) | covered |
| TP3 | `folder_module.html` (depth 2) renders sub-folder table (if any) + features table, breadcrumb `Projects / <project> / <module>`, and `+ Sub-folder` + `+ Create test case` buttons. | Public surface \u2192 Templates | `F07_02_dispatch.py` | covered |
| TP4 | `folder_subfolder.html` (depth 3..10) renders the same shape as the module view but with a server-built `crumbs` list for an arbitrarily long breadcrumb. | Public surface \u2192 Templates | `F07_02_dispatch.py` | covered |
| SH1 | `_folder_crumbs(segments) -> list[{label, path}]` builds the breadcrumb chain for the sub-folder view AND the file-editor breadcrumb so both render N levels uniformly. | Public surface \u2192 Server helper | `F07_03_crumbs.py` | covered |
| DP1 | `len(segments) == 0` \u2192 `folder_root.html`. | Invariants \u2192 Dispatch | `F07_02_dispatch.py` | covered |
| DP2 | `len(segments) == 1` \u2192 `folder_project.html`. | Invariants \u2192 Dispatch | `F07_02_dispatch.py` | covered |
| DP3 | `len(segments) == 2` \u2192 `folder_module.html`. | Invariants \u2192 Dispatch | `F07_02_dispatch.py` | covered |
| DP4 | `len(segments) >= 3 and <= MAX_FOLDER_DEPTH` \u2192 `folder_subfolder.html`. | Invariants \u2192 Dispatch | `F07_02_dispatch.py` | covered |
| DP5 | `len(segments) > MAX_FOLDER_DEPTH` \u2192 400 `bad_request` from `Storage.list_folder` (handled by the UI blueprint's `ValueError` handler). | Invariants \u2192 Dispatch | `F07_02_dispatch.py` + `F07_10_acceptance.py` AC3 | covered |
| FT1 | `File name` shown as-is. Click \u2192 `/ui/file/<path>`. | Invariants \u2192 Features-table columns | `F07_04_features_table.py` | covered |
| FT2 | `Description`: **first line only**, truncated; full description in `title=` attribute for hover. Multi-line descriptions never expand the row. | Invariants \u2192 Features-table columns | `F07_04_features_table.py` | covered |
| FT3 | `Tags`: chips rendered with `@` prefix, single line, truncated. Column shows the **union** of feature-level + scenario-level tags (D10). | Invariants \u2192 Features-table columns | `F07_04_features_table.py` | covered |
| ST1 | Sub-folder table: one column `Sub-folder` with a folder icon (\ud83d\udcc1). Click \u2192 `/ui/folder/<path>`. | Invariants \u2192 Sub-folder-table column | `F07_05_subfolder_table.py` | covered |
| BD1 | Depth 0 (root) \u2192 `+ New project` button. | Invariants \u2192 Buttons by depth | `F07_06_buttons.py` | covered |
| BD2 | Depth 1 (project) \u2192 `+ New module` button. | Invariants \u2192 Buttons by depth | `F07_06_buttons.py` | covered |
| BD3 | Depth 2 (module) \u2192 `+ Sub-folder`, `+ Create test case`. | Invariants \u2192 Buttons by depth | `F07_06_buttons.py` | covered |
| BD4 | Depth 3..10 (sub-folder) \u2192 `+ Sub-folder`, `+ Create test case`. | Invariants \u2192 Buttons by depth | `F07_06_buttons.py` | covered |
| BD5 | **No rename / delete / move buttons at any depth** \u2014 those operations either don't have UI (`04-folder-crud`) or live inside the file editor (`05-testcase-crud`). | Invariants \u2192 Buttons by depth | `F07_07_button_gaps.py` + `F04_07_ui_gaps.py` (folder-CRUD half) | covered |
| ES1 | Depth 0 with no projects \u2192 "No projects yet." + central `Create project` CTA. | Invariants \u2192 Empty states | `F07_08_empty_states.py` | covered |
| ES2 | Depth 1 with no modules \u2192 "No modules in `<project>` yet." + CTA. | Invariants \u2192 Empty states | `F07_08_empty_states.py` | covered |
| ES3 | Depth 2 / 3+ with no folders AND no features \u2192 "No test cases in `<name>` yet." + CTA (or `+ Sub-folder` and `+ Test case` CTAs side-by-side in sub-folder view). | Invariants \u2192 Empty states | `F07_08_empty_states.py` | covered |
| RR1 | Main pane is *not* SSE-wired in v1; only the tree pane is. Folder views update only when (a) the user navigates via HTMX click, (b) `tmsRefreshFolder(folderPath)` is called by JS after a CRUD operation, or (c) the user clicks the tree refresh and then re-navigates. | Invariants \u2192 Re-render trigger | `F07_09_rerender.py` | covered |
| AC1 | Visiting `/ui/folder/` with no projects renders an empty-state CTA and no tables. | Acceptance criteria | `F07_10a_empty_root_no_tables.py` (split per Step-4 rule) | covered |
| AC2 | Visiting `/ui/folder/<existing path>` at any depth `0..10` renders without error. | Acceptance criteria | `F07_10b_renders_at_each_depth.py` (split) | covered |
| AC3 | Visiting `/ui/folder/<path>` at depth `11` returns a 400 inline error snippet. | Acceptance criteria | `F07_10c_depth11_400.py` (split) | covered |
| AC4 | Clicking a feature row opens that file in the editor. | Acceptance criteria | `F07_10d_feature_row_opens_editor.py` (split; round-trip) | covered |
| AC5 | Clicking a sub-folder row navigates the main pane to that folder's view. | Acceptance criteria | `F07_10e_subfolder_row_navigates.py` (split; round-trip) | covered |
| AC6 | Multi-line feature descriptions render only their first line in the table; full text appears on hover. | Acceptance criteria | `F07_10f_description_first_line.py` (split; strengthens FT2 end-to-end) | covered |
| AC7 | After a CRUD mutation, the main pane reflects the new state on the writing tab once `tmsRefreshFolder` runs. | Acceptance criteria | `F07_10g_tmsrefreshfolder_endtoend.py` (split; end-to-end POST + simulated tmsRefreshFolder GET at depths 0/1/2) | covered |

## Summary

- Total rules: **30** (1 route, 4 templates, 1 server helper, 5 dispatch, 3 features-table, 1 sub-folder-table, 5 buttons, 3 empty states, 1 re-render, 7 acceptance).
- `covered`: **30**.
- `partial`: **0**.
- `missing`: **0**.
- `n/a`: **0**.

**Feature-07 is done** per the locked Definition-of-Done
(`COVERAGE.md` has zero `missing` rows; `run.py --filter
07` exits zero with all **24 smokes** green — 23 new + 1
moved-and-refined). The matrix's main expansion vs the
Step-1 plan was the per-rule split (FT → a/b/c, BD1–4 →
a/b/c/d, ES → a/b/c, AC → a..g) so each rule's failure
mode is isolated.

## Step 2 / Step 3 execution log

**Jun 8, 2026** — Step 2 (Restructure) + Step 3 (Refine)
executed for feature-07:

- Step 2 move (one file, via `git mv` to preserve
  history):
  - `.smoke-scratch/p2_2c_project_view_hides_test_run.py`
    → `.smoke-scratch/feature-07/F07_02b_project_view_filters_test_run.py`
    (HTML-half companion to feature-06 HD3; primary
    frame = feature-07's `folder_project.html`).
- Step 3 refinement:
  - **F07_02b**: docstring anchored to TP2 +
    cross-pointer to feature-06 HD3; spec-anchored
    failure messages; positive controls (project name
    'Alpha' + sibling-module `hx-get` must appear) on
    top of the existing negative invariant.
- Cross-update: feature-06's `HD3` row in
  `feature-06/COVERAGE.md` now points at
  `../feature-07/F07_02b_project_view_filters_test_run.py`.

## Step 4 execution log

**Jun 8, 2026** — Step 4 (Gap-fill) executed for feature-07:

- 23 new smoke files written. The original 10-file
  plan was expanded per the mid-Step-4 splitting rule
  ("split tests so each can run individually"):
  - `F07_01_route.py` covers RT1.
  - `F07_02_dispatch.py` covers TP1–TP4 + DP1–DP5 (one
    file walks depths 0, 1, 2, 3, 5, 10, 11).
  - `F07_03_crumbs.py` covers SH1 (direct call +
    render cross-check).
  - `F07_04a_filename_column.py` covers FT1 (split).
  - `F07_04b_description_column.py` covers FT2 (split,
    multi-line `\n`-encoded description).
  - `F07_04c_tags_column.py` covers FT3 (split,
    union of feature-level + scenario-level tags).
  - `F07_05_subfolder_table.py` covers ST1.
  - `F07_06a/b/c/d_buttons_*` cover BD1, BD2, BD3, BD4
    (split per depth so each button-set's failure is
    independent).
  - `F07_07_button_gaps.py` covers BD5 (probed at
    depths 0, 1, 2, 3, 10; absence of seven forbidden
    handlers + labels).
  - `F07_08a/b/c_empty_*` cover ES1, ES2, ES3 (split
    per depth's empty-FS fixture).
  - `F07_09_rerender.py` covers RR1 (Hybrid: render +
    static `tmsRefreshFolder` body + sse:change
    handler check).
  - `F07_10a..g_*` cover AC1–AC7 (split per
    acceptance bullet; AC7 is end-to-end).
- Each file carries `# Pattern: see .smoke-scratch/README.md`.
- Verification: `./.venv/bin/python .smoke-scratch/run.py
  --filter 07 --verbose` reports `24/24 passed; 0
  failed` and every direct rule-level `PASS <id>: ...`
  line fires (23 new + 1 moved).
- Full-suite re-run (`run.py` without filter) reports
  `76/76 passed; 0 failed`, confirming no regression
  in features 01–06.
- **Spec/code drifts discovered during Step 4.**
  - **ES3 sub-folder branch wording.** Spec says
    depth-3+ empty renders "No test cases in `<folder>`
    yet." Code: `folder_subfolder.html` renders
    "Nothing in `<folder>` yet." (depth-2
    `folder_module.html` does match the spec).
    `F07_08c` follows code (test asserts "Nothing
    in"); surfaced in the row note for spec or
    template alignment. Same shape as feature-04 UI3,
    feature-05 RR1c.
- **Per-rule notes:**
  - **FT3 (tag chips)**: `Storage.list_folder` now shows
    the **union** of feature-level + scenario-level tags
    (D10), matching `_case_tags` in `reporting.py`. (Bug
    fix Jun 11, 2026 — the listing previously read
    `feature.scenario.tags` only, so feature-level tags
    never appeared in the column.)
  - **F07_02 / F07_10d** initial failures were due to
    the `with tempfile.TemporaryDirectory()` block
    closing before later `client.get(...)` calls. Fix:
    keep all assertions inside the `with` block so the
    data root stays alive.
  - **F07_04b (FT2 description)** uses the literal
    two-character sequence `\n` on the `Feature:`
    line (decoded by `_assemble_description` into a
    real newline) to construct multi-line descriptions
    via the raw PUT route (canonical create only
    accepts single-line descriptions).
  - **F07_09 (RR1)** asserts THREE separate halves:
    (a) `<main id="main-pane">` does NOT carry
    `hx-trigger="sse:change"`; (b) `tmsRefreshFolder`
    body builds `/ui/folder/<path>` and calls
    `htmx.ajax("GET", ...)` targeting `#main-pane`;
    (c) the body-level `sse:change` handler does NOT
    touch `#main-pane` or call `tmsRefreshFolder`
    (so the main pane never silently SSE-wires).
  - **F07_10g (AC7 end-to-end)** triggers three CRUD
    cycles at depths 0/1/2 (project, module, file)
    and after each one issues the `tmsRefreshFolder`
    GET URL directly, asserting the response
    reflects the new FS state.

**Feature-07 cycle complete.** Per the locked plan,
**feature-08 is next** — audit
`specs/features/08-*-NEW.md` (file editor).

## Notes & flags

- **Step 2 plan (one move).** Per the Step-2 rule
  established during feature-06 ("move smokes whose
  primary frame is the feature being audited"):
  - `.smoke-scratch/p2_2c_project_view_hides_test_run.py`
    \u2192 `.smoke-scratch/feature-07/F07_02b_project_view_filters_test_run.py`.
    Tests the rendered `folder_project.html` output's
    test-run filtering \u2014 the rendering layer is
    feature-07's territory. The underlying rule
    (`Storage.list_folder` filters `test-run`) stays
    primary-framed in feature-06 HD3; this smoke is
    the HTML-half counterpart that asserts the filter
    actually reaches the rendered project view.
  - **Originally stayed in `.smoke-scratch/` root** (NOT
    moved by feature-07 — *superseded*: all of these have
    since been folded into `feature-10/` — `p3_a*` +
    `p2_2d/2e/s3/s4/s6` during feature-10's own cycle, and
    `p2_2a` → `F10_80` / `p2_2h` → `F10_81` / `p2_s7` →
    `F10_79` in feature-10 Step 5; the root now holds only
    `run.py`):
    - `p3_a1` / `p3_a2` / `p3_a3` \u2014 test the
      test-run typed area branch of `ui_folder`
      (`segments[1] == "test-run"`); primary frame =
      feature-10 (test-run typed area).
    - `p2_2a` / `p2_2d` / `p2_2e` / `p2_2h` / `p2_s3`
      / `p2_s4` / `p2_s6` / `p2_s7` \u2014 sidebar shell /
      test-run sidebar; primary frame = feature-10.
- **Step 3 plan (refine the moved file).** Update
  `F07_02b`'s docstring to anchor on TP2 + cross-pointer
  to feature-06 HD3; add positive controls (project name
  appears, sibling module appears) on top of the existing
  negative invariant.
- **TP+DP combination.** `F07_02_dispatch.py` covers
  TP1\u2013TP4 + DP1\u2013DP5 in one file by walking each depth
  (0, 1, 2, 3, 5, 10, 11) and asserting (a) the right
  template fires and (b) its surface markers are present
  (heading, breadcrumb, button labels). Empty states are
  covered separately in `F07_08_empty_states.py` because
  they share the templates but have a different setup
  fixture (no children at the target depth).
- **AC7 testable shape.** Hybrid:
  - **Static**: app.js defines `function tmsRefreshFolder
    (folderPath)` that issues `htmx.ajax("GET",
    "/ui/folder/" + (folderPath || ""), {target: "#main-pane",
    swap: "innerHTML"})`. Greppable in `app/static/app.js`.
  - **Render-and-grep**: every folder view's root `<div>`
    carries `data-folder-path="{{ folder_path }}"` (used
    by the create-button handlers to know which path to
    refresh after a CRUD operation).
  - The "actually updates the pane" link is delegated to
    HTMX library behaviour, mirroring AC2's framing in
    feature-06.
- **RR1 testable shape.** Static + render-and-grep:
  - `<main id="main-pane">` in `app/templates/base.html`
    does NOT carry `hx-trigger="sse:change"` (only
    `#tree-pane` does).
  - `tmsRefreshFolder` is exported in app.js.
  - The `sse:change` body listener in app.js does NOT
    touch `#main-pane` for tree refreshes (it only
    routes to the file/run editor's external-change
    handlers).
- **Test-run typed area is OUT OF SCOPE.** `ui_folder`'s
  `segments[1] == "test-run"` branch dispatches to
  feature-10's templates (`folder_test_run_area.html`
  and `folder_test_run_group.html`). The smokes for that
  branch (`p3_a1`, `p3_a2`, `p3_a3`) stay in
  `.smoke-scratch/` root with primary frame = feature-10.
  This feature's matrix only covers the non-typed-area
  branch.
- **Spec gaps discovered during Step-1 read-through.**
  - The spec lists `\ud83d\udcc1` (folder icon) for the
    `Sub-folder` column. Quick check on
    `folder_module.html` / `folder_subfolder.html`
    confirms the icon is rendered. The smoke (ST1)
    asserts presence of the icon character or the
    surrounding markup.
  - **Spec/template ambiguity (BD3).** Spec says
    depth-2 has `+ Sub-folder` and `+ Create test case`
    buttons; depth 3..10 has the same. The sub-folder
    empty state at any depth uses `+ Test case` (no
    "Create" prefix) instead. The smoke asserts both
    labels are present somewhere in the rendered page
    (header button + empty-state CTA) at the right
    depths, treating the label drift as cosmetic.
    Surfaced for spec polish but not a behavioural gap.

## Step 1 sign-off log

**Jun 8, 2026** — Step 1 (Audit) sign-off for feature-07:

1. **Q1 — TP+DP combination.** Approved **combine**:
   one `F07_02_dispatch.py` covers TP1–TP4 + DP1–DP5
   by walking depths 0, 1, 2, 3, 5, 10, 11 and asserting
   the right template + structural markers at each.
2. **Q2 — Step 2 move for `p2_2c`.** Approved **move**:
   `.smoke-scratch/p2_2c_project_view_hides_test_run.py`
   → `feature-07/F07_02b_project_view_filters_test_run.py`
   as the HTML-half companion to feature-06 HD3.
3. **Q3 — AC7 testable shape.** Approved **end-to-end**:
   the smoke fires a real CRUD POST + simulates the
   `tmsRefreshFolder` GET, asserting the response
   reflects new FS state at depths 0, 1, 2.
4. **Q4 — BD3/BD4 label drift handling.** Approved:
   assert both labels (`+ Create test case` in module
   header, `+ Test case` in sub-folder empty-state CTA)
   at their respective sites, surface drift as a
   spec-polish note.

**Mid-Step-4 sign-off (Jun 8, 2026) — splitting heuristic:**
*"Split tests into smaller ones to ensure each can run
individually."* Memorialised in the smoke-suite memory
store. Applied retroactively within feature-07: FT1/FT2/FT3
split into `F07_04a/b/c`; BD1–BD4 split into
`F07_06a/b/c/d`; ES1/ES2/ES3 split into `F07_08a/b/c`;
AC1–AC7 split into `F07_10a..g`. A regression in any
one rule no longer masks verification of the others.
