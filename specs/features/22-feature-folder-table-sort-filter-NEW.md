# 22 · Folder test-case table sort and scenario filter

_**SHIPPED Aug 19, 2026.**_

## Goal

In module and nested-folder detail pages, let users sort direct test cases by
filename and filter those rows by scenario name.

## Current evidence

- Both folder views include `_folder_feature_table.html`; project detail has a
  module table, not a test-case table.
- `Storage.list_folder()` supplies direct feature metadata (`file_name`,
  `scenario_name`, tags, enums) in filesystem `iterdir()` order. It is also
  used by JSON folder-content callers, so changing it globally would broaden
  this UI feature unnecessarily.
- `tmsBulkBind()` owns current checkboxes, count text, and Select all. A
  separate row-filter controller would leave Select all acting on hidden rows.
- Spike
  `.smoke-scratch/_investigate/folder-table-sort-filter/01_current_contract.py`
  confirms the direct-row and bulk-selection seam.

## Confirmed behavior

### Scope

- Direct `.feature` rows only in module and nested-folder detail views.
- No project-module-table, recursive-descendant, tree-sidebar, storage, or API
  behavior change.

### Sort

- Filename header is a button with an accessible ascending/descending state.
- Initial order is filename ascending, case-insensitive. Repeated click toggles
  descending; ties retain original-row order.

### Filter

- A scenario-name text input sits above the feature table.
- Trimmed, case-insensitive substring match against scenario name only.
- Blank filter shows all direct rows. Rows from malformed files have an empty
  scenario name, so a non-empty filter hides them.

### Bulk selection

- Filtering hides rows without clearing their checks.
- Select all / its tri-state state applies to visible rows only, matching the
  established test-run case-picker behavior.
- Bulk actions keep acting on every selected row, including hidden selected
  rows. Count text must show shown and selected quantities while filtered.
- Folder HTMX refresh after any mutation resets sort, filter, and selection,
  matching the existing full-partial refresh behavior.

## Implementation

1. `_folder_feature_table.html` adds semantic row data
   (`data-file-name`, `data-scenario-name`), a filename-header button, and a
   scenario-filter input.
2. `tmsBulkBind()` in `08_bulk_actions.js` reorders the same `<tr>` elements,
   toggles filter visibility, and derives Select all from visible checkboxes.
   Moving existing rows preserves checkbox listeners and checked state.
3. Feature-22 smokes cover both folder depths plus static sort/filter/bulk
   selection wiring.

## Verification

- `feature-22/F22_01_table_render` renders both shared-table consumers with
  sort, filter, and row metadata.
- `feature-22/F22_02_controller_static` locks the case-insensitive filter,
  stable sorting, visible-only Select all, and hidden selected bulk paths.
- Existing feature-07 folder-view smokes and relevant tech-03 bulk smokes
  remain green.

## Affects

- `07-feature-folder-views` — shared direct test-case table layout.
- Existing bulk actions — selection/count/Select all semantics during filter.
- `10-feature-test-run` — reuse its visible-row Select all precedent only;
  no run API changes.

## Depends on

- `Storage.list_folder()` direct feature-row contract.
- `_folder_feature_table.html` shared module/nested-folder inclusion.
- `tmsBulkBind()` lifecycle on HTMX load.

## Surface for follow-up

- Tag/group filtering remains separate backlog scope.
- Server-side pagination, persisted sort/filter preferences, and recursive
  search are out of scope.
