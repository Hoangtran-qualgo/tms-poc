# 18 · Delete folders from the UI

_Shipped Aug 17, 2026. Extends feature 04's existing recursive DELETE
contract without changing its API or storage implementation._

## Goal

Allow users to delete a folder from the UI, recursively deleting the folder,
its descendant folders, and contained test cases after an explicit permanent-
delete confirmation.

## Evidence

- `DELETE /api/folders/<path>` already calls
  `Storage.delete_folder(parts)` and returns idempotent `204`.
- `delete_folder()` rejects only the data root and file targets; otherwise it
  runs `shutil.rmtree()` under the storage root. It does not need a new
  recursive primitive.
- Before this feature, folder views had no delete controls. Their main-pane
  content still needs a direct refresh after a mutation because only the
  sidebar listens to SSE.
- A module or branch delete removes only that branch; project-level
  `enums.yaml` remains. Deleting a project removes every project descendant,
  including hidden `test-run/` and `report/` typed areas and enum config.
- The generic UI does not list reserved typed areas, but the existing generic
  delete route does not block a direct API call to one.

The runnable spike
`.smoke-scratch/_investigate/folder-delete/01_recursive_scope.py` proves the
module and project scopes above against an isolated storage root.

## Implemented approach

Reuses the existing DELETE route and storage method. Adds a red **Delete
folder** action only to generic module (depth 2) and branch (depth 3..10)
views; root, project, and reserved typed-area views have no control. Open a
`tmsOpenModal()` confirmation naming the full target path and warning that the
action permanently removes all descendants and test cases. One Confirm click
is sufficient. After a successful DELETE, close the modal, navigate the main
pane to the deleted folder's parent, and refresh the Directory tree explicitly
because self-writes suppress its SSE event.

This does not add a new endpoint, a storage implementation, a tree context
menu, undo/trash, a recursive count endpoint, or controls inside reserved
typed-area views.

## Rules / accepted blindspot

1. **Scope:** Only modules and deeper branches can be deleted in the UI.
   Project deletion remains API-only because it destroys hidden runs, reports,
   and enum configuration as well as test cases.
2. **Confirmation:** One explicit modal confirmation names the target and says
   that descendant folders/test cases are permanently deleted.
3. **Summary:** The warning is static; no count/list preflight is added. The
   normal tree hides typed project data, and a count can become stale before
   the destructive request.
4. **Accepted blindspot:** The generic direct API can still delete a reserved
   `test-run`/`report` folder. This feature exposes no such control; API
   hardening is a separate task and is intentionally untouched.

## PDCA record

1. **Plan — done:** locked module/branch scope, one-click confirmation, and a
   static warning.
2. **Do — done:** added one small `tmsDeleteFolder(folderPath, parentPath)` controller
   in `03_folder_actions.js`; reuse `tmsOpenModal`, fetch DELETE, error
   rendering, `tmsRefreshFolder(parentPath)`, and `tmsRefreshTreePane`.
3. **Do — done:** added buttons only at confirmed generic folder depths, using safely
   encoded template values; never add a root or typed-area control.
4. **Check — done:** added feature-18 UI/API smokes for control scope, confirmation,
   recursive delete, parent navigation, tree refresh, and error retention;
   revise old feature-04/07 no-delete gap assertions into historical notes.
5. **Act — done:** updated backlog and historical docs, removed the temporary
   plan, and synchronised the feature summary after green checks.

## Acceptance criteria after decisions are locked

- Users can invoke deletion only at the confirmed generic folder depths; root,
  project, and reserved typed-area views offer no generic delete control.
- The modal names the target path and clearly says descendants/test cases are
  permanently deleted before the DELETE request is sent.
- Successful deletion removes the selected folder recursively, replaces the
  now-invalid main-pane view with its parent, and refreshes the Directory tree.
- Failed deletion keeps the confirmation open and displays the API error.
- Existing direct DELETE idempotence and the no-data-root invariant remain
  unchanged.

## Affects

- `app/static/03_folder_actions.js` — gains the confirmation, DELETE request,
  error handling, and deterministic parent/tree refresh sequence.
- `app/templates/folder_module.html` and `folder_subfolder.html` — contain
  the controls at the confirmed scope; project and typed templates stay
  unchanged.
- `specs/features/04-feature-folder-crud-NEW.md` and
  `07-feature-folder-views-NEW.md` — their v1 UI-gap statements must record
  this additive feature rather than remain current behaviour.
- `.smoke-scratch/feature-04/`, `.smoke-scratch/feature-07/`, and new
  `.smoke-scratch/feature-18/` coverage — old negative gap checks must be
  revised and new behaviour locked.

## Depends on

- Feature 04's recursive, idempotent folder DELETE route and data-root guard.
- Feature 06's tree refresh helper and self-write SSE suppression model.
- Feature 07's current-folder templates and parent breadcrumb routing.
- `tmsOpenModal()` for accessible Cancel/Escape/Confirm behaviour.

## Surface for follow-up

- An explicit project-delete decision may require a stronger confirmation and
  typed-data summary because runs/reports/enums are not visible in generic
  folder views.
- A trash/undo model or delete preview/count endpoint is deliberately deferred
  until demanded; either is materially broader than wiring the existing API.
- Generic DELETE access to reserved typed areas is an existing API-hardening
  question, separate from the UI scope.
