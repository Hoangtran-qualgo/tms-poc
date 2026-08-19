# 21 · Folder and test-case filename rename UI

_Shipped Aug 19, 2026. Folder/project rename and test-case filename rename
now preserve persisted path references._

## Goal

- Rename project, module, and nested branch folders from their folder-detail
  views.
- Rename a test-case filename from its folder-detail row, not from the file
  editor.
- Keep test runs and reports valid after a rename.

## Contract

`PATCH /api/folders/<path>` and `PATCH /api/files/<path>/rename` keep their
existing request and `{ "ok": true }` response contracts. Folder/file
renames remain same-parent operations, retain existing validation and conflict
rules, and now cascade path references before returning success.

For an old path `old` and new path `new`, a stored path changes only when it
is exactly `old` or begins `old + "/"`. A loose prefix never matches: renaming
`project/module` does not alter `project/module-other`.

The cascade covers every data-root-relative value in the affected project:

- `TestRun.results[].file_path`;
- `Report.case_path`;
- `Report.scope`;
- `Report.run_paths` (notably after a project rename).

Before moving anything, storage parses all run YAML below
`<project>/test-run/` and all report YAML in `<project>/report/`. A malformed
typed document blocks the rename with no physical move. This is deliberately
stricter than checking only known dependents: malformed metadata cannot be
proven unrelated without risking a stale link.

After preflight, storage moves the folder/file with `os.replace` and atomically
rewrites only changed metadata documents. If a rewrite fails, it best-effort
restores already-written metadata and reverses the physical move, then returns
the original error. This is compensating recovery, not crash-safe journalling;
a process crash during that sequence can still leave a partial cascade.

File **move** and delete retain their established tombstone-on-render behavior;
this feature changes rename only.

## UI

- Project headers show **Rename project**.
- Module and nested folder headers show **Rename folder** beside Delete.
- Each test-case row in the module/nested folder table shows **Rename**.
- Both actions use `tmsOpenModal`, prefill the current leaf name, keep API
  errors inline, and preserve `.feature` auto-append for filenames.
- A successful module/nested-folder rename pushes its new folder URL, then
  refreshes the renamed folder and Directory tree. File rename refreshes its
  containing folder and Directory tree. A project rename uses a full
  navigation to its renamed folder so Directory, Test-run, Reports, and Enums
  reload under the new key.
- `file_editor.html` and `tmsEditor` have no rename control; its Move, Reload,
  and Save controls remain unchanged.

Generic folder views do not expose typed areas. Root has no folder to rename.

## Implementation

- `Storage.rename_folder()` and `Storage.rename_file()` reuse
  `FoldersMixin._relocate_with_reference_cascade()`.
- `_reference_rewrites_for_relocation()` parses/prepares all changed documents
  first; `_relocate_reference_path()` applies exact/slash-bounded replacement.
- Project rename moves run/report documents with the project folder, then
  writes their updated bytes at their new physical locations. Other folder/file
  renames rewrite metadata in place.
- `tmsRenameFolder()` and `tmsRenameFile()` in
  `app/static/03_folder_actions.js` own modal behavior and URL encoding.

## Checks

- `.smoke-scratch/feature-21/F21_01_storage_cascade.py` covers file, folder,
  and project cascades; slash-boundary protection; failed-write compensation;
  and malformed run metadata blocking.
- `.smoke-scratch/feature-21/F21_02_rename_ui.py` verifies project/module/
  branch controls, folder-table file action, and absence of editor rename.

## Affects

- `04-feature-folder-crud` — its existing folder route/storage primitive now
  backs project/module/branch UI and cascades references.
- `05-feature-testcase-crud` — its existing file rename route/storage
  primitive now backs folder-row UI and cascades references.
- `07-feature-folder-views` — owns all new rename controls and file-row action.
- `08-feature-file-editor` — relinquishes filename rename to folder details.
- `10-feature-test-run` and `12-feature-quality-report` — persisted path
  fields stay valid through rename.

## Depends on

- Feature 04/05 physical same-parent rename and name-conflict primitives.
- Feature 02 atomic writes, per-path locks, and self-write bookkeeping.
- Feature 10/12 persisted data-root-relative path formats.
- Shared `tmsOpenModal`, HTMX folder refresh, and full-navigation deep-link
  support.

## Surface for follow-up

- Cross-folder file move still needs an explicit cascade decision.
- Undo/trash and crash-safe journalling are separate features.
- The current project-wide typed-metadata preflight is intentionally simple;
  a large project may later need an indexed dependency graph.
