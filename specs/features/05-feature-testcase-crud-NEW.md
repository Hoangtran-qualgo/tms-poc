# 05 · Test case CRUD

_Retroactive spec: documents the as-shipped behaviour. Source files:_
_`app/server/routes_files.py` (file routes), `app/storage/_features.py`_
_(file methods; moves + duplicates in `_folders.py`), `app/static/_
_03_folder_actions.js` (`tmsCreateFile`) + `08_file_editor.js`_
_(`tmsEditor.move/rename`), `app/templates/file_editor.html` (topbar_
_buttons), `app/templates/folder_*.html` (create buttons)._

## Summary

CRUD lifecycle for `.feature` files: create, read (structured +
raw), update (structured + raw), rename, move, duplicate, delete.
The contract is intentionally split into one storage method per
operation and one HTTP route per operation so the UI can compose
flows (e.g. "rename then save" in the editor) from primitives.

## Scope

In scope:

- Create a `.feature` file at any module-or-deeper folder
  (`2..10` depth) with a non-empty `description`. A placeholder
  scenario is injected so the file is immediately editable.
- Read a file as either canonical JSON (`GET /api/files/<p>`) or
  raw source (`GET /api/files/<p>/raw`).
- Update via canonical JSON (`PATCH /api/files/<p>`) or raw
  (`PUT /api/files/<p>/raw`). Both paths run the full
  parse → validate → serialize → atomic-write cycle, so raw input
  is canonicalised on save.
- Rename, move, duplicate (all same-parent for rename/duplicate;
  cross-folder for move).
- Delete (idempotent, 204).

Out of scope:

- The editor experience itself — dirty tracking, structured tab,
  raw tab, save flow, banners. That's `08-file-editor`.
- Search over file contents — `09-search`.
- File listing in folder views — `07-folder-views` consumes
  `Storage.list_folder` output.

## Public surface

HTTP routes (Flask blueprint `api`):

- `POST /api/files` — body `{ file_name, description, parent }`.
  `parent` segments must be `2..10`; non-empty `description` is
  required.
- `GET /api/files/<path:p>` — returns `Feature.to_dict()`.
  Non-`.feature` extensions → 415 `unsupported_type`.
- `PATCH /api/files/<path:p>` — body matches `Feature.from_dict`
  shape. Validates + serializes + atomic-writes.
- `DELETE /api/files/<path:p>` — 204 (idempotent).
- `PATCH /api/files/<path:p>/rename` — body `{ file_name }`.
  Same-parent only.
- `PATCH /api/files/<path:p>/move` — body `{ parent }`. Leaf name
  preserved; destination parent must be at depth `2..10`; same-
  parent attempts rejected.
- `POST /api/files/<path:p>/duplicate` — body `{ file_name }`.
  Same-parent, same-extension.
- `GET /api/files/<path:p>/raw` — returns source text (`text/plain`).
- `PUT /api/files/<path:p>/raw` — accepts raw text; parses,
  validates, re-serialises, atomic-writes. Always canonicalises.

Storage methods:

- `Storage.create_file(parts, description)`
- `Storage.read_feature(parts) -> Feature`
- `Storage.read_raw(parts) -> str`
- `Storage.write_feature(parts, feature)`
- `Storage.write_raw(parts, text)`
- `Storage.rename_file(parts, new_name)`
- `Storage.move_file(source_parts, dest_parent)`
- `Storage.duplicate_file(parts, new_name)`
- `Storage.delete_file(parts)`

UI triggers (`app/static/03_folder_actions.js` + `08_file_editor.js`):

- `tmsCreateFile(parent)` — `tmsOpenModal`-based form with file
  name + description; posts `/api/files`. Hint text declares
  `.feature` is auto-appended. Wired into `+ Create test case`
  buttons in `folder_module.html` / `folder_subfolder.html`.
- `tmsEditor.rename()` — topbar `Rename…` button in
  `file_editor.html`; PATCH `/api/files/<p>/rename`.
- `tmsEditor.move()` — topbar `Move…` button; opens a tree-based
  folder picker modal then PATCH `/api/files/<p>/move`.
- `tmsEditor.save()` — PATCH `/api/files/<p>` with the structured
  buffer.
- `tmsEditor.saveRaw()` — PUT `/api/files/<p>/raw` with the raw
  textarea contents.

UI gaps in v1:

- `DELETE /api/files/<p>` has **no UI button**. API-only.
- `POST /api/files/<p>/duplicate` has **no UI button**. API-only.

