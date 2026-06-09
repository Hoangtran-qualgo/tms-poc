# 08 · File editor

_Retroactive spec: documents the as-shipped behaviour. Source files:_
_`app/templates/file_editor.html`, `app/static/app.js` (`tmsEditor`_
_object), `app/server.py` (`ui_file`, `_folder_crumbs`)._

## Summary

The single-pane editor for one `.feature` file. Combines two tabs
(structured + raw) over a shared in-memory buffer, applies a save-
click cleanup pass, supports manual reload, exposes Rename / Move /
Save buttons in the topbar, and reacts to out-of-band file changes
via SSE with a context-sensitive banner. Per-tab state lives in a
single `tmsEditor` object on the page; the structured tab is the
default and renders the canonical JSON shape returned by
`Feature.to_dict()`.

## Scope

In scope:

- The full editor template (`file_editor.html`) and its embedded
  JSON state payload.
- The `tmsEditor` JS controller: bootstrap, dirty tracking, tab
  switching, chip / step / examples grid / data-table rendering,
  save-click cleanup, save flow (structured PATCH and raw PUT
  paths), rename invocation, move invocation, manual reload,
  external-change banner.
- The `Saved` transient badge and dirty-buffer indicators.
- The `beforeunload` warning on dirty state.
- Breadcrumb rendering at any depth (via `_folder_crumbs`).

Out of scope:

- The HTTP / storage contracts the editor calls into (covered in
  `05-testcase-crud`).
- Parsing / serialising the Gherkin source (`01-gherkin-io`).
- The tree pane (`06-tree-pane`).
- Search (`09-search`).
- Unsupported-file rendering (handled by `ui_file` returning
  `unsupported.html`).

## Public surface

Route:

- `GET /ui/file/<path:p>` (`ui_file`) — for `.feature` files
  renders `file_editor.html` with `file_path`, `crumbs`,
  `file_name`, `feature = Feature.to_dict()`, `raw = read_raw()`.
  Non-`.feature` paths render `unsupported.html`. If the on-disk
  `.feature` fails to parse, `read_feature` raises
  `GherkinParseError`; the UI blueprint registers dedicated
  handlers only for `ValueError` (400) and `FileNotFoundError`
  (404), so a parse error falls through to the catch-all
  `Exception` handler and surfaces as a generic **500** error
  page (no editor scaffold). The 422 `parse_error` envelope is
  produced by the JSON API surface (`PUT /api/files/<p>/raw`), not
  this HTML route.

Template (`file_editor.html`):

- Topbar buttons (left → right): breadcrumb, dirty indicator
  (`#dirty-indicator`), Saved badge (`#saved-indicator`),
  `#btn-rename`, `#btn-move`, `#btn-reload`, `#btn-save`.
- Banner slot: `#editor-banner`, empty by default; populated by
  `tmsEditor._showBanner`.
- Tabs: `#tab-btn-structured`, `#tab-btn-raw`.
- Structured tab: feature description textarea, feature-tag
  chips, background card (with steps + `+ Add background step`),
  scenario card (kind toggle, name, tags chips, steps,
  examples).
- Raw tab: textarea, error display (`#raw-error`), `#btn-save-raw`.
- Embedded JSON payload (`#editor-data`, `type="application/json"`)
  with keys `path`, `file_name`, `feature`, `raw` — consumed by
  `tmsEditor.boot()` via `JSON.parse(textContent)`.

`tmsEditor` controller (`app/static/app.js`):

- Lifecycle: `boot()`, `_refreshFromDisk()`.
- Dirty / save UX: `markDirty(d)`, `updateSaveButton()`,
  `flashSaved()`, `_hideSavedBadge()`.
- Tab + render: `renderStructured()`, `renderRaw()`,
  `renderChips(prefix, list)`, `renderSteps(target, steps)`,
  `_renderStepDataTable(step, container, rerender)`,
  `renderExamplesSection()`, `_renderExamplesGrid(node, ex)`,
  grid helpers (`_makeGridCell`, `_autoSizeCell`,
  `_finalizeGridSizing`).
- Save flow: `cleanupBuffer()`, `save()`, `saveRaw()`.
- File operations: `rename()`, `move()`, `reload()`.
- External-change banner: `onExternalChange()`, `_showBanner({...})`,
  `_hideBanner()`.
- Step / table editing helpers: `addStep('background' |
  'scenario')`, `addExamplesBlock()`.

Wiring (`app/static/app.js`, bottom of file):

- `htmx:afterSwap` on `#main-pane` clears `tmsEditor.state` when
  the main pane swaps to anything other than the editor.
- `document.body.addEventListener("sse:change", ...)` calls
  `tmsEditor.onExternalChange()` whenever the page receives a
  `"change"` SSE event AND `tmsEditor.state` is non-null.

## Invariants & rules

**Bootstrap**

