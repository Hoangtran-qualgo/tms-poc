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
