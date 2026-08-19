# feature-22 · Folder table sort and scenario filter — coverage matrix

Smoke coverage against `specs/features/22-feature-folder-table-sort-filter-NEW.md`.

| Contract | Smoke | Status |
| --- | --- | --- |
| Module and nested-folder tables render scenario filter, ascending filename sort, and row data | `F22_01_table_render` | covered |
| Case-insensitive scenario filter, stable filename toggle, visible-only Select all, and hidden selected bulk paths remain wired | `F22_02_controller_static` | static |

Browser-only interactions reuse the feature-10 case-picker pattern. The
static check guards its hooks and selection boundaries; no endpoint or storage
behaviour changed.
