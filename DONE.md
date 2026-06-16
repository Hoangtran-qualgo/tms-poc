# Done backlog

Items fixed during v1 manual verification.

## Must have

- **Test-case directory tree: folders above files within each folder
  (shipped Jun 16, 2026).** Reference:
  `specs/features/06-feature-tree-pane-NEW.md`. The Directory sidebar tree
  interleaved sub-folders and `.feature`/other files (`_tree_children` in
  `app/storage/_listing.py` appended in raw `iterdir()` order). It now does a
  **stable** partition — `children.sort(key=… folder→0, file→1)` — so all
  folders hoist above all files at every level, while the intra-group order is
  preserved unchanged (only the folder/file split moved). `tree.html` needed no
  change (it renders the order it's given); main-pane folder views +
  `list_test_run_tree` left untouched per scope. No existing smoke pinned the
  interleaved order (all use order-insensitive lookups); new
  `feature-06/F06_13_tree_folders_above_files` asserts all folders precede all
  files. Full suite **306/306**. Too small for a `tech-*` spec.

- **Test-run list: status badge colours match the result palette
  (shipped Jun 16, 2026).** Reference:
  `specs/features/10-feature-test-run-NEW.md`. The runs-list (group view)
  status badges (`app/templates/folder_test_run_group.html`) used divergent
  hard-coded tints (PENDING slate, EXECUTING amber, SKIPPED slate). They now
  carry `data-status` and inherit the canonical `app/static/app.css`
  `[data-status]` palette (tech-02 D1) — **✓ green, ✗ red, ? orange, ⋯ blue,
  ⤷ purple** — matching the run-editor chips + the result `<select>`. Symbol +
  count only (no status word, unlike the run-editor summary); zero-count badges
  still omitted. Tests: `F10_14` needed no re-pin (only checks symbol+count);
  new `feature-10/F10_86_group_badge_palette` (each badge carries data-status,
  no hard-coded bg tint, no status word). Full suite **305/305**. Too small for
  a `tech-*` spec.

- **Test-run detail: per-status result summary below the description
  (shipped Jun 16, 2026).** Reference:
  `specs/features/10-feature-test-run-NEW.md`. A one-line **Result** summary
  renders below the description / "Created …" line, above the Results table.
  - **Chips.** One chip per `RUN_RESULTS` status showing **symbol + count +
    word**, e.g. `✓ 1 PASSED  ✗ 2 FAILED  ? 3 PENDING  ⋯ 4 EXECUTING
    ⤷ 5 SKIPPED`. Zero-count chips are hidden; an em-dash shows when the run is
    empty. Server-rendered in `app/templates/run_editor.html` via
    `selectattr` counts.
  - **Colours = single source of truth.** Chips carry `data-status` and inherit
    their colour from `app/static/app.css`'s `[data-status]` palette (tech-02
    D1): PASSED green, FAILED red, PENDING orange, EXECUTING blue, SKIPPED
    purple — so they always match the result `<select>`. No colour map
    duplicated in JS/template.
  - **Live update.** `tmsRunEditor._updateResultSummary`
    (`app/static/06_run_editor.js`) recomputes counts from the live
    `.run-result-select` values and is wired into `_refreshDirty`, so the chips
    stay accurate on every result change / add / remove (not reload-only). It
    only writes the count numbers + toggles `hidden` (display-only; never enters
    the dirty snapshot).
  - Tests: new `feature-10/F10_84_result_summary_render` (counts, status words,
    hidden zero-count chips, em-dash) + `F10_85_result_summary_live` (live JS
    wiring). Full suite **304/304**. Too small for a `tech-*` spec.

- **Test-run list: open a run group from the Test-run sidebar tree
  (shipped Jun 16, 2026).** Reference:
  `specs/features/10-feature-test-run-NEW.md`. The main-pane run listing
  already existed (`ui_folder`'s typed `test-run` dispatcher →
  `folder_test_run_group.html`, reached from the run-editor breadcrumb); only
  the **sidebar wiring** was missing.
  - **Change.** In `app/templates/test_run_sidebar.html`, **group** (depth-1)
    folder rows now navigate via
    `hx-get="/ui/folder/<project>/test-run/<group>"` (caret still toggles
    children), mirroring `tree.html`'s folder navigation. **Project** (depth-0)
    rows stay **toggle-only** / non-interactive (USER decision).
  - Tests: new `feature-10/F10_83_sidebar_group_nav` (group row links to the
    run listing; project row has no nav target; run leaf still links to the
    editor). No existing smoke pinned the old non-interactivity. Full suite
    **302/302**. Too small for a `tech-*` spec.

- **Scenario Outline as per-example run items — `tech-09`
  (shipped Jun 16, 2026).** Spec:
  `specs/tech/09-tech-outline-import-run-NEW.md`. Follow-up to `feature-15`;
  builds on `tech-05`. An Allure report renders one Scenario Outline as N
  leaves `"<base> -- @<table>.<row> "` (one per `Examples` data row); each row
  now becomes a **distinct run item** pointing at the single outline case.
  - **Suffix parser (DO-1).** `split_example_suffix` (`app/allure_io.py`)
    trims a whitespace-tolerant trailing ` -- @<n>.<m>` to recover the base
    name + `{table, row}` (1-based ints); plain names pass through untouched.
  - **Per-example identity (DO-2).** `RunResult` gains an optional
    `example: {table, row}` (`app/models/_run.py`), **omitted from `to_dict`
    when `None`** so legacy run YAML / JSON keeps its exact
    `{file_path, result, remark}` shape. Uniqueness key relaxed to
    `(file_path, example)` — same path may repeat once per example row, two
    plain results on one path still duplicate.
  - **Import (DO-3).** One shared `_classify_report` helper
    (`app/server/routes_runs.py`) splits each row's suffix, resolves the
    **distinct base names**, and re-attaches each row's `example`. An outline's
    repeated base is kept as distinct rows (never "ambiguous"); counts tally
    **per report row** (fixes the old `len(resolution[...])` collapse); errors
    key on the **suffixed** name. Allure carries no remark.
  - **Editor display (DO-4).** `ui_run` (`app/server/routes_ui.py`,
    `_resolve_example`) reads the live Examples header + matched data row for a
    pinned example (tolerant-blank when not an outline / row out of range);
    `run_editor.html` renders base name + a small monospace `| a | b |` block
    in the display-only scenario cell (dropped `truncate`).
  - **DQ1 global tombstone change.** Removed-case cue moved to a **"file has
    been removed"** sub-line under the filename (Test-case column); the
    remark-column `run-remark-override` was removed for **all** runs.
  - **Manual add (DO-5).** Adding an outline case in the run editor
    (`app/static/06_run_editor.js`) expands into N rows stamped with
    `data-example`; `_readCurrent` / `_compareJson` canonicalize + sort on
    `(file_path, example)` so same-path rows don't false-flag dirty, and the
    full-run PATCH round-trips the per-example identity.
  - **Import-modal width (USER follow-up Jun 16).** `tmsOpenModal` gained a
    `2xl` (`max-w-6xl`) tier; the **Import test cases** modal now uses it and
    shows up to **50 chars** of a scenario name on one line.
  - Tests: new `tech-09/T09_01..06` + `COVERAGE.md`; re-pinned `F10_29`,
    `F10_32`, `F10_75`, `T05_04`, and `F14_04` (modal width / 50-char name).
    Full suite **301/301**.

- **Import a test run (upload an Allure HTML report → TMS test run) —
  `feature-15` (shipped Jun 15, 2026).** Spec:
  `specs/features/15-feature-import-test-run-NEW.md`. Upload a single-file
  Allure 2 report; each report scenario maps **by name (case-insensitive,
  whole-project)** to a TMS case, and the report's scenarios become one test
  run written under a chosen project's `test-run/<group>/`. **All-or-nothing:**
  any unmatched / project-ambiguous scenario aborts with a per-line error.
  - **Parser (DO-1).** `parse_allure_report` in `app/allure_io.py` — pure
    (text in / dataclasses out): extracts the `d('<path>','<b64>')`
    embedded-data calls, decodes `data/suites.json` (leaf walk, depth-agnostic)
    + `widgets/summary.json`. Status map (IR-3): `broken`→FAILED,
    `unknown`/unrecognised→SKIPPED. `created_at` from `summary.time.start`
    (IR-4, earliest-leaf fallback), **never server-now**. Same-name retries
    collapse to the final run by `time.stop` (IR-5b). Malformed / non-Allure →
    `ValueError` → 400 `bad_request`.
  - **Storage (DO-2/DO-3).** `import_test_run` in `app/storage/_runs.py` — a
    near-clone of `create_run` that takes `created_at` verbatim + caller-supplied
    `RunResult`s (still gated by `validate_run`); `resolve_scenarios` in
    `app/storage/_search.py` — project-wide, case-insensitive name→path resolver
    returning `{matched, unmatched, ambiguous}` (skips unparseable cases).
  - **API (DO-4).** `POST /api/runs/import/preview` (report name + `created_at`
    + per-scenario rows + counts + per-line `errors`) and `POST /api/runs/import`
    (re-parses + re-resolves server-side; all-matched → one `RunResult` each,
    else `ImportValidationError` → 422 `{reasons}`), both capped at **30 MB**;
    text body (`html`), no multipart (`app/server/routes_runs.py`).
  - **UI (DO-5).** Top-bar **Import test run** button beside **Import test
    cases**; `tmsImportRun()` modal in `app/static/04_run_create.js` (appended,
    no new script tag) + `app/templates/base.html`. Destination from
    `/api/run-groups` (existing group only, **no "+ create group" row**, IR-6);
    `#`/`Scenario`/`Result`/`Matched case` preview; **raw `fetch`** (not
    `tmsApiPost`) to keep `details.reasons`; client gates `.html` + 30 MB.
  - **Report is transient:** parsed in-memory, **never persisted** — only the
    run `.yaml` is written (`F15_05` asserts zero `.html` under the data root);
    on success the modal clears the file input and **opens the new run** by
    default.
  - **NOTE / accepted risk:** name match is whole-project + case-insensitive
    (explicitly *temporary*, IR-5) — cross-folder name reuse makes a scenario
    ambiguous and aborts the import. Tracked by the open `IN-PROGRESS.md`
    Must-have on a project-level scenario-name uniqueness rule.
  - Tests: new `feature-15/F15_01..06` + `COVERAGE.md`. Full suite **295/295**
    (was 289; +6 feature-15).

- **Revamp the test-case list (Enums column + top-3 Tags) — `tech-08`
  (shipped Jun 15, 2026).** Spec:
  `specs/tech/08-tech-testcase-list-revamp-NEW.md`. Folder-detail features
  table gains a new **Enums** column and caps both Tags and Enums to the
  first **3** chips + `+N more…`, with the full set in the cell `title`.
  - **Storage (DO-1).** `Storage.list_folder` attaches `enums:
    [{kind, key, label}]` per row via a storage-local `_enum_display_rows`
    helper (mirrors `reporting._case_enums`, no engine import); vocab read
    once per call (best-effort), kind-sorted, unset skipped, redundant
    `label == key` blanked; parse-failure rows get `enums: []`
    (`app/storage/_listing.py`).
  - **Template (DO-2).** `_folder_feature_table.html` — Enums chips read
    `key : label` (indigo, no `@`); both columns show top-3 + `+N more…`,
    em-dash when empty; widths rebalanced (File `1/5` · Scenario `2/5` ·
    Tags `1/5` · Enums `1/5`).
  - **Decisions.** LR-2 = `key : label`; cap raised from 2 → **3** per USER
    request. `feature-07/F07_04c` needed no re-pin (3-tag fixture under a
    cap of 3).
  - Tests: new `tech-08/T08_01..02` + `COVERAGE.md`. Full suite **289/289**.

