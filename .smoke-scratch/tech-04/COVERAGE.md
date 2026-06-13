# tech-04 · Test-case detail (editor) revamp — coverage matrix

Smoke coverage against
`specs/tech/04-tech-testcase-detail-revamp-NEW.md` (shipped Jun 13, 2026).

## Method

- Spec source: `specs/tech/04-tech-testcase-detail-revamp-NEW.md`
  (decisions D1–D5, RG1, Option B, OQ1–OQ8).
- New tech-04 smokes pin the cross-cutting behaviours (empty-description
  round-trip, the scenario-name migration, the enums grid). The per-layer
  contracts that changed were **re-pinned in their owning feature dirs**
  (feature-01/02/05/08/09/11) rather than duplicated here.
- `Status`: `covered`, `static` (JS invariant by source inspection).

## Matrix

| Spec area | Smoke | Status |
| --- | --- | --- |
| D1: empty feature description validates + serialises (bare `Feature:`) + parses + round-trips + `create_file` accepts it | `tech-04/T04_01_empty_description_roundtrip` | covered |
| D1: `validate_feature` no longer rejects empty/whitespace description (V1 inverted) | `feature-01/F01_02_validate_time` | covered |
| D1 migration: move description → `scenario.name` (`" / "`-joined), skip already-named + empty-description, idempotent | `tech-04/T04_02_scenario_name_migration` | covered |
| D2/D3 + Option B: `POST /api/files` — `file_name` required; `scenario_name` + `description` optional (type-checked); created `scenario.name` carries the identity | `feature-05/F05_07_create_body` | covered |
| D2/D3: create modal `tmsCreateFile` — 3 fields (File name, Feature description optional, Scenario name); POST body + gate on name+scenario | `feature-05/F05_02_ui_triggers` | static |
| D5: enums render as up-to-3-column (kind, value) row grid; `+ Add enum`; OQ6 kind exclusion; orphan-preserving commit; scaffold ids intact | `tech-04/T04_03_enums_grid` | static + covered |
| D5 / ED11: a kind with no entries → disabled value `<select>` + `edit enums.yaml` hint | `feature-11/F11_14_picker_empty_disabled` | static |
| D5 / ED12: value `<select>` leads with `— not set —` (value=""); options submit key, display label; stored key pre-selected | `feature-11/F11_15_picker_options_notset` | static |
| D5: value/kind change commits via `_commitEnumRows` → rebuilds `feature.enums` + marks dirty; renderEnums wired into renderStructured; orphans/init unchanged | `feature-11/F11_09_editor_controller` | static |
| D5: enums scaffold container ids unchanged (`#feature-enums-*` + init button) | `feature-11/F11_08_editor_scaffold` | covered |
| D4: file-name `<h2>` removed; structured tab + legacy ids still render | `feature-08/F08_05_structured_tab`, `feature-11/F11_08` | covered |
| RG1: editor Save-gate keys on `scenario.name` (not description); disabled-state styling on `#btn-save` | `feature-08/F08_10b_save_disabled_empty_desc`, `F08_19a_open_default` | static + covered |
| OQ8: search-results list displays the scenario name instead of the description | `feature-09/F09_19_results_list_view` | covered |
| OQ8: `SearchHit` carries `scenario_name` (text + tag modes) | `feature-09/F09_01`, `F09_05`, `feature-02/F02_07_search` | covered |
| Follow-up: text search matches `Feature.description` **OR** `scenario.name` (either field; `matched_field` stays `"description"`) | `feature-09/F09_04_match_text` (scenario-name-only hit) | covered |
| Follow-up: editor `#scenario-name` placeholder is `"Scenario name"` (was the stale `"(optional)"`) | `feature-08/F08_05_structured_tab` | covered |
| Follow-up: folder-detail test-case list middle column shows the scenario name (was the feature description); `list_folder` carries `scenario_name` | `feature-07/F07_04b_description_column`, `F07_10f`, `feature-06/F06_12` | covered |
| Raw view unchanged | `feature-08/F08_06_raw_tab`, `F08_14_save_raw_flow`, `F08_19d` | covered |

## Notes

- **Option B (deferred):** `scenario_name` is required only by the create
  modal (client-side), not the API — consistent with the permissive model
  (V5) and the UI-only Save-gate (RG1). Server-side enforcement is tracked
  as a separate Must-have ("Require `scenario_name` at the create API").
- **Migration script:** `scripts/backfill_scenario_names.py`, run offline
  via `.venv/bin/python scripts/backfill_scenario_names.py`; idempotent.
- Full suite at sign-off: **275/275 PASS / 0 FAIL**.
