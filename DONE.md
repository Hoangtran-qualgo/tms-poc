# Done backlog

Items fixed during v1 manual verification.

## Must have

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