- **Require `scenario_name` at the create API — `tech-07`
  (shipped Jun 15, 2026).** Spec:
  `specs/tech/07-tech-require-scenario-name-create-api-NEW.md`. Closes the one
  unguarded HTTP entry point that still accepted an empty scenario name
  (deferred from `tech-04` as Option B). Chose **Option A — API-only
  entry-point enforcement** (SN-1=A, SN-2=standard 400, SN-3=strip-aware),
  matching how `import_feature_cases` already enforces it server-side; the
  model stays permissive (V5) so tech-04 D1's bare-`Scenario:` round-trip is
  untouched.
  - **API (DO-1).** `post_file` now requires a non-empty `scenario_name` via
    `_require_non_empty_string` + a strip guard
    (`app/server/routes_files.py`); `create_file`, `validate_feature`,
    PATCH/PUT-raw, and the editor save-gate are unchanged.
  - **Re-pin (DO-2).** Added a `scenario_name` to **64 `POST /api/files`
    create sites across 38 smoke files** (`feature-04/05/06/07/08`,
    `tech-03`). `F05_07_create_body` rewritten to the new required contract;
    `F05_12`/`F10_51`/`F10_52` kept their original guard as the
    discriminator. No `storage.create_file` fixtures touched.
  - Tests: new `tech-07/T07_01` + `COVERAGE.md`. Full suite **287/287**.

- **Import test cases (upload a `.feature`, split into cases) — `feature-14`
  (shipped Jun 13, 2026).** Spec:
  `specs/features/14-feature-import-test-cases-NEW.md`. Upload one `.feature`
  file; each scenario is split into a single test case (the one-file =
  one-scenario model invariant), all sharing the source feature description,
  feature tags, and `Background`.
  - **Splitter (DO-1).** `split_feature_source` + a shared `_collect_children`
    helper in `app/gherkin_io.py`; `parse_feature` (exactly-one) rebuilt on
    top so feature-01's error/line-col contracts stay byte-identical. Missing
    `Feature:` header is synthesized with a blank description (IM-A); enum
    directives are always dropped (IM-2).
  - **Storage (DO-2).** `create_feature_file` + `import_feature_cases` in
    `app/storage/_features.py` — **all-or-nothing** with a pre-flight
    (collect-all `ImportValidationError`) and compensating-delete rollback on
    any mid-write failure. Uniqueness (file + scenario names) is scoped to the
    destination folder's direct children, **case-insensitive**, and also
    enforced within the batch.
  - **API (DO-3).** `POST /api/files/import/preview` (shared header +
    per-scenario `{scenario_name, step_count, scenario_tags}` + `enums_present`)
    and `POST /api/files/import` (`{project, parent, source, names}`), both
    capped at **3 MB**; text body (no multipart, mirrors `PUT /files/<p>/raw`).
    `ImportValidationError` → 422 `import_validation_error {reasons}`
    (`app/server/routes_files.py`, `app/server/errors.py`).
  - **UI (DO-4).** Global **Import test cases** button in the top bar
    (`app/templates/base.html`) → `tmsImportFile()` modal
    (`app/static/03_folder_actions.js`): project + destination-folder pickers
    (built from `/api/tree`, folders shown relative to the chosen project),
    `.feature` picker with client type + 3 MB gating, a bordered preview table
    (Scenario name 30-char truncate · Feature tag · Scenario tag as top-2
    `@`+N-more · File name input, placeholder-only), enum-drop acknowledgement
    gate, and collect-all reason list on abort.
  - **NOTE:** only **feature + scenario** tags are supported; `Examples:`-level
    tags are not a first-class concept yet (they round-trip verbatim but are
    not surfaced). Documented in the spec + `README.md`.
  - Tests: new `feature-14/F14_01..04` + `COVERAGE.md`. Full suite **286/286**.

- **Revamp test-case detail (editor) + search display — `tech-04`
  (shipped Jun 13, 2026).** Spec:
  `specs/tech/04-tech-testcase-detail-revamp-NEW.md`.
  - **Description optional (D1).** Dropped the non-empty rule in
    `validate_feature` (`app/models/_feature.py`); an empty description
    serialises to a bare `Feature:` line and round-trips. The editor's
    description is a 1-line `textarea`.
  - **Scenario name is the identity.** Create flow is a 3-field modal
    (File name, Feature description optional, Scenario name) in
    `tmsCreateFile` (`app/static/03_folder_actions.js`); the editor
    Save-gate now keys on scenario name (RG1), not description, and the
    `#scenario-name` placeholder reads "Scenario name" (was "(optional)").
    `POST /api/files` + `create_file` accept a `scenario_name` (required at
    the API as of **`tech-07`**, shipped Jun 15, 2026; see above). The
    file-name `<h2>` header is removed (D4).
  - **One-time migration** `scripts/backfill_scenario_names.py` moves each
    legacy `description` into `scenario.name` (newlines → `" / "`), skips
    already-named/empty-description files, idempotent.
  - **Enums redesign (D5).** Replaced the one-`<select>`-per-kind model
    with an up-to-3-column (kind, value) row grid + `+ Add enum` /
    per-row remove in `app/static/08_file_editor.js` (`_renderEnumRows` /
    `_buildEnumRow` / `_commitEnumRows`); ED11/ED12 + orphan handling
    preserved.
  - **Search (OQ8).** Results list shows the scenario name instead of the
    description; `SearchHit` carries `scenario_name`
    (`app/storage/_search.py`, `app/templates/search_results.html`). Text
    search now matches the `Feature.description` **OR** the scenario name
    (either field; the `matched_field` badge stays `"description"`).
  - **Folder-detail list.** The test-case list's middle column shows the
    scenario name instead of the feature description; `Storage.list_folder`
    now carries `scenario_name` per row (`app/storage/_listing.py`,
    `app/templates/_folder_feature_table.html`).
  - Tests: new `tech-04/T04_01..03`; re-pinned
    feature-01/02/05/08/09/11 smokes. Full suite **275/275**.

- **Run detail: scenario-name column + remark resize — `tech-05`
  (shipped Jun 13, 2026).** Spec:
  `specs/tech/05-tech-run-detail-scenario-name-NEW.md`. Builds on the
  tech-04 migration.
  - **Display-only Scenario name column.** The run editor table is now
    `Test case | Scenario name | Result | Remark | ×`. `ui_run`
    (`app/server/routes_ui.py`) reads each result's scenario name **live**
    from the `.feature` (tolerant: tombstoned / unparseable → blank, RD-4);
    it is rendered as a plain `run-scenario-name` `<td>` (not an input), so
    it never enters the dirty snapshot or the run model / JSON API (RD-3).
  - **Add-on-fetch (RD-1b).** Newly-added rows fetch their scenario name
    from the existing `GET /api/files/<path>` via `_fillScenarioName`
    (`app/static/06_run_editor.js`); no new endpoint and no per-feature
    parsing added to the `list_tree` sidebar hot path.
  - **Remark resize (RD-2a).** CSS-only: the textarea is a fixed ~1.5-line
    height (`h-10`) + `overflow-y-auto` so a clipped 2nd line cues "there's
    more"; column narrowed to `w-1/4`. Folder-group heading `colspan`
    bumped 4→5 (server row + clone template).
  - Tests: new `tech-05/T05_01..04` + `COVERAGE.md`; no feature-10 re-pin
    needed. Full suite **279/279**.

- **Quality-report detail: extra columns — `tech-06`
  (shipped Jun 13, 2026).** Spec:
  `specs/tech/06-tech-report-detail-columns-NEW.md`. Builds on the tech-04
  migration; enhances `feature-12`.
  - **Case trend (ask 1).** `_case_trend` (`app/reporting.py`) adds
    `run_name`; the timeline table gains a **Run name** column →
    `Run | Run name | When | Result`. RP-3: re-investigated and confirmed a
    run always has a non-empty name (`POST /runs` requires it, `validate_run`
    enforces it, all writes go through `_serialize_run`), so the column
    renders `run.name` directly with no fallback.
  - **Per-case enrichment (asks 2–4).** New `_read_vocab` + `_case_enums`
    helpers; `compute_report` threads `project` into `_tag_ranking` /
    `_tag_inventory`. Per-case entries gain `scenario_name` plus the type's
    extra dimension: enum-ranking → `tags`; tag-ranking / tag-inventory →
    `enums` rendered `key : label` (RP-2). Tombstoned `(removed)` cases
    enrich to blanks. Since `write_feature` cross-checks enums against the
    vocab, the only blank-label path is a missing/unreadable `enums.yaml` at
    report time → key-only, no crash.
  - **Per-case row layout.** Scenario name is the prominent identity
    (`text-slate-800 font-medium`); the case path is a muted mono link
    separated by a `·` divider (`app/templates/report_detail.html`).
  - **Bucket bar contrast.** Track = total (dark grey `bg-slate-400`); fill
    = dark green (`bg-green-600`) for real buckets, orange (`bg-orange-500`)
    for synthetic ones (unset/removed/untagged).
  - Tests: new `tech-06/T06_01..03` + `COVERAGE.md`; re-pinned `F12_02` for
    the additive per-case keys. Full suite **282/282**.

- **Search function does not display results.**
  - Root cause: HTMX 2.x filter expressions like `keyup[key=='Enter']`
    fail silently (bare `key` is undefined in the filter eval scope), so
    no `/ui/search` request was ever made. Replaced with explicit JS
    wiring (`tmsWireSearch` in `root/app/static/app.js`)
    that debounces input 300 ms and fires immediately on Enter.

- **Feature file in `Structured` view does not display inline data
  (step DataTables).**
  - Added `tmsEditor._renderStepDataTable` in
    `root/app/static/app.js` and wired
    it into `renderSteps`. Each step now shows either a `+ table` button
    (when `data_table` is null) or an inline editable mini-grid with
    per-column / per-row remove controls and a `× remove table` footer.
    `cleanupBuffer` strips all-empty body rows on save.

- **Inline data table & Examples table sizing.**
  - Both grids now render at `width: 50vw; max-width: 100%` with
    `table-layout: fixed` so columns share the width evenly. Cells are
    `<textarea rows="1">` that auto-resize on every keystroke; the cap
    is computed at render time as `5 × headerCell.offsetHeight`, after
    which the cell scrolls internally. Enter is suppressed and pasted
    CR/LF is collapsed to spaces, keeping the Gherkin pipe-table
    single-line invariant. Shared helpers (`_makeGridCell`,
    `_autoSizeCell`, `_finalizeGridSizing`) live in
    `root/app/static/app.js` and are
    consumed by `_renderStepDataTable` and `_renderExamplesGrid`.

## Must have

- **Manual refresh button for the directory tree.**
  - Added a small `↻` icon button at the top of the tree partial
    (`root/app/templates/tree.html`)
    that fires `GET /ui/tree` and swaps `#tree-pane` — the same endpoint
    and target the existing SSE-driven refresh uses, so it's a literal
    manual fallback when the watcher misses an event or the SSE
    connection drops. Pure HTMX attributes, no JS. The button is part of
    the partial, so it re-renders on every swap (stateless).
    `aria-label="Refresh tree"` + `title` for accessibility.

- **Manual refresh button for the test-case editor content.**
  - Added a `Reload` button between `Rename…` and `Save` in the file
    editor topbar
    (`root/app/templates/file_editor.html`),
    wired to a new `tmsEditor.reload()` handler in
    `root/app/static/app.js`. The
    handler confirms with the user when `state.dirty`
    (`Discard unsaved changes and reload from disk?`), then delegates to
    the existing `_refreshFromDisk()` so the structured + raw refetch
    path stays single-sourced with the post-save reload. Also clears any
    open external-change banner, raw parse-error region, and lingering
    `Saved` badge. `title` + `aria-label` for accessibility; failure
    surfaces via `alert("Reload failed: …")`.