- `tmsBootEditor()` is called by `file_editor.html` after the
  partial is swapped in.
- `boot()` reads `#editor-data`, hydrates `state =
  {path, file_name, feature, raw, snapshotJson, snapshotRaw,
  dirty: false, tab: "structured"}`. The two snapshots
  (`snapshotJson` and `snapshotRaw`) drive external-change
  detection — see W6.

**Dirty tracking**

- Every editable widget calls `this.markDirty(true)` on change.
- `markDirty(d)` toggles `#dirty-indicator`, recomputes the Save
  button's enabled state, and clears the `Saved` badge so the two
  states never overlap.
- Save button is **disabled** when `Feature.description` is
  empty / whitespace-only (mirrors business rule).
- `beforeunload` warns when the buffer is dirty.

**Tab switching**

- `state.tab ∈ {"structured", "raw"}`. The visible content swaps
  but the underlying buffer (`state.feature` + `state.raw`)
  persists across tab switches IF the buffer is clean.
- If `state.dirty` when the user clicks the other tab,
  `switchTab` shows a browser `confirm("You have unsaved changes
  in the current tab. Switching tabs will discard them.
  Continue?")`. On Cancel the switch is aborted. On OK the
  buffer is reset to the snapshots (both `feature` and `raw`),
  `markDirty(false)`, both tabs re-render, then the switch
  proceeds. There is no merge — dirty edits in one tab cannot
  carry over.
- `save()` dispatches: if `state.tab === "raw"`, delegates to
  `saveRaw()` instead of structured PATCH.

**Save-click cleanup (`cleanupBuffer`)**

Runs before validation on the structured save path. Operations
applied in order:

1. Drop any step (background or scenario) whose `text` is
   empty / whitespace-only.
2. Drop any examples row consisting entirely of empty cells
   (header preserved).
3. For each step's `data_table`: if **every** row (header *and*
   body) is all-empty, set `data_table = null`. Otherwise keep
   the header and filter out any body rows that are all-empty.
   A header-with-content but zero remaining body rows stays as
   `[header]` (not null).
4. Outline-only refusal: if `kind === "outline"` and the
   scenario has zero examples *blocks* (`examples.length === 0`)
   after the row-filter pass, abort the save with a browser
   `alert("Cannot save: An outline must have at least one
   Examples block.")`. Outline blocks with empty rows (but with
   a header) are NOT rejected client-side — they pass
   `validate_feature` server-side because that check is on
   block count, not row count.

**Save flow — structured (`save`)**

1. If `state.tab === "raw"`, dispatch to `saveRaw()`.
2. Run `cleanupBuffer()`; on error, show a browser `alert(
   "Cannot save: …")` and abort. (Inline-style error display is
   only used by the raw tab via `#raw-error`.)
3. Re-render the steps + examples so the user sees the cleaned
   buffer.
4. PATCH `/api/files/<state.path>` with `JSON.stringify(
   state.feature)`.
5. On 2xx: `await _refreshFromDisk()` to capture the canonicalised
   on-disk version (refetches both `/api/files/<p>` and
   `/api/files/<p>/raw`, refreshes `state.feature`, `state.raw`,
   both snapshots, calls `markDirty(false)`, re-renders both
   tabs); then `flashSaved()` for the 1.5 s badge.
6. On non-2xx: show a browser `alert("Save failed: " + (server
   error message || statusText))`. Buffer stays dirty (no
   refresh, no `markDirty(false)`).

**Save flow — raw (`saveRaw`)**

1. `hideRawError()`. PUT `/api/files/<state.path>/raw` with
   `state.raw` as `text/plain`.
2. Server parses + re-serialises (canonicalises). On 422
   `parse_error` / `validation_error`, the JSON envelope includes
   `details.line` / `details.column` for parse errors;
   `showRawError` renders the formatted message inline at
   `#raw-error` (`"Line N, col M: <message>"` for parse errors;
   plain message otherwise).
3. On 2xx: `await _refreshFromDisk()` so the structured tab also
   reflects the canonical form; `flashSaved()`.

**Rename (`rename`)**

- Uses `window.prompt` (legacy v1 affordance; the file-create
  flow uses `tmsOpenModal`, rename does not).
- PATCH `/api/files/<p>/rename` with `{file_name}`.
- On success, navigates to `/ui/file/<newpath>` via
  `htmx.ajax(...)`.

**Move (`move`)**

- Confirms when `state.dirty`
  (`"Discard unsaved changes and move the file?"`).
- Fetches `/api/tree`, walks the result to collect every folder
  at depth `2..MAX_FOLDER_DEPTH`, opens a `tmsOpenModal` with a
  `<select>` (current parent disabled, prompt option keeps
  Confirm disabled until the user picks a real target).
- PATCH `/api/files/<p>/move` with `{parent}`.
- On success, navigates to the file at its new path via
  `htmx.ajax('GET', '/ui/file/<newpath>', ...)`.
