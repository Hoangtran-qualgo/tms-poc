# 04 · Folder CRUD

_Retroactive spec: documents the as-shipped behaviour. Source files:_
_`app/server/routes_folders.py` (folder routes), `app/storage/_folders.py`_
_(folder methods), `app/static/03_folder_actions.js` (`tmsCreateProject`,_
_`tmsCreateModule`, `tmsCreateSubfolder`), `app/templates/folder_*.html`_
_(create buttons)._

## Summary

Create / rename / delete operations for project, module, and
sub-folder levels of the data root. Depth `1..10` is uniformly
supported by the API and storage; the UI only exposes the create
half of the contract in v1 — rename and delete exist on the server
but have no button yet.

## Scope

In scope:

- Create folders at any depth `1..10` (project, module, sub-folder).
- Rename folders at any depth (same-parent only — the parent path
  is fixed by construction since the new name occupies the same
  slot).
- Delete folders recursively at any depth; idempotent on missing
  target.
- Server-side name uniqueness scoped to the parent.
- The three UI create entry points (project, module, sub-folder)
  with their distinct prompts/modals.

Out of scope:

- Folder *move* (no API today).
- Folder *duplicate* (no API today).
- UI buttons for folder rename / delete (API-only in v1).
- File operations (covered in `05-testcase-crud`).

## Public surface

HTTP routes (Flask blueprint `api`):

- `POST /api/folders` — body `{ name, parent? }`, parent defaults
  to `""` (root). Creates `parent + [name]`. Returns `{ok: true}`
  on 201.
- `PATCH /api/folders/<path:p>` — body `{ name }`. Renames `p` to
  `<parent of p>/<name>`. Returns `{ok: true}`.
- `DELETE /api/folders/<path:p>` — recursive delete. Returns
  `""` with HTTP 204 (idempotent: missing target is treated as
  success).

Storage methods (called by the routes):

- `Storage.create_folder(parts) -> None`
- `Storage.rename_folder(parts, new_name) -> None`
- `Storage.delete_folder(parts) -> None`

UI triggers (`app/static/03_folder_actions.js`):

- `tmsCreateProject()` — prompt-based, posts to `/api/folders`
  with `parent: ""`. Used by the `+ New project` button in
  `folder_root.html`.
- `tmsCreateModule(project)` — prompt-based, posts with
  `parent: project`. Used by `+ New module` in
  `folder_project.html`.
- `tmsCreateSubfolder(parent)` — `tmsOpenModal`-based, posts with
  the given parent. Used by `+ Sub-folder` in
  `folder_module.html` and `folder_subfolder.html`.

All three call `tmsRefreshFolder(parent)` on success so the current
main pane re-renders.

## Invariants & rules

**Depth**

- `create_folder` accepts `1 <= len(segments) <= MAX_FOLDER_DEPTH`
  (10). Depth 1 = project; depth 2 = module; depth 3..10 =
  sub-folder.
- `rename_folder` and `delete_folder` accept any depth `>= 1`.

**Name uniqueness**

- Enforced via `target.exists()` (OS-dependent case sensitivity —
  see `02-storage-core` for the full rule). No explicit
  `casefold` / `lower` normalisation. Conflicts raise
  `NameConflictError` → HTTP 409.
- A folder and a file may coexist at the same logical name iff
  the host filesystem treats their resolved paths as distinct;
  in practice they always differ because the file leaf includes
  the `.feature` extension.

**Name validation**

- Every segment passes `_validate_segment`: no `/ \ : * ? " < > |`
  or control characters. Empty / `.` / `..` rejected.

**Idempotence**

- `DELETE /api/folders/<p>` returns 204 even if `p` was already
  gone (storage's `delete_folder` no-ops on missing target).

**UI gaps**

- v1 has no UI button for folder rename or delete. Users wanting
  these operations must call the API directly (e.g. `curl` or the
  forthcoming pending Investigate items that may add the
  surfaces).

## Affects

- `02-storage-core`: every route is a one-line delegation to a
  `Storage` method.
- `06-tree-pane`: every successful folder mutation triggers an SSE
  `"change"` event (via the watcher), which the tree pane consumes
  to re-render.
- `07-folder-views`: hosts the create buttons; the modules /
  sub-folders list rendered by these views reflects the post-
  mutation state after the tree refresh.

## Depends on

- `02-storage-core` for all FS work and name validation.
- `app/errors.py` for `NameConflictError` (→ HTTP 409) and
  `ValueError` (→ HTTP 400).
- `app/static/03_folder_actions.js` modal primitive (`tmsOpenModal`) for the
  sub-folder create flow; `window.prompt` for project / module
  create (legacy v1 affordance).

## Surface for follow-up

- Folder rename and delete buttons in the UI are missing — easy
  additions because the API already exists; UX decision needed
  (inline action menu vs. modal vs. dedicated folder-detail view).
- Folder *move* would require a new storage method and route
  (analogous to `move_file`); reuse the sorted-dual-lock pattern.
- `10-feature-test-run` (shipped) layers a depth-2 reservation on
  top of `create_folder`: the name `test-run` at the second
  segment is rejected via `NameConflictError`, and folders under
  `<project>/test-run/<group>/` are similarly refused. The
  grouping folders themselves are created via the run-specific
  `create_run_group` helper, not the generic API.
- Migrating `tmsCreateProject` / `tmsCreateModule` away from
  `window.prompt` to `tmsOpenModal` would unify the create-flow
  UX (cosmetic; tracked nowhere yet).

## Acceptance criteria

- Creating a folder named with a forbidden char returns 400 with
  `code: bad_request`.
- Creating a folder at depth 11 (or higher) returns 400.
- Creating a duplicate folder name in the same parent returns 409
  with `code: name_conflict`.
- Deleting a folder removes every descendant file and folder.
- Deleting a non-existent folder returns 204 (idempotent).
- Each successful mutation results in exactly one SSE `"change"`
  event reaching open tabs (after `DEBOUNCE_SECONDS`), with no
  self-event from the writing tab.