- **Move a test case to another folder from the UI.**
  - Storage: `Storage.move_file(source_parts, dest_parent)` in
    `root/app/storage.py` —
    preserves the file leaf (renaming is separate), validates
    destination parent depth in `2..MAX_FOLDER_DEPTH` and existence,
    rejects same-parent moves and name conflicts, acquires src+dst
    locks in sorted order, `os.replace`, marks both sides recently
    written so the watcher self-write suppression covers the move.
  - Server: new `PATCH /api/files/<p>/move` in
    `root/app/server.py`, body
    `{ parent: "<dest folder>" }`. Kept distinct from
    `PATCH /api/files/<p>/rename` so each endpoint owns one semantic
    (mirrors the existing `rename` / `duplicate` / `delete` suite and
    leaves room for a future `PATCH /api/folders/<p>/move`).
  - First in-app modal primitive `tmsOpenModal({title, body, onConfirm,
    confirmLabel, confirmDisabled})` in
    `root/app/static/app.js` —
    overlay + centered card, backdrop / Esc / Cancel dismiss, caller
    decides when to close (so failed requests keep the modal open).
    Returns `{ close, setConfirmDisabled }` for programmatic control.
    Built generic for reuse by future pickers.
  - UI: `Move…` button between `Rename…` and `Reload` in
    `root/app/templates/file_editor.html`,
    wired to `tmsEditor.move()`. Handler confirms when `state.dirty`,
    fetches `/api/tree`, walks it to collect every folder with
    `2..MAX_FOLDER_DEPTH` path segments, opens the modal with a
    `<select>` (current parent rendered but disabled, prompt option
    keeps Confirm disabled until a real pick is made). On success
    navigates to the file at its new path via
    `htmx.ajax('GET', '/ui/file/<newpath>', …)`; server errors surface
    inline in the modal so the user can correct and retry.
  - Verified by 5 storage micro-tests (happy path, depth-cap reject,
    missing-parent reject, name-conflict reject + source preserved,
    same-parent reject), 2 server micro-tests (happy 200 + the three
    error-envelope cases), and a UI smoke that the `#btn-move` element
    is rendered.

- **Single-form create-test-case flow.**
  - Replaced the two sequential `window.prompt` calls in `tmsCreateFile`
    (`root/app/static/app.js`) with
    one `tmsOpenModal`-based form. The function signature is unchanged,
    so the `+ Create test case` buttons + empty-state CTAs in
    `root/app/templates/folder_module.html`
    and
    `root/app/templates/folder_subfolder.html`
    work as-is.
  - Form: a file-name `<input>` with the hint
    `".feature is added automatically"` (server-side
    `_normalize_filename` still appends the suffix), a
    `<textarea rows="2">` for the description, and a single `Create`
    button. Confirm is gated on "both fields non-empty after trim";
    everything else (regex, name conflicts) is delegated to the server
    response so the client never drifts from `_validate_segment` /
    `NameConflictError`. Pattern mirrors `tmsEditor.move()` —
    server-side errors render inline in the modal and the user can
    correct and retry. Keyboard: autofocus file-name; `Enter` in the
    name field jumps to description; `Ctrl/Cmd+Enter` in either field
    submits; `Esc` / backdrop / `Cancel` dismiss. On success the modal
    closes and the existing `tmsRefreshFolder(parent)` runs (no
    behaviour change vs. the previous flow). `node --check` clean.

- **Rewrite `README.md` to the minimal practical contributor doc.**
  - Replaced the prior 18-line `root/README.md`
    (which was an orphan Gherkin block + a one-line run command) with a
    35-line contributor doc organised as: one-line description,
    Prerequisites (Python 3.11+), Setup (venv +
    `pip install -r requirements.txt`), Run (`python3 -m app` + the
    localhost URL), Data (one paragraph on the `./project/` layout),
    and a Docs link map to `PLAN.md` / `IN-PROGRESS.md` / `DONE.md` /
    `AGENTS.md`. The orphan `## Sample / ### sample inline map` block
    is gone.
  - `AGENTS.md` was left untouched (the original plan called for
    trimming it to a 2-line pointer, but it had since been rewritten
    into a full engineering-principles doc; the README's Docs section
    now describes it accordingly).
  - No code changed; `python3 -m app` still launches the app at
    `http://127.0.0.1:5000`.

- **`+ Add test case` modal — tri-state select-all checkbox.**
  - Root cause: the run editor's `+ Add test case` picker
    (`tmsBuildCasePicker` in `root/app/static/app.js`) required one
    click per row even for cases where the user wanted every matching
    `.feature` file. Adding many cases at once was slow and error-
    prone, especially with deeply-nested projects where the filter
    is the main navigation tool.
  - Fix: added a tri-state `<input data-role="select-all" aria-label=
    "Select all visible">` checkbox to the picker's `<thead>` (the
    previously-empty `w-8` cell). New `_refreshHeaderState()` helper
    queries `tr:not(.hidden)` selectors to count visible / selected-
    visible rows and toggles the header between `checked`,
    `unchecked`, and `indeterminate` states. Wired into the existing
    row `change`, row `click`, and filter `input` handlers plus an
    initial call so every selection / filter change refreshes the
    header. The new header `change` handler bulk-toggles every
    currently-visible row to match the header's checked state;
    hidden-but-checked selections are preserved by design so the
    user's pre-filter choices survive bulk operations and filter
    changes.
  - Touched: `root/app/static/app.js` — `tmsBuildCasePicker` only
    (five surgical edits at `:638-643`, `:653 + :680`, `:699-707`,
    four wire-ins at `:709/:715/:729/:749`, and the new header
    handler at `:752-768`). Function signature, return-value
    contract, and the empty-state code path are unchanged.
    `tmsRunEditor._onAddCaseClicked` (the sole remaining caller) was
    not touched — the feature is fully internal to the picker.
  - Verification: one new static-wiring smoke
    `root/.smoke-scratch/p3_i1_picker_select_all_wiring.py` asserts
    the `data-role="select-all"` sentinel is present, the
    `aria-label="Select all visible"` copy is wired, and
    `_onAddCaseClicked` contains no `select-all` references (no
    caller-side leak). Full suite: 94 PASS / 0 FAIL across 44
    scripts. Tri-state click behaviour requires a browser per the
    standing Phase-2 lock-in; manual verification sequence is
    captured in spec 10 § Case picker.
  - Specs: `root/specs/features/10-feature-test-run-NEW.md` §
    Case picker grew a new behaviour bullet and § JS controller
    `tmsBuildCasePicker` entry gained a one-clause note about the
    tri-state header.