- On failure, error renders inline in the modal so the user can
  correct + retry.

**Reload (`reload`)**

- Confirms when `state.dirty`
  (`"Discard unsaved changes and reload from disk?"`).
- Calls `_refreshFromDisk()` (shared with the post-save reload).
- Clears banner, raw-error region, lingering `Saved` badge.
- Failure surfaces via `alert("Reload failed: …")`.

**External-change banner (`onExternalChange`)**

Triggered by `document.body` listener on every `sse:change`,
provided `tmsEditor.state != null`. Three branches:

1. **File removed on disk** → red error banner: "This file was
   removed on disk." with `Discard` action only.
2. **File changed AND buffer NOT dirty** → silently overwrite
   snapshots + re-render; show a dismissable info banner: "File
   was updated externally; the editor reloaded."
3. **File changed AND buffer dirty** → amber warn banner: "File
   changed externally while you have unsaved changes." with two
   actions: `Reload (discard mine)` and `Keep editing`.

The save button is *not* explicitly disabled while the banner is
up — but the editor's own validation gates ensure the same effect
when the disk path is missing (Save returns 404 / 422 to the user
inline).

**`beforeunload`**

Browser-native confirm fires when `state.dirty == true`.

## Affects

- `05-testcase-crud`: the editor is the primary UI surface that
  invokes rename / move / save / save-raw routes. Every error
  envelope from those routes is rendered inside the editor.
- `01-gherkin-io`: the structured tab's `state.feature` is the
  canonical `Feature.to_dict()` shape; the raw tab's bytes feed
  the server-side `parse_feature` on save.
- `06-tree-pane`: shares the same SSE connection (page-level
  `sse-connect`). When a save succeeds on this tab, the tree on
  *other* tabs refreshes; on the writing tab, the tree refresh
  comes via post-save UI routing, not via SSE.
- `07-folder-views`: every feature row in a folder view opens the
  editor via `/ui/file/<path>`.

## Depends on

- `05-testcase-crud` for every HTTP route the editor calls.
- `01-gherkin-io` for the wire-shape contract on the structured
  tab.
- `03-watcher-and-sse` for the `sse:change` event that drives
  external-change detection.
- `app/static/app.js` modal primitive (`tmsOpenModal`) for the
  move folder-picker.
- HTMX 2.x for the post-save / post-move re-routes
  (`htmx.ajax(...)`); Tailwind CDN for layout.

## Surface for follow-up

- **Rename still uses `window.prompt`** — should migrate to
  `tmsOpenModal` for consistency with create and move. Pure
  cosmetic; no contract change.
- **No Delete / Duplicate buttons in the editor** — `05-testcase-
  crud` exposes both APIs; adding them here is the obvious next
  step (with dirty-buffer confirms + 204 idempotence handling for
  delete).
- **External-change banner ignores the file's parse state** —
  if the disk version becomes unparseable mid-edit, the editor
  silently surfaces the parse error on the next reload attempt
  rather than warning proactively.
- `10-feature-test-run` (shipped) links runs to test cases by
  external `file_path` but chose the **tombstone-on-render** path,
  so the file editor's rename / move / delete handlers need **no**
  coordination with run files — the run editor recomputes the
  `missing` flag per row on every render. The flip side: rename a
  feature file and any open run referencing it goes tombstoned
  silently until the user notices on the next render.
- Multi-tab editing of the same file is technically permitted but
  the conflict policy (last-write-wins) is silent — no banner
  warns the loser.

## Acceptance criteria

- Opening a parseable `.feature` file shows the structured tab by
  default, populated from `Feature.to_dict()`, with `Save`
  disabled until the description is non-empty.
- Editing any field toggles the dirty indicator on; clearing the
  field back to its original value leaves the indicator on (no
  deep equality check — `markDirty` is set-and-forget).
- A structured save on a buffer with an empty step text drops
  that step silently and writes the cleaned result.
- Attempting to save an outline-kind scenario after cleanup has
  removed every examples block (`examples.length === 0`) shows a
  browser `alert("Cannot save: An outline must have at least one
  Examples block.")` and aborts.
- Switching tabs with a dirty buffer prompts a `confirm` and
  discards (resets to snapshots) on OK.
- Raw save of a file with a parse error returns 422 and renders
  the message at `#raw-error`; buffer remains dirty.
- After a successful save, the `Saved` badge appears for ~1.5 s
  then disappears; the next dirty edit clears it immediately.
- External rename of the open file with a clean buffer triggers
  the "updated externally" info banner and silently reloads the
  editor.
- External delete of the open file triggers the red "removed"
  banner; the buffer remains in memory and the user can copy
  values out before discarding.
- Manual reload with a dirty buffer prompts to confirm before
  discarding.
- Move success navigates the editor to the new path; failure
  keeps the modal open with the server's error inline.