## Invariants & rules

**Filename normalisation**

- The leaf is normalised on create / rename / duplicate by
  `_normalize_filename`: lower-cased extension comparison,
  rejects supplied non-`.feature` extension, auto-appends
  `.feature` if missing.

**Depth rules**

- File create: parent at `2 <= depth <= MAX_FOLDER_DEPTH`. Enforced
  in `server.post_file` (storage trusts the segments).
- File move destination parent: same `2..10` range. Enforced in
  `Storage.move_file`.
- Rename / duplicate: leaf path inherits the source's parent
  depth, so the same range is implicitly preserved.

**Same-parent / cross-parent**

- Rename: source and destination share the parent by construction.
- Duplicate: same-parent only (use move after duplicate to relocate
  the copy).
- Move: destination parent must differ from the source's; same-
  parent move is rejected as a no-op (forces the caller to surface
  intent).

**Create body**

- `description` is required non-empty (whitespace-only rejected at
  the API layer). The created file holds
  `Feature(description=…, scenario=Scenario(kind="scenario",
  name=""))` — i.e. one empty scenario, no steps, no tags, no
  background.

**Raw round-trip**

- `PUT /api/files/<p>/raw` always parses, validates, and
  re-serialises before writing. The bytes on disk after a raw save
  may differ from the bytes the client sent (canonical formatting
  applied). Parse errors return 422 `parse_error`; validation
  errors return 422 `validation_error`.

**Atomicity & locking**

- Every mutation goes through `_atomic_write_bytes` and `_mark_write`
  (covered in `02-storage-core`). The watcher suppresses the
  resulting FS events so the writing tab sees no SSE echo.

**Idempotence**

- `DELETE` is idempotent: missing target → 204.

## Affects

- `02-storage-core`: every route is a thin delegation; storage
  owns all the invariants.
- `01-gherkin-io`: parsing on read and raw write; serialising on
  every save.
- `06-tree-pane` and `07-folder-views`: each mutation triggers an
  SSE `"change"` that causes the tree and the active folder view
  to refresh; the folder view's `features` list reflects the new
  state.
- `08-file-editor`: rename, move, save, save-raw are invoked from
  the editor topbar; the editor owns dirty-state + breadcrumb
  updates around the calls.

## Depends on

- `01-gherkin-io` for parse / validate / serialize on read and
  every write path.
- `02-storage-core` for the eight underlying methods plus the
  locking and atomic-write guarantees.
- `app/static/03_folder_actions.js` modal primitive (`tmsOpenModal`) for create
  and move pickers.
- `app/templates/file_editor.html` topbar markup (`#btn-rename`,
  `#btn-move`, `#btn-save`, `#btn-save-raw`).

## Surface for follow-up

- Add UI surfaces for **delete** and **duplicate** — likely in the
  editor topbar alongside Rename / Move / Reload, with
  confirmations on dirty buffers.
- A future bulk-move or bulk-delete operation would compose the
  per-file storage methods; consider whether to add a transactional
  primitive or keep it as a client-side loop (failure-mode
  trade-off).
- `10-feature-test-run` (shipped) links to test cases by external
  `file_path` and chose the **tombstone-on-render** path: rename /
  move / delete here are NOT auto-coordinated with run files; the
  run editor recomputes a `missing: bool` per row on every render
  and strikes through the orphaned link while preserving the
  stored remark verbatim. `create_file` also enforces "no
  `.feature` files under `<project>/test-run/`" via
  `NameConflictError`.
- `PUT …/raw` is the only path that exposes `parse_error` / 422 to
  end users today; structured-tab saves go through `Feature.from_dict`
  on shapes the UI built, so they only surface `validation_error`.
  Worth keeping in mind when designing future client-side parsers.

## Acceptance criteria

- Creating a file at depth-1 parent (`POST /api/files` with
  `parent: "<project>"` only) returns 400 — files must live at
  depth `2..10`.
- Creating a file with a name conflict returns 409.
- Saving via structured PATCH and saving the same content via raw
  PUT (after a `GET /raw` round-trip) result in byte-identical
  files on disk.
- Renaming to a name that conflicts in the same parent returns 409
  and leaves the source file in place.
- Moving across folders preserves the leaf name and the file's
  content byte-for-byte.
- Deleting an already-missing file returns 204.
- Every successful mutation produces exactly one SSE `"change"`
  event on *other* tabs and zero on the writing tab (verified by
  `_mark_write` covering both target and parent dir).