- **Run editor — mask test-case column to filename only.**
  - Root cause: the run editor's results table rendered the full
    data-root-relative path (e.g. `kchatb2b/desktop-app/UI/AI
    chat/create_page_content.feature`) in the first column. Long
    paths wrapped awkwardly and crowded the Result / Remark
    columns; the meaningful identifier — the filename — got
    lost among the folder segments.
  - Fix: split the cell content into two `<span data-role="…">`s
    inside the existing `<a class="run-row-link">`. Folder is
    rendered muted (`text-slate-400`, `truncate min-w-0` for
    ellipsis on overflow); filename is emphasized (`text-slate-
    700`, `flex-none` so it is always shown in full). The `<a>`
    became a flex container (`flex items-center min-w-0 w-full
    font-mono text-xs`) so the folder shrinks while the filename
    stays at the cell's right edge. Three preservation surfaces
    keep the full path for non-display use: `<tr data-file-path>`
    (serialize / dirty-snapshot), `<td title>` (tooltip), and
    `<a hx-get="/ui/file/…">` (click-through). Defensive split
    (Jinja `rsplit('/', 1)` + JS `lastIndexOf("/")`) handles
    zero-slash file_paths (hand-edited YAML) by rendering an
    empty folder span and putting the whole string in filename.
  - Tombstone interaction (`r.missing`): `line-through` is now
    applied to the **filename span only**; the folder span stays
    muted but unstruck so the path context reads naturally and
    only the case identity is marked as removed. The pre-
    existing `p3_f1_tombstone_render.py` substring check on
    `"line-through"` still passes — `line-through` is inside the
    captured row body, just on a more specific descendant.
  - Touched:
    - `root/app/templates/run_editor.html` — server row at
      `:90-110` (added defensive `rsplit` + two-span structure;
      dropped dead `truncate` from outer `<td>` since the inner
      folder span owns the ellipsis now), `<template>` prototype
      at `:139-147` (mirror of the two-span shape; dropped same
      dead `truncate`).
    - `root/app/static/app.js` — `tmsRunEditor._createResultRow`
      at `:1119-1142` (defensive `lastIndexOf("/")` split;
      `querySelector('[data-role="folder"]').textContent` +
      `querySelector('[data-role="filename"]').textContent`;
      `title=` + `hx-get=` preserved as before).
    - Pre-existing observation (per AGENTS.md "mention don't
      delete"): the prototype's `<td class="px-3 py-2 text-
      slate-800">` carries a pre-existing `text-slate-800` that
      is overridden by the inner spans' colors and has no
      visible effect. Left untouched.
  - Verification: three new static-wiring smokes —
    `root/.smoke-scratch/p3_j1_run_editor_two_span_template.py`
    (template grep: both `data-role` spans on server row +
    prototype, full path preserved on `tr data-file-path` / `td
    title` / `a hx-get`, no `truncate` on outer `<td>`),
    `root/.smoke-scratch/p3_j2_create_result_row_populates_
    spans.py` (JS function-body grep: `lastIndexOf("/")` split,
    both spans receive `textContent` assignments, `title` and
    `hx-get` preserved), and
    `root/.smoke-scratch/p3_j3_tombstone_strikes_filename_only
    .py` (Flask + Storage fixture: tombstoned row's filename
    span has `line-through`, folder span doesn't; sibling live
    row carries no `line-through` on either span). Full suite:
    104 PASS / 0 FAIL across 47 scripts (was 94 / 44). Visual
    layout (folder ellipsis behaviour, filename always visible,
    tooltip disclosure) requires a browser; manual verification
    sequence is captured in spec 10 § Run editor / Path
    masking.
  - Specs: `root/specs/features/10-feature-test-run-NEW.md` §
    Run editor grew a new **Path masking (test-case column)**
    sub-block describing the two-span shape and defensive
    branch, and the **Tombstone rendering** bullet that
    previously said "the file-path link swaps to `line-through
    text-slate-400`" was refined to "Only the **filename span**
    swaps to `line-through text-slate-400`; the folder span
    stays muted but unstruck."

- **Rename run-result status `IN-PROGRESS` → `EXECUTING`.**
  - Root cause: the status value `IN-PROGRESS` read as a meta-
    comment about the codebase (cf. the `IN-PROGRESS.md` backlog
    file) rather than a per-case state. `EXECUTING` describes
    the test case, not the process — clearer label, no ambiguity
    with the unrelated backlog filename.
  - Decision (Q1a — hard cutover): renamed in `RUN_RESULTS` only;
    no read-time alias, no startup rewrite pass. Verified before
    implementing that zero on-disk YAMLs under `root/project/`
    contained `result: IN-PROGRESS` (all current values are
    `PENDING`), so the operational migration risk is nil. Pre-
    rename YAMLs containing the old value now fail
    `validate_run` with HTTP 422 and a diagnostic that lists
    the new valid set: `Invalid result value: 'IN-PROGRESS'.
    Must be one of ['PENDING', 'EXECUTING', 'PASSED', 'FAILED',
    'SKIPPED']`.
  - Touched:
    - `root/app/models.py:43` — `RUN_RESULTS` tuple member
      `"IN-PROGRESS"` → `"EXECUTING"`. `validate_run` derives
      its error message from `list(RUN_RESULTS)` verbatim at
      `:512-513` so no error-path edit was needed.
    - `root/app/templates/folder_test_run_group.html:12` (legend
      comment symbol `IN-PROGRESS → ⋯` → `EXECUTING → ⋯`) and
      `:59` (status-badge guard `counts.get('IN-PROGRESS', 0)`
      and interpolation `counts['IN-PROGRESS']` both renamed to
      `'EXECUTING'`).
    - `root/app/templates/run_editor.html` — **not** touched;
      its result `<select>` options come from server-side
      `results_options = list(RUN_RESULTS)`, so the rename in
      `models.py` propagated automatically.
  - Verification: two new smokes —
    `root/.smoke-scratch/p3_k1_run_results_renamed.py` (model
    layer: `RUN_RESULTS` membership, `validate_run` accepts
    `EXECUTING`, rejects `IN-PROGRESS` with a diagnostic
    echoing both the rejected value and the new valid set) and
    `root/.smoke-scratch/p3_k2_run_editor_renders_executing_
    option.py` (Flask + Storage fixture: GET `/ui/run/...`
    renders `<option value="EXECUTING">EXECUTING</option>` and
    contains no `IN-PROGRESS` string; GET
    `/ui/folder/<project>/test-run/<group>` renders the
    `EXECUTING` (`⋯`) badge with the expected count). Full
    suite: 109 PASS / 0 FAIL across 49 scripts (was 104 / 47).
    All 47 pre-existing smokes pass unchanged — confirms the
    pre-flight finding that no smoke referenced the literal
    string `IN-PROGRESS`.
  - Specs: `root/specs/features/10-feature-test-run-NEW.md`
    received three edits — § Summary status list at `:24`,
    § Data model — Constants `RUN_RESULTS` literal at `:92`,
    and a new bullet at the end of § Surface for follow-up
    titled "Status rename history" documenting the old name,
    the rename date, the hard-cutover decision, and the 422
    behaviour for pre-rename YAMLs. `root/specs/features/00-
    summary.md` was not touched (it never mentioned the
    status by name).

- **Review and refine comments across the codebase.**
  - Root cause: three consecutive must-haves shipped during
    Jun 5–8 (test-run feature in three phases, select-all
    picker, path masking, `IN-PROGRESS` → `EXECUTING` rename)
    each touched code adjacent to comments that referenced
    the same features as "see IN-PROGRESS.md" backlog
    pointers. After each feature shipped to DONE.md, the
    corresponding pointers in code went stale: the comments
    still read "see IN-PROGRESS.md '<feature>'" for features
    that had since moved to DONE.md. A parallel drift
    pattern existed in two specs that cited "PLAN.md
    decision B4" / "(R2 / G3 per PLAN.md)" labels that
    PLAN.md no longer carries.
  - Scope decided at Investigate time:
    - Q1(c) — per-citation judgment for stale `IN-PROGRESS.md`
      refs: rewrite to `DONE.md` only where rationale-trail
      is essential; strip otherwise.
    - Q2(b) — leave imprecise prose alone; refine only
      confirmed inaccuracies (e.g. stale cross-references).
    - Q3(c) — line-by-line read of every spec file.
  - Step 1 (code-side, 14 edits across 7 files):
    - `root/app/templates/folder_module.html:5` —
      stripped "(see IN-PROGRESS.md / PLAN.md B4)";
      rewrote prose to a self-contained depth-3 entry-point
      description.
    - `root/app/templates/folder_subfolder.html:6` — same
      pattern, stripped.
    - `root/app/templates/tree.html:34` + `:72` —
      stripped two IN-PROGRESS.md cross-references.
    - `root/app/storage.py:474` — stripped the entire
      "This is the bullet …" sentence; prior sentence
      describes the rule.
    - `root/app/server.py:562` — stripped parenthetical.
    - `root/app/templates/file_editor.html:56` / `:64` /
      `:72` — three IN-PROGRESS.md parentheticals stripped.
    - `root/app/static/app.js:283` — **kept** as
      `(introduced for the "Move test case…" feature; see
      DONE.md § Must have)` — rationale-trail essential
      ("First in-app modal primitive" answers "why this
      exists").
    - `root/app/static/app.js:421` / `:1621` / `:1895` /
      `:2263` — stripped four IN-PROGRESS.md trailers.
    - `root/app/static/app.js:508` — **kept** with redirect
      to `DONE.md § Should have` (the comment's value
      depends on the post-relocation rationale-trail).
  - Step 2 (spec-side, 2 edits after line-by-line read of
    all 11 spec files):
    - `root/specs/features/06-feature-tree-pane-NEW.md:
      134-135` — stripped "(revisits PLAN.md decision B4 —
      …)" parenthetical; promoted its substance ("sub-
      folders under modules navigate to their own view via
      `folder_subfolder.html`") to a standalone clause.
    - `root/specs/features/07-feature-folder-views-NEW.md:
      83` — stripped "(R2 / G3 per PLAN.md)" parenthetical;
      rule "Multi-line descriptions never expand the row"
      stood alone.
  - Touched in total: 9 files (`root/app/storage.py`,
    `root/app/server.py`, `root/app/static/app.js`,
    `root/app/templates/folder_module.html`,
    `root/app/templates/folder_subfolder.html`,
    `root/app/templates/tree.html`,
    `root/app/templates/file_editor.html`,
    `root/specs/features/06-feature-tree-pane-NEW.md`,
    `root/specs/features/07-feature-folder-views-NEW.md`).
    16 edits total (14 in code, 2 in specs).
  - Out of scope but **observed and intentionally left**
    for a future code-comment audit pass:
    - `root/app/storage.py:62` — `Revisits PLAN.md decision
      B4 which previously capped depth at 2.` (same
      stale-PLAN.md-decision-label pattern as the spec
      edits; in a code comment, so out of Step 2's
      spec-only scope).
    - `root/app/templates/folder_module.html:6` — `(R2 /
      G3)` parenthetical (co-located with a comment I
      edited in Step 1 for the IN-PROGRESS.md pattern;
      same stale-PLAN.md-label drift but not the IN-
      PROGRESS.md pattern I was targeting, so left).
    - `root/app/templates/run_editor.html:85` — tombstone
      comment "the row's path is struck through" is
      technically imprecise after path-masking (only the
      filename span is struck) but directionally
      accurate; left per Q2(b).
  - Verification: full smoke suite **109 PASS / 0 FAIL
    across 49 scripts**, unchanged before and after
    (comments-only edits don't affect runtime). Final
    grep check: zero `IN-PROGRESS.md` references in code
    point at items already in DONE.md (the one remaining
    code reference at `root/app/templates/
    test_run_sidebar.html:16` correctly points at the
    still-live `Investigate: persist expand-state for the
    Test run sidebar tab` item in IN-PROGRESS.md `## Could
    have`); zero `PLAN.md decision` / `R2 / G3` refs in
    `specs/`.
  - Pointer-pattern convention established for future
    comments: `see DONE.md § <MoSCoW section>` cites the
    section, not the entry title — provides enough
    navigation context without locking the comment to
    entry-title drift.

- **Folder-detail test-case list — bulk selection + actions (Move /
  Re-tag / Run / Delete), direct children only.** _Investigate + Plan +
  Do shipped Jun 11, 2026; spec
  `root/specs/tech/03-tech-folder-bulk-actions-NEW.md`._
  - A multi-select toolbar above the folder-detail features table lets the
    user select the folder's **direct** test cases and apply one of four
    bulk actions. Scope is one level only — sub-folder cases are never in
    the table (the listing already returns only direct `features`), so the
    "direct children only" rule falls out of the existing data shape.
  - **Shared partial**: the duplicated `features` table in
    `root/app/templates/folder_module.html` (depth 2) and
    `folder_subfolder.html` (depth 3..MAX) was factored into
    `root/app/templates/_folder_feature_table.html` (parameterised on
    `folder_path`). It adds a select-all header checkbox, a per-row
    checkbox carrying the canonical key `data-case-path="<folder>/<file>"`,
    and a toolbar (Move / Re-tag / Run / Delete + live count). The checkbox
    `<td>` and input both `event.stopPropagation()` so toggling never fires
    the row's `hx-get` (same technique as `tree.html`); the `<tr>` hx-get is
    unchanged so the feature-07 contract holds.
  - **Controller**: new `root/app/static/08_bulk_actions.js` (loads before
    `08_enums_manager.js`, keeping `09_bootstrap.js` last per the `T01_01`
    script-order contract). Binds idempotently on `htmx:load` via a
    `data-bulk-bound` guard (NOT `htmx:afterSwap`, which the editor/tree/
    run-editor wiring smokes assume is a single body-level listener).
    Selection is per-render; select-all reflects all/none/indeterminate;
    action buttons disable on empty selection.
  - **All-or-nothing (D3)**: each action runs a read-only pre-flight over
    every selected case and only fans out (sequential, one request per case
    over the existing single-item endpoints — no new HTTP surface) if all
    pass. Any pre-flight failure aborts before a single write and lists the
    blocked case(s) in the modal. Move pre-flights name-conflict via
    `GET /api/folders/<dest>/contents` + same-parent; Run de-dups via the
    run read; Re-tag validates the tag grammar. Move is same-project only
    (D4); Re-tag overwrites feature-level `tags` only and leaves
    `scenario.tags` untouched (D1); Run adds to an existing run only (D2).
  - **Verified**: 6 `tech-03/` smokes (toolbar present at depth 2 + 3;
    per-row checkbox + double stopPropagation + canonical key with the
    `<tr>` hx-get intact; scope = direct-children-only; toolbar only when
    features exist; controller static inspection of the four actions +
    pre-flight endpoints + idempotent bind + D1 tags). feature-07 stayed
    green after both the verbatim extraction and the checkbox/toolbar add.
    Full suite: **272/272 PASS / 0 FAIL**. The fan-out interaction itself
    is client JS (browser-level), verified by static inspection per the
    standing Phase-2 lock-in.

## Should have

- **Review `DONE.md` doc and refine content.**
  - Replaced all 22 occurrences of the machine-specific absolute path
    prefix `@/Users/hoang.tv/Documents/Projects/tms` in `root/DONE.md`
    with the portable placeholder `root` so the file's path citations
    stay meaningful when the repo is checked out elsewhere. Pure
    docs-only edit: no code changed, no other content touched.

- **`Save` (structured) and `Save raw` show no success indicator.**
  - Added a single transient topbar `Saved` badge (green, 1.5 s,
    `role="status" aria-live="polite"`) in
    `root/app/templates/file_editor.html`,
    driven by `tmsEditor.flashSaved()` in
    `root/app/static/app.js`. Wired
    into the success branches of both `save()` (structured PATCH) and
    `saveRaw()` (raw PUT). `markDirty()` clears the badge the moment a
    new edit makes the buffer dirty so the two states never overlap.

- **Relocate + simplify the `+ New run` flow.**
  - Root cause: the Phase-3 navigation graph had no source node for
    run creation. The `+ New run` button lived only in
    `root/app/templates/folder_test_run_group.html`, reachable only
    via a group URL that didn't exist for cold-start projects. The
    sidebar's "Open any project and click + New run" empty-state copy
    pointed at an affordance that didn't exist; the Directory tree
    and project module view both hide `test-run/` by design, so even
    the empirical repro on `kchatb2b` (test-run/ present but empty)
    surfaced no button anywhere.
  - Fix: moved the button to the Test-run sidebar tab header (single,
    always-visible entry point) and rewrote the modal to ask just two
    things — group selector (with `<optgroup label="proj">` rows +
    trailing `+ Create new group...` reveal-on-select) and run name
    (with a live "will save as `<slug>.yaml`" preview). On submit it
    conditionally POSTs `/api/runs/<project>/groups` (auto-creates
    the typed area when bare) then POSTs `/api/runs`, surfacing 409s
    inline next to the offending input, then `htmx.ajax`-navigates
    to the new run editor. A zero-projects branch shows "No projects
    yet — create one first." with a Cancel-only footer (Confirm
    suppressed via a new `tmsOpenModal({confirmLabel: null})` option).
  - Touched: `root/app/storage.py` (new `list_projects()`);
    `root/app/server.py` (new `GET /api/run-groups`);
    `root/app/templates/test_run_sidebar.html` (header button + new
    empty-state copy); `root/app/templates/folder_test_run_group.html`
    (button + CTA removed, replaced with a pointer to the sidebar);
    `root/app/static/app.js` (`tmsCreateRun` full rewrite,
    `tmsOpenModal` extended for info-only modals). Backend storage
    needed zero changes — `Storage.create_run_group` already
    lazy-creates `<project>/test-run/`, and both `create_run_group`
    and `create_run` already raise `NameConflictError` for uniqueness
    violations.
  - Verification: 11 new single-focus smokes under
    `root/.smoke-scratch/` (`p3_h1a` / `p3_h1b` sidebar wiring,
    `p3_h2a` / `p3_h2b` group-view absence + pointer copy, `p3_h3a` /
    `p3_h3b` / `p3_h3c` `/api/run-groups` shape across project
    states, `p3_h4` auto-creation of `test-run/` from the groups
    POST, `p3_h5` duplicate-group → 409, `p3_h6` duplicate-run → 409
    incl. slug-collision path, `p3_h7a..f` JS internals). Two
    pre-existing Phase-3 smokes (`p3_a2`, `p3_b1`) had their
    assertions inverted to reflect the new template contract; no
    test was deleted or weakened. Full suite: 91 PASS / 0 FAIL
    across 43 scripts. End-to-end click behaviour still requires a
    browser per the standing Phase-2 lock-in.
  - Specs: `root/specs/features/10-feature-test-run-NEW.md` rewritten
    across § Scope, § Public surface, § Templates, § JS controller,
    § Invariants & rules / Create flow, § Surface for follow-up;
    `root/specs/features/00-summary.md` § W10 workflow rewritten.

- **Restructure and extend the `.smoke-scratch/` smoke suite.**
  - Restructured every standalone smoke into
    `root/.smoke-scratch/feature-01..11/` as `F<N>_<MM>_<slug>.py` in
    spec-section order, with a `run.py` runner (`--filter` / `--list` /
    `--verbose`), a single `README.md` pattern doc, and a per-feature
    `COVERAGE.md`. Audited every spec rule per feature (PDCA: audit →
    restructure → refine → gap-fill) to zero `missing` rows. No `pytest`
    / harness introduced; UI / browser (Playwright) smokes stay manual.
  - Verification: `python root/.smoke-scratch/run.py` →
    **219/219 PASS / 0 FAIL**.
  - Three spec-vs-shipped drifts pinned (not fixed) by smokes: SC2
    (`F10_47`), SM5/FL6 (`F10_57`), VS3 (`F11_12`).

## Could have

- **Increase folder nesting depth up to 10 levels.**
  - New `MAX_FOLDER_DEPTH = 10` constant in
    `root/app/storage.py`. `create_folder`
    now accepts depth 1..10 and `list_folder` accepts depth 0..10, returning
    `{kind: "module"|"subfolder", folders, features}` whenever the path has
    two or more segments.
  - `POST /api/files` (`root/app/server.py`)
    accepts any parent depth in 2..10 so `.feature` files can live in a
    module or any sub-folder beneath it. `GET /ui/folder/<path:p>` now
    dispatches depth 3..10 to a new `folder_subfolder.html` and passes a
    server-built `crumbs` list to the file editor so its breadcrumb renders
    N segments dynamically.
  - Tree macro
    (`root/app/templates/tree.html`) was
    revised: every folder at any depth now gets an `hx-get` navigation
    target (revisits PLAN.md decision B4 — sub-folders below modules have a
    first-class folder view via
    `root/app/templates/folder_subfolder.html`).
    The module view
    (`root/app/templates/folder_module.html`)
    gained a `Sub-folder` table and a `+ Sub-folder` button.
  - `tmsCreateSubfolder(parent)` helper in
    `root/app/static/app.js` powers the
    new buttons. Vestigial `project`/`module` fields were dropped from the
    file editor's JSON state since the breadcrumb is now server-rendered.
  - Verified via 9 storage micro-tests (`MAX`, depth-10 creation, every
    `list_folder` return shape, file round-trip, rename/delete regression
    at depth 4), 2 server micro-tests (deep-folder `POST /api/files` +
    `ui_folder` dispatch), 5 template micro-tests (module sub-folder row,
    `folder_subfolder.html` breadcrumb + lists, depth-4 file editor
    breadcrumb anchors, JSON state cleanup), and 4 E2E micro-tests
    (integrated module / sub-folder / file-editor / tree flow).

- **New feature: test run (typed area, run editor, tombstone
  render, external-change banner).** _Investigate signed off
  Jun 5, 2026; Do phase shipped Jun 5, 2026 in three slices._
  - **Spec**: `root/specs/features/10-feature-test-run-NEW.md`
    (retroactive as-shipped style — superseded the original
    forward-looking Investigate spec). Aggregated summary entry
    in `root/specs/features/00-summary.md` § 10 +
    workflows W10 / W11 / W12.
  - **Phase 1 — Backend** (storage + HTTP API, zero UI churn).
    New on-disk schema `<project>/test-run/<group>/<run>.yaml`.
    `TestRun` / `RunResult` dataclasses + `RUN_RESULTS` +
    `validate_run` in `root/app/models.py`. `RunParseError`
    (HTTP 422) in `root/app/errors.py`. Storage gained
    `RESERVED_DEPTH2_NAMES = frozenset({"test-run"})`,
    `_normalize_run_filename`, and ten run methods
    (`create_run_group`, `delete_run_group`, `list_run_groups`,
    `list_runs`, `create_run`, `read_run`, `write_run`,
    `delete_run`, `add_run_case`, `remove_run_case`,
    `update_run_result`) in `root/app/storage.py`. HTTP routes
    (`POST /api/runs`, four GET / PATCH / DELETE on
    `/api/runs/<project>/<group>/<file_name>`, three case-level
    routes, plus `POST` / `DELETE` for groups) in
    `root/app/server.py`. `pyyaml` pinned in
    `root/requirements.txt`. Depth-2 reservation + no-`.feature`-
    under-`test-run/` rules surface as 409 via
    `NameConflictError`.
  - **Phase 2 — UI shell** (sidebar restructure, Test run tab).
    Vertical-tab sidebar with Directory tree + Test run tabs in
    `root/app/templates/base.html`; drag-to-resize handle
    (240..600 px, double-click resets to 316 px), localStorage
    width + collapsed persistence. `Storage.list_tree` filters
    `test-run` at depth 1; `Storage.list_folder` filters it from
    project-view module tables; new `Storage.list_test_run_tree`
    aggregates the typed area across projects. New UI route
    `GET /ui/test-run-tree` renders
    `root/app/templates/test_run_sidebar.html`. JS:
    `tmsSwitchSidebarTab`, `tmsActivateTestRunPane`,
    `tmsInitSidebar` (+ resize / collapse) in
    `root/app/static/app.js`. The Test run pane is lazy-mounted
    on first activation; once mounted it subscribes to
    `sse:change` and re-renders even while hidden.
  - **Phase 3 — UI integration** (run editor + create flow).
    Dispatcher branch on `segments[1] == "test-run"` in
    `ui_folder` → `folder_test_run_area.html` /
    `folder_test_run_group.html` (groups landing + runs list
    with status-breakdown badges and `+ New run` toolbar). New
    route `GET /ui/run/<project>/<group>/<file_name>` renders
    `root/app/templates/run_editor.html` (header buttons + run
    fields + results table + `<template>` row prototype + banner
    placeholder). JS controller `tmsRunEditor` in
    `root/app/static/app.js`: dirty tracking via
    JSON-stringify compare, whole-doc PATCH save, manual
    Reload, `Saved` 1.5 s badge, `beforeunload` guard, event-
    delegated per-row remove + remark + select listeners, `+
    Add test case` modal reusing a new `tmsBuildCasePicker`
    primitive (flat checkbox table with live filter +
    exclude-set support), tombstone rendering via server-
    computed `missing: bool` per row (strike-through + "test
    case was removed" override with the hidden-but-preserved
    remark textarea so Save round-trips the stored note),
    `onExternalChange()` state machine mirroring the file
    editor's (removed / changed-clean / changed-dirty) with a
    deferred-banner sentinel that survives the
    `htmx.ajax` re-mount. `tmsCreateRun(project, group)` opens
    an `lg` modal hosting the picker; `tmsOpenModal` gained a
    `size: "md" | "lg" | "xl"` parameter; `tmsSlugifyForFilename`
    derives the run's `file_name` from the human label.
  - **Side fixes**: `folder_test_run_group.html`'s status
    badge for `BLOCKED` was corrected to `SKIPPED` (the actual
    `RUN_RESULTS` enum value) before the new badge could ever
    render incorrectly.
  - **Verified** via 27 standalone smoke scripts in
    `.smoke-scratch/` (13 `p2_*` + 14 `p3_*` files, one per
    scenario), totalling 52 PASS assertions across Phases 2
    and 3. Phase 1 was verified by hand with curl as documented
    in the original Investigate spec. Browser-level smokes
    (3.a–3.f from the spec) covered via manual gestures
    documented in the spec's *Acceptance criteria*. Same-process
    SSE suppression (writer's own Save silences both tabs) is a
    shared caveat with the file editor; end-to-end "two tabs"
    demos require out-of-band edits (`git restore`, terminal
    `vim`, second Flask process).

- **New feature: test-case project-level enums (`Feature.enums`
  + `<project>/enums.yaml`).** _Investigate signed off
  Jun 8, 2026; Do phase shipped Jun 8, 2026 in three slices
  (S1 model, S2 storage, S3 HTTP + editor)._
  - **Spec**: `root/specs/features/11-feature-testcase-component-NEW.md`
    (forward-looking Investigate spec — Q1–Q5 resolved before
    the Do phase began; the spec was not rewritten as
    as-shipped). Aggregated summary entry in
    `root/specs/features/00-summary.md` § 11.
  - **S1 — Model + parser/serializer** (`01-gherkin-io`,
    `app/models.py`, `app/gherkin_io.py`). New
    `Feature.enums: dict[str, str]` dataclass field stores
    selected **keys** only (snake_case identifiers); labels
    live in `enums.yaml` and are display-only. `Feature.validate`
    rejects non-identifier kinds, non-string keys, and embedded
    newlines (multi-line labels). On read, the parser does a
    pre-scan over the raw bytes for
    `# enum.<kind>: <key>` namespaced header comments above
    the feature tags / `Feature:` keyword and lifts them into
    `Feature.enums`. On write, the serializer re-emits one
    line per non-empty entry in **alphabetical kind order**
    immediately after the leading shebang-style block, so
    byte-stable round-tripping holds for any feature whose
    only edit was an enum change. The `enum.` namespace prefix
    avoids collision with hand-written comments like
    `# todo: x` (preserved by the existing comments-are-
    discarded invariant; the namespaced ones are the only
    `#`-prefixed lines the parser lifts into structured state).
  - **S2 — Storage + cross-check + auto-init + tree filter +
    error envelope** (`02-storage-core`, `app/storage.py`,
    `app/errors.py`). New `EnumsParseError` (422
    `enums_parse_error`) registered alongside
    `GherkinParseError` / `RunParseError`; carries
    `details.line` for editor surfacing. `Storage` gained
    `_ENUMS_FILE_NAME = "enums.yaml"`,
    `_ENUMS_DEFAULT_BYTES = b"components:\n"`,
    `read_project_enums` (with an mtime-keyed cache so the
    cross-check in `write_feature` does not re-parse on every
    save), `init_project_enums` (writes exact bytes, refuses
    overwrite via `NameConflictError`), and
    `_cross_check_enums` (hooked into `create_file`,
    `write_feature`, `write_raw`). The cross-check is
    **write-strict on keys only** — unknown kind or unknown
    key in a kind raises `ValidationError(field="enums[<kind>]")`
    (422); all-empty-enums saves skip the cross-check entirely
    so legacy projects without `enums.yaml` keep saving; the
    missing-file rule rejects non-empty enum saves with
    `field="enums"` + an `Initialize enums file` hint.
    `create_folder` depth-1 branch auto-writes the default
    `enums.yaml` next to the freshly-created project folder
    (zero new methods called for module / sub-folder creates).
    `_tree_children` filters `enums.yaml` out of
    project-root listings so the file never surfaces in the
    tree or folder views — its only UI surface is the editor's
    init action. `write_project_enums` was deliberately
    **deferred** to the CRUD-UI follow-up (no caller in v1).
  - **S3 — HTTP + editor UI** (`04-folder-crud`,
    `05-testcase-crud`, `08-file-editor`). Two new routes in
    `root/app/server.py`:
    `GET /api/enums/<project>` (200 parsed dict / 404 if file
    missing / 422 `enums_parse_error` if malformed) and
    `POST /api/enums/<project>` (201 with default body / 409
    `name_conflict` if already initialised / 404 if project
    missing). New `Enums` section in
    `root/app/templates/file_editor.html` between the feature
    tags row and the background card, with four id'd
    sub-elements: `feature-enums-missing` (legacy / pre-init
    state hosting the `Initialize enums file` button +
    inline error region), `feature-enums-empty` (empty-vocab
    hint), `feature-enums-pickers` (dynamic
    `<select id="feature-enum-<kind>">` rows), and
    `feature-enums-orphans` (amber `(kind, key)` badges with
    per-row `Clear` action). JS controller (`tmsEditor` in
    `root/app/static/app.js`) gained a module-level
    `_vocabCache` keyed by project (Promise-valued, shared
    across editor mounts so file navigation within a project
    never re-fetches); per-mount state slots
    `enumsProject` / `enumsStatus` / `enumsVocab` /
    `enumsMessage`; async `_loadEnums()` with a stale-fetch
    guard (resolves drop their result if the editor has
    navigated to a different file); `renderEnums()` wired
    into `renderStructured()` so SSE silent-reload + tab-
    discard paths re-render; `_buildEnumPicker()` rendering
    one `<select>` per kind with `— not set —` as the first
    option (key-empty kinds render disabled with an
    "edit `enums.yaml`" hint); `_renderEnumOrphans()`
    implementing the spec's exact orphan join
    (`kind ∉ vocab` OR `key ∉ vocab[kind]`);
    `wireEnumsInit()` + `_initEnumsFile()` for the POST flow,
    hydrating `_vocabCache[project]` from the 201 body so a
    subsequent re-open does not re-fetch. Save already
    JSON-stringifies `state.feature` whole, so the new
    `enums` map travels over PATCH `/api/files/<p>` without
    any save-path edit — the backend cross-check rejects
    unknowns with 422 (currently surfaced via the editor's
    shared `alert("Save failed: …")`).
  - **Operational notes**: enums vocab fetches are
    **fetch-once-per-(project, session)**; manual hand-edits
    to `enums.yaml` take effect on the next page reload by
    design (SSE-driven live refresh is the deferred
    CRUD-UI follow-up). Project create is **not atomic
    across folder + enums file** — if the process is killed
    between the `mkdir` and the byte write, the editor falls
    back to the missing-state UI and the user clicks
    `Initialize enums file` to reconcile.
  - **Touched**: `root/app/errors.py` (new `EnumsParseError`);
    `root/app/models.py` (`Feature.enums` field +
    validation); `root/app/gherkin_io.py` (pre-parse scan +
    serializer emit); `root/app/storage.py` (constants,
    mtime cache, `read_project_enums`,
    `init_project_enums`, `_invalidate_enums_cache`,
    `_parse_project_enums`, `_cross_check_enums`,
    `_tree_children` filter, `create_folder` auto-init);
    `root/app/server.py` (two routes + `EnumsParseError`
    handler); `root/app/templates/file_editor.html` (Enums
    section scaffold); `root/app/static/app.js` (controller
    extensions + init button). `pyyaml` was already pinned
    for the test-run feature; no new dependency.
  - **Verified** via 9 standalone smoke scripts in
    `root/.smoke-scratch/` (3 `s11_*` model / parser /
    serializer, 3 `s12_*` storage + handler + cache, 3
    `s13_*` HTTP + scaffold + JS-controller-wires), totalling
    68 PASS assertions. The JS-controller smoke is a static
    inspection of `app.js` for the new methods, wiring, and
    URL patterns — end-to-end picker UX (orphan render,
    `Clear` action, save round-trip, missing → init flow,
    cross-file cache reuse) is covered by a manual UX
    checklist, mirroring the standing Phase-2 lock-in for
    JS-heavy surfaces. Existing smokes (file editor save
    round-trip, tombstone render, tree / folder hiding,
    run-group POST flows) regression-pass.
  - **Surface for follow-up**: a per-project CRUD UI for
    `enums.yaml` (with SSE-driven live refresh + cascade
    rename across affected `.feature` files) is the obvious
    next step once teams hit the limits of the
    hand-edit-the-YAML flow — captured under
    `root/IN-PROGRESS.md` as
    *"Investigate: per-project enums.yaml CRUD UI"*. The
    `quality-report` Investigate item is unblocked
    (bucketing dimension = `Feature.enums["components"]`);
    new enum kinds ship with **zero code change** (e.g.
    `priorities`, `sprint`) — only product behaviour layered
    on a specific kind is new work.

- **New feature: quality report (typed `report/` area, live
  recomputation, four report types, Reports sidebar tab).**
  _Investigate signed off Jun 9, 2026; Do phase shipped Jun 10,
  2026 in three slices (S1 model + aggregation, S2 storage,
  S3 HTTP + UI)._
  - **Spec**: `root/specs/features/12-feature-quality-report-NEW.md`
    (forward-looking Investigate spec; Q1–Q-decisions resolved
    before the Do phase). Aggregated summary entry in
    `root/specs/features/00-summary.md` § 12. Four report types:
    `enum_ranking`, `tag_ranking`, `case_trend` (run-set sourced,
    mutable) and `tag_inventory` (folder-scope sourced, static).
    Reports persist in a reserved `<project>/report/` typed area;
    results are **recomputed live on every render** — no caching,
    no result persistence.
  - **S1 — Model + aggregation engine** (`app/models.py`,
    `app/reporting.py`). New `REPORT_TYPES` constant + `Report`
    dataclass + `validate_report` (type discriminator, per-type
    config presence, run-set vs. scope shape exclusivity, ≤ 10
    runs). New pure `reporting.compute_report(storage, project,
    report)` dispatching to `_enum_ranking` / `_tag_ranking` /
    `_case_trend` / `_tag_inventory`, all returning the common
    envelope `{type, title, created_at, total, buckets|trend,
    warnings, params}`. Tolerant by design: missing / malformed
    run paths and missing scope folders are dropped from the
    computation and surfaced as `warnings` rather than crashing;
    an empty run set yields `total=0` + empty buckets, no warning.
    Enum-ranking counts **distinct cases** and resolves keys to
    `enums.yaml` labels; synthetic `unset` / `removed` buckets
    reconcile the count. Tag-ranking buckets are multi-valued
    (a case can land in many) plus an `untagged` bucket, so the
    percentage total can exceed 100%. Case-trend orders columns
    by run `created_at`, renders an absent-run placeholder, and
    flags tombstoned (removed) cases. Storage gained the
    `iter_feature_paths` helper backing the feature scans.
  - **S2 — Storage + persistence + reserved area + cross-checks**
    (`app/storage.py`, `app/errors.py`). New `ReportParseError`
    (422 `report_parse_error`) alongside `RunParseError` /
    `EnumsParseError`. `_REPORT_AREA = "report"` added to
    `RESERVED_DEPTH2_NAMES` so the generic `create_folder` rejects
    a hand-made `report/` and `_tree_children` / `list_folder`
    hide it from the directory tree and project module tables —
    its only surface is the Reports tab. `_normalize_report_filename`
    (`.yaml` suffix), `_report_segments`, and the full CRUD set:
    `create_report`, `read_report`, `write_report`, `delete_report`,
    `list_reports` (best-effort, skips parse errors), and
    `list_report_tree` (aggregates the flat `report/` subtree across
    projects, mirroring `list_test_run_tree`). Write-time
    cross-checks reject unknown enum `kind`, missing run / scope /
    case paths, and > 10 runs **before** writing anything; an empty
    run set is accepted. `read_report` wraps malformed YAML and
    non-mapping roots in `ReportParseError`.
  - **S3 — HTTP + UI** (`app/server.py`, `app/templates/`,
    `app/static/app.js`). Report API routes (`POST /api/reports`,
    `GET` list, `GET` / `PATCH` / `DELETE` on
    `/api/reports/<project>/<file_name>`) with `type` + `created_at`
    immutable on PATCH (422 otherwise); plus
    `@api.errorhandler(ReportParseError)` → 422. UI routes
    `GET /ui/reports-tree` (sidebar partial) and
    `GET /ui/report/<project>/<file_name>` (calls `compute_report`
    → per-type detail template, 404 if missing). New templates
    `reports_sidebar.html` (flat report leaves + new/refresh
    buttons + empty state) and `report_detail.html` (branches on
    `view.type`: ranking table with collapsible per-bucket case
    lists, trend timeline with status-coloured cells, inventory
    carrying/not-carrying split, tolerant warnings, empty states).
    `base.html` gained the third **Reports** sidebar tab + lazy
    pane and injects `TMS_RUN_RESULTS`. `app.js` extended
    `tmsSwitchSidebarTab`; added `tmsActivateReportsPane`,
    `tmsCreateReport` (per-type config modal), `tmsBuildRunPicker`,
    `tmsAddReportRuns`, and `tmsEditReportScope`.
  - **As-built deltas vs. the original S3 cut** (folded into the
    spec's S3 checklist before deletion): added
    `GET /api/runs/<project>` — a flat newest-first run list across
    all groups, backing the run picker's `run_paths` source (not in
    the original surface list); `case_trend` creation uses a single
    native `<select>` rather than the checkbox `tmsBuildCasePicker`
    (single-select reads cleaner as a select); the run picker is a
    **flat filter + group column** rather than a project→group tree
    (same selection power, less machinery); the lazy Reports pane
    re-GETs on `sse:change` for **all** report types once mounted;
    `tag_inventory` detail exposes an **Edit scope** action
    (`tmsEditReportScope`, folder `<select>` → PATCH `scope`);
    trend result cells are colour-coded by status.
  - **Verified** via 17 standalone smoke scripts in
    `root/.smoke-scratch/feature-12/` (`F12_01`–`F12_07` +
    `F12_10`–`F12_13` aggregation / validation / storage /
    parse-error / cross-check / reserved-area; `F12_20`–`F12_25`
    HTTP + UI: create→navigate, sidebar aggregation, per-type
    detail render, add/remove-runs PATCH + immutability,
    `app.js`/template JS wiring, `/api/runs/<project>` envelope +
    scope PATCH). JS-heavy surfaces are covered by the standing
    static-inspection + render-and-grep convention (no
    Playwright runtime). Full suite:
    **236/236 PASS / 0 FAIL** (was 219 before this feature's 17).
  - **Surface for follow-up**: report types are recomputed live, so
    new enum kinds and tags flow in with zero report-file edits;
    result caching / snapshotting and richer chart rendering are
    the obvious next steps once report sets grow.

- **Tech: restructure & decentralize the codebase.** _Investigate +
  Plan + Do shipped Jun 10, 2026 in four behaviour-preserving slices;
  spec `root/specs/tech/01-tech-restructure-NEW.md` (the first
  `/specs/tech` initiative)._
  - **Why**: four files had grown large enough that any one change
    forced scanning unrelated logic — `app/static/app.js` (3554 lines),
    `app/storage.py` (2258), `app/server.py` (968), `app/models.py`
    (753). Goal: split each into smaller single-purpose units behind an
    **unchanged public surface** (same HTTP routes, on-disk behaviour,
    and DOM behaviour). Verified by the smoke suite staying green after
    every slice.
  - **Slice 1 — `models.py` → `root/app/models/` package**:
    `_common.py` (shared constants + `_is_single_line`), `_feature.py`,
    `_run.py`, `_report.py`; `__init__.py` re-exports the full surface
    (incl. the `_is_valid_tag` private a smoke imports). The `_common`
    leaf keeps submodules acyclic (star, not chain). Old `models.py`
    deleted.
  - **Slice 2 — `server.py` → `root/app/server/` package**: `_shared.py`
    (defines the `api` + `ui` blueprints + cross-route helpers +
    `_folder_crumbs`), eight `routes_*.py` (tree / folders / files /
    runs / reports / search / enums / ui), `errors.py` (12 handlers).
    `__init__.py` imports every route module for its registration side
    effects and re-exports `api` / `ui` / `_folder_crumbs`. **URL map
    stayed byte-identical at 47 rules** (handler + blueprint names are
    verbatim). Old `server.py` deleted.
  - **Slice 3 — `storage.py` → `root/app/storage/` package**: `_core.py`
    (constants + free functions + `_PathLock` + a `_StorageBase` holding
    init / path discipline / locking / self-write / `_atomic_write_bytes`)
    plus seven mixins (`_listing`, `_features`, `_enums`, `_search`,
    `_folders`, `_runs`, `_reports`) composed into `Storage` in
    `__init__.py`. Each mixin imports only `_core` + stdlib + sibling app
    modules (acyclic); cross-area calls resolve at runtime on the composed
    instance. Two atomic-write smokes monkeypatch `app.storage.os.replace`/
    `.fsync` — preserved with **zero smoke churn** by re-exporting `os` on
    the package (shared singleton, so the patch still reaches
    `_core._atomic_write_bytes`). Old `storage.py` deleted.
  - **Slice 4 — `app.js` → nine ordered global scripts**: split by
    contiguous source ranges into `01_tree.js`, `02_sidebar.js`,
    `03_folder_actions.js`, `04_run_create.js`, `05_report_flows.js`,
    `06_run_editor.js`, `07_util_search.js`, `08_file_editor.js`,
    `09_bootstrap.js` (verbatim — no body edits; symbol inventory verified
    identical). No build step / ES modules — they stay classic globals
    loaded by `base.html` in `NN_` order with `09_bootstrap.js` **last**
    (it registers the listeners + `tmsBootShell`, which call functions
    defined earlier). The `NN_` prefix also makes a sorted glob of
    `static/*.js` reproduce the original source order, which the
    static-inspection smokes rely on. Old `app.js` deleted.
  - **Smoke impact**: ~30 JS source-inspection smokes repointed from
    reading `app/static/app.js` to a glob-concat of `static/*.js` (the
    `.smoke-scratch/README.md` "JS source-inspection" idiom documents
    why); `run.py` extended to also discover `{feature,tech}-*` dirs +
    `[FT]\d+_\d+` files; a new guard `tech-01/T01_01_script_order.py`
    asserts the `<script>` load order + that every `static/NN_*.js` is
    referenced. No assertion was deleted or weakened.
  - **Verified**: full suite **237/237 PASS / 0 FAIL** (236 + the new
    `tech-01` guard), `node --check` clean on all nine JS files,
    `create_app()` boots with the URL map unchanged at 47 rules, and
    `import app.storage` has no cycle. JS **runtime** behaviour (no
    build step to catch load-order / `ReferenceError` mistakes) was
    confirmed by a manual browser pass owned by the user.
  - **Spec-pointer follow-through**: every `## Source file` /
    relationship-section pointer that named the now-deleted monoliths was
    updated to the new package / submodule / `NN_*.js` paths across
    `root/specs/features/01,02,04,05,06,07,08,09,10,11,12` +
    `00-summary.md`, and the `root/specs/rules/tech-rule.md` module-
    boundary statements.

- **Tech: UI/UX styling & detailing enhancements (E1–E5).** _Investigate +
  Plan + Do shipped Jun 10, 2026; spec
  `root/specs/tech/02-tech-ui-styling-enhancement-NEW.md`. Five Must-have
  presentational/freshness polish items, each investigated + built
  individually. No data-model, on-disk, or HTTP-contract change._
  - **Palette foundation (drives E3 + E4)**: a single source-of-truth status
    palette as five `[data-status]` attribute selectors in
    `root/app/static/app.css` (no Tailwind build → raw CSS is the only
    cross-consumer home). `PASSED` green / `FAILED` red / `EXECUTING` blue /
    `SKIPPED` **purple** / `PENDING` orange. Consumers attach only the
    `data-status` hook, never a colour.
  - **E1 — Result column width**: widened the run-editor results table and the
    report `case_trend` table `Result` header from `w-32` to `w-40` so the
    longest status (`EXECUTING`) never clips/wraps (`run_editor.html`,
    `report_detail.html`).
  - **E2 — folder grouping (run editor)**: `run_editor.html` groups
    `run.results` by folder server-side (first-seen folder order, within-folder
    order preserved), emits one plain `run-group-head` row per folder, and
    renders each result row **filename-only** (the masked folder span is
    dropped — the heading now carries the folder). `06_run_editor.js`: result
    reads scoped to `tr[data-file-path]`; "+ Add case" lands rows in their
    folder group via `_insertResultRow` (cloning a `run-group-head-template`
    when the folder is new); remove drops an empty heading; a new
    `_compareJson` projection sorts by `file_path` so dirty / external-change
    comparisons stay order-insensitive while **Save** still persists grouped
    DOM order. _Post-ship extension (user feedback): the same grouping idiom
    was applied to the **ranking-report bucket case lists**
    (`report_detail.html`, shared by `enum_ranking` / `tag_ranking` /
    `tag_inventory`) — each bucket now groups its cases by folder with a
    filename-only list (server-side Jinja only; no `reporting.py` change;
    smoke `T02_08`). Folder headings on **both** surfaces (report buckets +
    run-editor `run-group-head` rows) render as a **badge** — bold dark text
    on a slate-200 pill — to lift contrast against the muted case filenames;
    `06_run_editor.js:_createGroupHead` writes the badge `<span>` so
    JS-created headings match._
  - **E3 — run-editor Result colour**: the `Result` `<select>` carries
    `data-status` (server-rendered for live rows; kept in lock-step by JS on
    `change` and on clone), so the shared palette colours the closed select.
  - **E4 — report detail consistency + highlight**: dropped the inline
    `result_colors` Jinja map in favour of the shared `data-status` palette on
    the `case_trend` Result cell (em-dash keeps its muted fallback);
    bold-emphasised the key factors (status / kind / case / run-count / tag /
    scope) and palette-coloured the **enum-ranking** `status` param
    (`report_detail.html`).
  - **E5 — auto-refresh tree on create**: the watcher suppresses `sse:change`
    for in-app self-writes, so new artifacts didn't appear until an external
    change / manual Refresh. Added `tmsRefreshTreePane(paneId)` in
    `02_sidebar.js` (re-GETs only a **mounted** pane; unmounted lazy panes load
    fresh on first open) and wired each create flow to refresh **only its own
    tab's tree** (decision D4): case → `#tree-pane` (`03_folder_actions.js`),
    run → `#test-run-pane` (`04_run_create.js`), report → `#reports-pane`
    (`05_report_flows.js`).
  - **Smoke impact**: 8 new smokes under `.smoke-scratch/tech-02/`
    (`T02_01` palette source · `T02_02` E1 width · `T02_03` E3 select hook ·
    `T02_04` E4 palette+emphasis · `T02_05` E2 server grouping · `T02_06` E2
    JS touch-points · `T02_07` E5 create-refresh · `T02_08` E2 report-bucket
    grouping). Six feature-10 smokes
    updated for the intentional E2 structural change (filename-only rows +
    order-insensitive compare): `F10_31`/`F10_32`/`F10_33` (folder span
    dropped → filename-only + heading) and `F10_67`/`F10_76`/`F10_69`
    (`JSON.stringify` baseline/disk projection → `_compareJson`); `F12_22`
    re-pointed from inline `text-rose-600` to `data-status="FAILED"`. No
    assertion was weakened — each preserved its original intent.
  - **Verified**: full suite **245/245 PASS / 0 FAIL** (237 + 8 new tech-02).

## Could have

- **Per-project `enums.yaml` CRUD UI** (`specs/features/13-feature-enums-crud-NEW.md`).
  Shipped the full create/edit/rename/clear surface for a project's enum
  vocabulary, replacing the prior hand-edit-the-YAML-only flow. Decisions
  D1–D12 resolved up front (sign-offs: D3 block-in-use, D5 sidebar tab, D11
  clear=block, D2 verbs); built slice by slice S1→S5.
  - **S1 — storage write + canonical serializer** (`app/storage/_enums.py`):
    `write_project_enums(project, data)` round-trips the payload through
    `_parse_project_enums` **before** writing (bad payload 422s untouched),
    then atomic-write + `_mark_write` + cache-invalidate;
    `_serialize_project_enums` emits canonical block YAML (insertion order
    preserved, empty kind byte-matches the seed `components:\n`, labels
    PyYAML-quoted so YAML-special content round-trips). Legacy projects (no
    file) raise `FileNotFoundError` → 404.
  - **S2 — whole-document API + usage guard**: `count_enum_key_usage` (count
    + ≤5 sample paths); in-use removal guard `_block_in_use_removals` raises
    the new `EnumInUseError` (HTTP **409** `enum_in_use`, details
    `{kind,key,count,sample}`) so a `PUT` can never silently orphan a case
    (D3). Routes: `PUT /api/enums/<project>`, `GET /api/enums/<project>/usage`.
  - **S3 — rename + cascade**: `rename_enum_key` is alias-first + crash-safe
    (D4) under a project-scoped lock: validate → dry-run-parse every feature
    (abort before any write) → write alias (both keys) → rewrite referencing
    features → drop `old_key` in its slot. Reuses `write_project_enums` for
    both YAML writes (the final drop passes the in-use guard naturally since
    usage is already 0 — no bypass needed). Route: `POST .../rename` →
    `{renamed:<count>}`; `new_key` conflict → 409, unknown/invalid → 422,
    unparseable feature → 422 `parse_error`.
  - **S4 — Enums sidebar tab + manager view + Clear + SSE**: 4th sidebar tab
    (`base.html`, `02_sidebar.js` `tmsActivateEnumsPane`), `enums_sidebar.html`
    (projects via `Storage.list_root()` + legacy "no file" badge),
    `enums_manager.html` + `08_enums_manager.js` (`tmsEnumsManager`: add/remove
    kind+entry, edit label, Save=PUT, Rename, Clear, Initialize), routes
    `GET /ui/enums-tree` + `GET /ui/enums/<project>`. `clear_project_enums`
    (D11) resets to the seed but **blocks** with a detailed 409 if any case
    is still in use (never deletes the file, D8). Editor wiring (D6):
    `08_file_editor.js` gains an `openEnumsManager()` deep-link and refreshes
    its vocab cache on `sse:change` (`_refreshEnumsFromDisk`); the manager
    keeps `tmsEditor._vocabCache` in lock-step on writes. Users clear a case's
    enum via the existing picker "— not set —" / orphan Clear affordance.
  - **S5 — one-time backfill** (`scripts/backfill_enums.py`): idempotent CLI
    that initialises `enums.yaml` for every legacy project (skips initialised
    ones via `NameConflictError`); `--data-root` defaults to `./project`.
    Auto-init on project create (D9) and one-file-per-project (D12) were
    already shipped — pinned by a regression smoke.
  - **Smoke impact**: 17 new smokes `.smoke-scratch/feature-13/`
    (`F13_01`/`02` write+serialize · `F13_03`–`06` PUT/usage/in-use ·
    `F13_07`–`10` rename cascade/dry-run/alias/errors · `F13_11`–`15` tab +
    manager + clear + SSE wiring · `F13_16` backfill · `F13_17` D9 auto-init).
    `08_enums_manager.js` placed before `08_file_editor.js` to keep the
    `base.html` script tags in sorted `NN_` order (tech-01 invariant).
  - **Verified**: full suite **262/262 PASS / 0 FAIL** (245 + 17 new).

## Should have

- **Shorten the test-case directory path in the picker modals** (Jun 11, 2026;
  filed same day in `IN-PROGRESS.md`). The project is already chosen in the
  create-report / create-run / add-case modals, so the test-case pickers
  repeated the redundant `<project>/` prefix on every row. Now they show the
  path from the **module level down**, while the stored value stays the full
  data-root `path`.
  - `app/static/04_run_create.js`: `tmsFetchProjectFeaturePaths` now also
    derives `rel_path` / `rel_folder` (the `<project>/` prefix stripped;
    `rel_folder === ""` for a file directly under the project root). The full
    `folder_path` + the folder-then-file ASC sort are untouched (CP1/`F10_70`).
    `tmsBuildCasePicker` displays + filters on `rel_folder` (Folder column),
    keeping `tr.dataset.path = f.path` as the stored value — so the run
    editor's **+ Add test case** modal shortens.
  - `app/static/05_report_flows.js`: the `case_trend` Test-case `<select>`
    labels each option with `rel_path` while the option **value** stays the
    full `f.path` (the persisted `case_path`).
  - **Smoke impact**: 2 new static-inspection smokes — `F10_82`
    (picker shows `rel_folder`, value stays full path) and `F12_26`
    (`case_trend` labels with `rel_path`, value stays full path).
  - **`+ Add test case` button moved to the top of the Results table**
    (`app/templates/run_editor.html`): relocated from the bottom of the run
    editor into the `Results` header row (right-aligned). Wired by `id`, so
    behaviour is unchanged (`F10_16`/`F10_28` still pass).
  - **Verified**: full suite **264/264 PASS / 0 FAIL** (262 + 2 new); both
    shortened pickers confirmed live in the browser after reload (the initial
    "still full path" report was stale in-memory JS in the open tab).

- **Confirm modal actions with a keyboard shortcut** (Jun 11, 2026; filed
  same day in `IN-PROGRESS.md`). Every in-app create / update / add modal is
  built by the single `tmsOpenModal` primitive, so the shortcut was added
  once there and all modals inherit it — Create test run, Create report,
  Add/remove runs, Edit scope, Create test case, Add test cases, Move test
  case. (The folder/file/enum `window.prompt` flows are native dialogs and
  already Enter-capable; out of scope.)
  - `app/static/03_folder_actions.js`: the confirm action was factored into a
    shared `triggerConfirm()` that respects the disabled gate, skips
    information-only modals (`!hasConfirm`), and guards against double-submit
    with a `confirmInFlight` flag — used by both the Confirm button click and
    the keyboard path. The modal's document-level `keydown` handler now fires
    `triggerConfirm()` on **macOS `Cmd+Return`** (`e.metaKey && e.key === "Enter"`,
    with `preventDefault`), alongside the existing Escape-to-close.
  - **Scope note**: keyboard shortcut is `Cmd+Return` only, per the backlog
    spec (clicking the primary button is unchanged on all OSes). `Ctrl+Enter`
    for Windows/Linux was deliberately not added.
  - **Smoke impact**: 1 new static-inspection smoke `tech-03/T03_01`
    (shared guarded confirm path + Cmd+Return wiring; Escape regression).
  - **Verified**: full suite **265/265 PASS / 0 FAIL** (264 + 1 new).

- **Allow a dash (`-`) in enum entry keys** (Jun 11, 2026; filed same day in
  `IN-PROGRESS.md`). A natural key like `knowledge-base` was rejected at every
  layer because keys reused the strict identifier regex. Relaxed **keys only**;
  enum **kinds** (and the `enum_ranking` report `kind`) stay strict. Built
  PDCA: plan → do → check (suite green) → act.
  - **New validator** `ENUM_KEY_RE = ^[A-Za-z_][A-Za-z0-9_-]*$`
    (`app/models/_common.py`), exported from `app/models`. Distinct from
    `ENUM_IDENTIFIER_RE` (unchanged, still used for kinds).
  - **Server key call sites switched to `ENUM_KEY_RE`**: `Feature.enums`
    validation (`app/models/_feature.py`), the `enums.yaml` schema parser +
    rename `new_key` guard (`app/storage/_enums.py`), and the on-disk
    `# enum.<kind>: <key>` directive parser (`app/gherkin_io.py`). Kind call
    sites and `enum_ranking` `report.kind` (`app/models/_report.py`) left on
    `ENUM_IDENTIFIER_RE`.
  - **Client** (`app/static/08_enums_manager.js`): added `ENUM_KEY_RE` for the
    add-entry prompt; `_addKind` keeps `ENUM_ID_RE`. (Rename has no client-side
    regex — the server now validates `new_key` with `ENUM_KEY_RE`.)
  - **Smoke impact**: 1 new end-to-end smoke `feature-13/F13_18`
    (PUT/GET round-trip · validate + serialise/parse · rename cascade
    dashed→dashed · client `ENUM_KEY_RE` wiring). Re-pinned 6 boundary smokes
    that used `bad-key` as the canonical invalid key to a dotted key
    (`F11_01`, `F11_02`, `F11_05`, `F13_02`, `F13_03`, `F13_10`) and added
    positive dashed-key coverage to the model + parser + schema smokes.
  - **Verified**: full suite **266/266 PASS / 0 FAIL** (265 + 1 new).

- **Move test case modal — project/folder defaults + tree refresh**
  (Jun 11, 2026; filed same day in `IN-PROGRESS.md`). The move picker was a
  single destination `<select>` spanning every project, with no default and a
  full-path label per option. Reworked `tmsEditor.move()`
  (`app/static/08_file_editor.js`) into a two-step picker:
  - **Project select** defaults to the source file's current project
    (`segments[0]`); the tree walker now also collects depth-1 folders as the
    project list.
  - **Folder select** is scoped to the chosen project and repopulates when the
    project changes; option **labels are project-relative** (prefix stripped,
    e.g. `moduleA/sub`) while the option **value stays the full path** the
    `PATCH /api/files/<p>/move` contract needs. The current parent is still
    rendered disabled with a `(current)` marker, and the prompt option keeps
    Confirm gated until a real destination is picked.
  - **Deterministic tree refresh on success**: added
    `tmsRefreshTreePane("tree-pane")` after a successful move (was relying
    solely on the server's SSE `change` event), mirroring `tmsCreateFile`'s
    E5 refresh.
  - **Unchanged**: dirty-buffer confirm, the `PATCH .../move` endpoint/verb/
    body (`{parent: destParent}`), and the post-move navigation to the file's
    new path.
  - **Smoke impact**: extended `feature-08/F08_16_move.py` with **MV6**
    (project default), **MV7** (project-scoped, relative label, full-path
    value), **MV8** (explicit tree refresh); added MV6–MV8 rows to
    `feature-08/COVERAGE.md`. MV1–MV5 invariants preserved.
  - **Verified**: full suite **266/266 PASS / 0 FAIL** (no net file count
    change — MV6–MV8 fold into the existing move smoke).

- **Search results grouped by project (collapsible)** (Jun 11, 2026; filed
  same day in `IN-PROGRESS.md`). The ≥2-hit search view was a single flat
  table spanning every project with full project-prefixed paths. Reworked the
  list into collapsed-by-default per-project groups:
  - **Server-side grouping** in `ui_search` (`app/server/routes_ui.py`):
    hits are bucketed by their first path segment (project), **projects
    sorted**, hit order within a project preserved, and each hit gains a
    `rel_path` (project prefix stripped) for display. The route now passes a
    `groups` list (`[{project, hits}]`) alongside the existing `hits`.
  - **Template** (`app/templates/search_results.html`): the ≥2-hit branch
    renders one `<details>` per group (no `open` ⇒ **collapsed by default**),
    a `<summary>` with the project name + a hit-count badge, and a table whose
    File column shows `hit.rel_path` (full path in `title`). The 0-hit and
    1-hit (auto-navigate) variants are unchanged.
  - **Navigation unchanged**: each row still `hx-get`s `/ui/file/<full_path>`
    into `#main-pane` — only the *displayed* path is shortened.
  - **Smoke impact**: 1 new smoke `feature-09/F09_20_results_grouped.py`
    (UX5: collapsed sorted per-project groups + count badge; rel-path display
    with full-path `hx-get`); added a UX5 row to `feature-09/COVERAGE.md`.
    The UX4 list-view smoke (`F09_19`) still passes unchanged.
  - **Verified**: full suite **267/267 PASS / 0 FAIL** (266 + 1 new).

- **Folder-detail Tags column empty for feature-level tags** (Jun 11, 2026;
  investigated + approved same day). The folder test-case list rendered no
  tags for cases tagged at the **feature level** (the common case — the
  editor exposes a *Feature tags* field and most `.feature` files carry their
  tags above the `Feature:` line).
  - **Root cause**: `Storage.list_folder` (`app/storage/_listing.py`) built
    each row's `tags` from `feature.scenario.tags` only, ignoring
    `feature.tags`. This diverged from the domain convention `_case_tags`
    (D10, `app/reporting.py`), which is the union of both levels.
  - **Fix**: the listing now emits the order-preserving, de-duped **union**
    `list(dict.fromkeys([*feature.tags, *feature.scenario.tags]))`.
  - **Smoke impact**: re-pinned `feature-07/F07_04c_tags_column.py` (FT3) —
    it previously placed tags on the Scenario line to satisfy the old
    scenario-only behavior; it now seeds a feature-level `@regression` plus
    scenario-level `@smoke @critical` and asserts all three chips render.
    Updated the FT3 row + per-rule note in `feature-07/COVERAGE.md`.
  - **Verified**: full suite **267/267 PASS / 0 FAIL**.

- **Search-by-tag ignored feature-level tags** (Jun 11, 2026). Tag-mode
  search (`match=tag`) already did a **substring (contains)** match, but it
  only looked at `Scenario.tags`. Test cases tagged at the **feature level**
  (the common case) returned no hits at all — e.g. `search("demo", match=tag)`
  found nothing despite `@demo` on the `Feature:` line.
  - **Root cause**: `Storage.search` tag branch iterated
    `feature.scenario.tags` only (`app/storage/_search.py`).
  - **Fix**: the tag branch now substring-matches each tag in the
    order-preserving, de-duped **union** of `feature.tags` + `feature.scenario.tags`
    (D10) — `dict.fromkeys([*feature.tags, *feature.scenario.tags])`. A tag
    carried at both levels still yields a single hit; substring "contains"
    semantics are unchanged.
  - **Smoke impact**: extended `feature-09/F09_05_match_tag.py` (ST3) to pin
    that a purely feature-level tag is searchable and that a both-levels tag
    de-dupes to one hit; updated the ST3 row + per-file note in
    `feature-09/COVERAGE.md`.
  - **Verified**: full suite **267/267 PASS / 0 FAIL**.
