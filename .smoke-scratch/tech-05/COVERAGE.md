# tech-05 · Run-detail scenario-name column + remark resize — coverage matrix

Smoke coverage against
`specs/tech/05-tech-run-detail-scenario-name-NEW.md` (shipped Jun 13, 2026).

## Method

- Spec source: `specs/tech/05-tech-run-detail-scenario-name-NEW.md`
  (asks 1–2; decisions RD-1b + RD-2a; assumptions RD-3/RD-4).
- New tech-05 smokes pin the cross-cutting behaviours (live display-only
  render, dirty-snapshot exclusion, colspan bump + remark height, add-on-
  fetch).
- `Status`: `covered`, `static` (JS / template invariant by source
  inspection).

## Matrix

| Spec area | Smoke | Status |
| --- | --- | --- |
| Ask 1 / SN1: results table has a `Scenario name` column header | `tech-05/T05_01_scenario_name_render` | covered |
| A (server): `ui_run` attaches each result's scenario name read LIVE from the `.feature`; rendered as a plain `run-scenario-name` <td> (no input) | `tech-05/T05_01_scenario_name_render` | covered |
| Display-only is read live, never snapshotted: rewriting the case's scenario name re-renders the new value without mutating the run YAML | `tech-05/T05_01_scenario_name_render` | covered |
| RD-4: tombstoned / unreadable case → blank scenario name | `tech-05/T05_01_scenario_name_render` | covered |
| RD-3: `_readCurrent` DOM snapshot projects only {file_path, result, remark} — never reads the scenario cell (can't flip dirty) | `tech-05/T05_02_display_only_not_dirty` | static |
| RD-3: scenario name is render-only — `RunResult` model + JSON run API carry exactly {file_path, result, remark} | `tech-05/T05_02_display_only_not_dirty` | covered |
| Ask 1 / SN4: folder-group heading spans all 5 columns (`colspan="5"`) — server render + clone <template> | `tech-05/T05_03_colspan_and_remark` | covered |
| Ask 2 / SN5 / RD-2a: remark <textarea> stands ~1.5 lines tall (`h-10`) + `overflow-y-auto` so a 2nd line peeks (cues "there's more"); live row + add-row template; CSS-only, no auto-grow JS | `tech-05/T05_03_colspan_and_remark` | covered |
| RD-1b: add-row <template> includes the `run-scenario-name` cell | `tech-05/T05_04_addcase_fetch_scenario` | covered |
| RD-1b: `_createResultRow` wires the async fill; `_fillScenarioName` GETs `/api/files/<path>`, reads `scenario.name`, fills the cell, swallows errors (blank on failure) | `tech-05/T05_04_addcase_fetch_scenario` | static |
| RD-1b: `GET /api/files/<path>` (the endpoint the fill reuses) returns the case's scenario name | `tech-05/T05_04_addcase_fetch_scenario` | covered |

## Notes

- **Decisions taken (Jun 13, 2026):** RD-1 **(b)** — newly-added rows fetch
  their scenario name on add (reusing the existing
  `GET /api/files/<path>`, so no new endpoint and no per-feature parsing in
  the `list_tree` sidebar hot path). RD-2 **(a)** — CSS-only remark resize.
- **Remark height follow-up (Jun 13, 2026):** the original 2-line
  `max-h-[3.25rem]` cap never showed a 2nd line (the `rows="1"` box stayed
  one line and silently scrolled). Replaced with a *fixed* ~1.5-line height
  (`h-10`) so a clipped 2nd line cues the user there's more to scroll.
- **No feature-10 smoke needed re-pinning:** the extra `<td>` + the
  `colspan` 4→5 bump did not break any existing E2 / tombstone / row-shape
  regex (full suite stayed green). The group-head colspan was already
  asserted loosely.
- **Depends on tech-04 migration** (already run) so legacy runs show
  scenario names rather than blanks.
- Full suite at sign-off: **279/279 PASS / 0 FAIL** (was 275; +4 tech-05).
