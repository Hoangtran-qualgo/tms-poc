# tech-03 · Folder bulk-actions — coverage matrix

Smoke coverage against
`specs/tech/03-tech-folder-bulk-actions-NEW.md` (shipped Jun 11, 2026).

## Method

- Spec source: `specs/tech/03-tech-folder-bulk-actions-NEW.md`.
- These smokes guard the **new server-rendered surface** (the shared
  `_folder_feature_table.html` partial: toolbar, checkbox column, scope)
  and **static invariants of the client controller**
  (`app/static/08_bulk_actions.js`). The fan-out interaction itself runs in
  the browser and is covered by static inspection per the standing Phase-2
  lock-in (no headless browser in this suite).
- The single-item endpoints the controller fans out over (Move / Delete /
  Re-tag / Run add-case) are primary-framed in feature-04 / feature-05 /
  feature-10 and are not re-tested here.
- `Status`: `covered`, `static` (JS invariant by source inspection),
  `n/a` (browser-only, documented).

## Matrix

| Spec area | Smoke | Status |
| --- | --- | --- |
| Toolbar renders (count + select-all + 4 disabled buttons) at depth 2 + 3 | `T03_02_toolbar_present` | covered |
| Per-row checkbox: canonical `data-case-path` key; double `stopPropagation`; `<tr>` hx-get intact (U2 / A1) | `T03_03_row_checkbox_no_navigate` | covered |
| Scope = direct children only (sub-folder cases excluded) | `T03_04_scope_direct_children` | covered |
| Toolbar renders only when the folder has direct features | `T03_05_toolbar_only_when_features` | covered |
| Controller shipped (referenced by base.html) | `T03_06_controller_static` | static |
| Four action handlers (move / delete / retag / run) | `T03_06_controller_static` | static |
| Fan-out over existing endpoints + 3 pre-flight listing endpoints (no new HTTP) | `T03_06_controller_static` | static |
| Idempotent `htmx:load` bind via `data-bulk-bound` (U3) | `T03_06_controller_static` | static |
| D1: Re-tag overwrites feature-level `tags` only (scenario untouched) | `T03_06_controller_static` | static |
| feature-07 contract preserved after extraction + checkbox column (A2) | `feature-07/F07_04a/b/c`, `F07_05`, `F07_08a/b/c` | covered |
| Shared modal Esc / Cmd+Enter (reused primitive) | `T03_01_modal_cmd_enter` | covered |
| All-or-nothing abort + modal error surface (D3) — browser interaction | — | n/a (browser) |
| Select-all all/none/indeterminate toggle behaviour — browser interaction | — | n/a (browser) |
| Click checkbox does not navigate (live) — browser interaction | — | n/a (browser; static half in `T03_03`) |

## Notes

- **Browser-only rows** mirror the project convention (feature-10 / Phase-2
  lock-in): selection toggling, the all-or-nothing modal flow, and the
  no-navigate click are exercised by hand. The static smokes pin every
  precondition those interactions depend on (markup hooks, endpoint URLs,
  bind wiring, D1 tag level) so a regression in the wiring fails CI even
  though the gesture itself is manual.
- Full suite at sign-off: **272/272 PASS / 0 FAIL**.
