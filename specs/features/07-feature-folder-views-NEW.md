# 07 · Folder views

_Retroactive spec: documents the as-shipped behaviour. Source files:_
_`app/server.py` (`ui_folder`, `_folder_crumbs`),_
_`app/templates/folder_root.html`, `folder_project.html`,_
_`folder_module.html`, `folder_subfolder.html`._

## Summary

Main-pane content for browsing folders of the data root. A single
HTMX-served route (`/ui/folder/<path>`) dispatches to one of four
templates based on depth: root (project list), project (module
table), module (sub-folders + features), and sub-folder (sub-
folders + features with breadcrumb). Each view hosts the create
buttons relevant at that depth, but never mutates content itself —
mutation goes through the JS helpers documented in `04-folder-crud`
and `05-testcase-crud`.

## Scope

In scope:

- The four folder-view templates and their visual contracts.
- Depth-based dispatch in `ui_folder`.
- Breadcrumb rendering for module / sub-folder views.
- Feature row rendering (file name, first-line description, tag
  chips) and sub-folder row rendering.
- Empty-state placeholders at each depth.

Out of scope:

- The CRUD operations themselves (`04-folder-crud`,
  `05-testcase-crud`).
- Tree-pane rendering (`06-tree-pane`).
- File editor (`08-file-editor`); rows just navigate to it via
  HTMX.

## Public surface

Route:

- `GET /ui/folder/` and `GET /ui/folder/<path:p>` — handled by
  `ui_folder`. Reads `storage.list_folder(segments)` and renders
  the depth-appropriate template.

Templates:

- `folder_root.html` (depth 0) — project list. Header with
  `+ New project` button (or empty-state placeholder).
- `folder_project.html` (depth 1) — module table. Breadcrumb
  back to root. `+ New module` button (or empty state).
- `folder_module.html` (depth 2) — sub-folder table (if any) +
  features table. Breadcrumb `Projects / <project> / <module>`.
  `+ Sub-folder` and `+ Create test case` buttons.
- `folder_subfolder.html` (depth 3..10) — same shape as module
  view but uses a server-built `crumbs` list to render an
  arbitrarily long breadcrumb.

Server helper:

- `_folder_crumbs(segments) -> list[{label, path}]` — builds the
  breadcrumb chain for the sub-folder view and (per its docstring)
  for the file-editor breadcrumb so both render N levels uniformly.

## Invariants & rules

**Dispatch**

- `len(segments) == 0` → `folder_root.html`.
- `len(segments) == 1` → `folder_project.html`.
- `len(segments) == 2` → `folder_module.html`.
- `len(segments) >= 3 and <= MAX_FOLDER_DEPTH` →
  `folder_subfolder.html`.
- `len(segments) > MAX_FOLDER_DEPTH` → 400 `bad_request` from
  `Storage.list_folder` (handled by the UI blueprint's
  `ValueError` handler).

**Features-table column contract**

- `File name`: shown as-is. Click → `/ui/file/<path>`.
- `Description`: **first line only**, truncated; full description
  in the `title=` attribute for hover. Multi-line descriptions
  never expand the row.
- `Tags`: chips rendered with `@` prefix, single line, truncated.

**Sub-folder-table column contract**

- One column: `Sub-folder` with a folder icon (`📁`). Click →
  `/ui/folder/<path>`.

**Buttons by depth**

| Depth | Create buttons |
|---|---|
| 0 (root) | `+ New project` |
| 1 (project) | `+ New module` |
| 2 (module) | `+ Sub-folder`, `+ Create test case` |
| 3..10 (sub-folder) | `+ Sub-folder`, `+ Create test case` |

No rename / delete / move buttons at any depth — those operations
either don't have UI (`04-folder-crud`) or live inside the file
editor (`05-testcase-crud` rename + move).

**Empty states**

- Depth 0 with no projects: "No projects yet." + central
  `Create project` CTA.
- Depth 1 with no modules: "No modules in <project> yet." + CTA.
- Depth 2 / 3+ with no folders AND no features: "No test cases in
  <name> yet." + CTA (or, in sub-folder view, both
  `+ Sub-folder` and `+ Test case` CTAs side-by-side).

**Re-render trigger**

- The main pane is *not* SSE-wired in v1; only the tree pane is.
  Folder views update only when (a) the user navigates to one
  explicitly via HTMX click, (b) `tmsRefreshFolder(folderPath)` is
  called by JS after a CRUD operation, or (c) the user clicks the
  tree refresh and then re-navigates.

## Affects

- `02-storage-core`: each render is one `Storage.list_folder` call;
  the return shape (`kind` + `projects`/`modules`/`folders`/
  `features`) is the rendering contract.
- `04-folder-crud`, `05-testcase-crud`: host the create-button
  entry points; consume `tmsRefreshFolder` to repaint after their
  own mutations.
- `08-file-editor`: every feature row's `hx-get` opens the editor.
- `06-tree-pane`: shares the same `hx-get="/ui/folder/<path>"`
  navigation URL as the tree's folder-name spans.

## Depends on

- `02-storage-core` for `list_folder` and `_folder_crumbs`'s
  segment splitting.
- `04-folder-crud` for the create-button handlers
  (`tmsCreateProject` / `tmsCreateModule` / `tmsCreateSubfolder`).
- `05-testcase-crud` for the `+ Create test case` handler
  (`tmsCreateFile`).
- HTMX 2.x for row-level `hx-get` navigation.
- Tailwind CDN for table / row styling (visual only).

## Surface for follow-up

- No per-row actions today (rename / delete / duplicate / move
  buttons absent on every row). Adding them is a layout decision —
  inline icons, hover-revealed action menu, or a per-row context
  menu. The APIs already exist.
- Column sorting / filtering not implemented; the rows render in
  the order `list_folder` returns them (OS listing order, since
  the watcher does not impose any sort).
- Multi-select + bulk operations not implemented; would need both
  a UI affordance and a server-side bulk endpoint.
- `10-feature-test-run` (shipped) extends `ui_folder` with a
  branch for `segments[1] == "test-run"` and adds two typed-area
  templates (`folder_test_run_area.html` for the groups landing,
  `folder_test_run_group.html` for the runs list). The typed area
  is exactly two levels deep; requests for paths deeper than
  `<project>/test-run/<group>` 404 under `ui_folder` because runs
  are reached via the separate `/ui/run/...` route. The project
  view also filters `test-run` out of its module table, so the
  typed area is unreachable from this spec's surfaces.

## Acceptance criteria

- Visiting `/ui/folder/` with no projects renders an empty-state
  CTA and no tables.
- Visiting `/ui/folder/<existing path>` at any depth `0..10`
  renders without error.
- Visiting `/ui/folder/<path>` at depth `11` returns a 400 inline
  error snippet.
- Clicking a feature row opens that file in the editor.
- Clicking a sub-folder row navigates the main pane to that
  folder's view.
- Multi-line feature descriptions render only their first line in
  the table; full text appears on hover.
- After a CRUD mutation, the main pane reflects the new state on
  the writing tab once `tmsRefreshFolder` runs.
