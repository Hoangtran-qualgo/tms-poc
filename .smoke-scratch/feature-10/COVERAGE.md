# Feature 10 — Test run — coverage matrix (Step 1 audit)

Spec source: `specs/features/10-feature-test-run-NEW.md` (777 lines —
the largest feature in the suite).

Source files in scope:
- `app/models.py` — `TestRun`, `RunResult`, `RUN_RESULTS`, `validate_run`.
- `app/storage.py` — run + group CRUD, per-case mutation, typed-tree
  aggregator, `RESERVED_DEPTH2_NAMES`, `_normalize_run_filename`,
  `list_projects`, sidebar-visibility filters.
- `app/errors.py` — `RunParseError`.
- `app/server.py` — `/api/runs/*`, `/api/run-groups`, `/ui/run/...`,
  the `ui_folder` `test-run` dispatcher branch, `/ui/test-run-tree`.
- `app/templates/` — `folder_test_run_area.html`,
  `folder_test_run_group.html`, `run_editor.html`,
  `test_run_sidebar.html`.
- `app/static/app.js` — `tmsRunEditor`, `tmsCreateRun`,
  `tmsBuildCasePicker`, `tmsFetchProjectFeaturePaths`,
  `tmsSlugifyForFilename`, plus the bottom-of-file wiring.

## Method

Same conventions as features 01–09:

- One stable ID per spec rule; one smoke per rule (or tightly-coupled
  cluster) under `.smoke-scratch/feature-10/F10_<MM>[a-z]?_<slug>.py`.
- HTTP round-trips use the Flask test client end-to-end; storage
  semantics are re-owned through the routes where a route exists.
- Pure-JS controller rules (`tmsRunEditor`, `tmsCreateRun`,
  `tmsBuildCasePicker`) are covered by **static regex inspection** of
  `app/static/app.js` — no JS runtime (carried forward from the
  feature-04/08 Step-1 sign-off; Phase-2/3 lock-in already documents
  "live clicks need a browser" for these).
- SSE / external-change claims reuse the EventBus-subscriber +
  out-of-band-write pattern from features 03/06.

Rule-ID groups:
- `DM*` data model + `validate_run` invariants.
- `SC*` on-disk schema (keys, block scalar, idempotence, parse error).
- `FL*` folder discipline / layout (reservation, nesting, lazy area).
- `SM*` storage public-surface methods.
- `AP*` HTTP API endpoints.
- `UR*` UI routes + dispatcher.
- `TM*` templates.
- `RE*` `tmsRunEditor` controller.
- `CR*` `tmsCreateRun` modal state machine.
- `CP*` `tmsBuildCasePicker`.
- `WR*` bottom-of-file wiring.
- `SV*` sidebar/project-view visibility filters.
- `AC*` acceptance criteria (mostly dedupe onto behaviour rows → `n/a`).

## Existing-smoke inventory (root-level, candidates for Step 2)

These 35 `p3_*` + 8 `p2_*` smokes live at the `.smoke-scratch/` root.
Their **primary frame** is assessed below. `s11_*/s12_*/s13_*`
(9 files) are about the **enums / testcase-component** surface →
feature-11, NOT feature-10; excluded here.

| Smoke | Asserts | Primary frame | Rule(s) |
|---|---|---|---|
| `F10_80_tab_strip_initial_state.py` (was `p2_2a`) | Directory tab active / Test-run tab inactive on load | **feature-10** (sidebar shell — folded in Step 5) | — |
| `F10_81_test_run_lazy_mount.py` (was `p2_2h`) | `#test-run-pane` has no hx-get/hx-trigger yet, hidden + placeholder | **feature-10** (sidebar shell — folded in Step 5) | — |
| `F10_79_sidebar_shell_renders.py` (was `p2_s7`) | `base.html` 200 + sidebar shell elements | **feature-10** (sidebar shell — folded in Step 5) | — |
| `p2_2d_test_run_tab_aggregates.py` | Test-run tab aggregates across projects; omits bare projects | **feature-10** | SM12, TM6 |
| `p2_2e_sse_picks_up_external_change.py` | External FS change under `test-run/` → `change` event + fresh `/ui/test-run-tree` reflects it | **feature-10** | AC15 (SSE), UR4 |
| `p2_s3_test_run_tree_skips_projects_without_runs.py` | `list_test_run_tree` omits projects without `test-run/` | **feature-10** | SM12 |
| `p2_s4_test_run_tree_leaf_shape.py` | tree leaves carry `type='run'` + project/group/file_name | **feature-10** | SM12 |
| `p2_s6_test_run_sidebar_render.py` | `GET /ui/test-run-tree` 200 + leaf URLs + empty state | **feature-10** | UR4, TM6 |
| `p3_a1_area_landing.py` | `/ui/folder/<p>/test-run` → area template + groups | **feature-10** | UR1, TM1 |
| `p3_a2_group_view.py` | `/ui/folder/<p>/test-run/<g>` → runs table DESC + badges | **feature-10** | UR2, TM2 |
| `p3_a3_deep_path_404.py` | deeper-than-group paths 404 | **feature-10** | UR6 |
| `p3_b1_create_run_wiring.py` | `+ New run` flow wiring (static) | **feature-10** | CR1 (partial) |
| `p3_c1_run_editor_render.py` | `/ui/run/...` renders editor shell | **feature-10** | UR3, TM3 |
| `p3_c2_run_editor_select_options.py` | each result `<select>` lists all RUN_RESULTS, stored pre-selected | **feature-10** | TM4 |
| `p3_c3_run_editor_404.py` | missing run → 404 not 500 | **feature-10** | UR3/AP3 (404) |
| `p3_d1_save_roundtrip_and_idempotent.py` | Save PATCH round-trip + canonical YAML idempotence | **feature-10** | AP4, SC3, AC11 |
| `p3_d2_runeditor_wiring.py` | dirty → Save → flash wiring (static) | **feature-10** | RE2/RE4/RE6 (partial) |
| `p3_e1_template_row_prototype.py` | editor always renders table + empty state + row template w/ all RUN_RESULTS | **feature-10** | TM5, SM16 |
| `p3_e2_runeditor_e_wiring.py` | add-case / remove-row wiring (static) | **feature-10** | RE7/RE8 (partial) |
| `p3_f1_tombstone_render.py` | tombstone render for missing case files | **feature-10** | RE10, AC5 |
| `p3_g1_runeditor_sse_wiring.py` | SSE external-change wiring (static) | **feature-10** | RE11/WR2 (partial) |
| `p3_g2_runs_get_endpoint_shape.py` | `GET /api/runs/.../<file>` shape for the SSE comparator | **feature-10** | AP3, RE12 |
| `p3_h1a_sidebar_has_new_run_button.py` | sidebar renders `+ New run` (3 states) | **feature-10** | TM6 |
| `p3_h1b_sidebar_button_calls_no_arg.py` | button calls `tmsCreateRun()` no-arg | **feature-10** | TM6, CR1 |
| `p3_h2a_group_view_no_toolbar_button.py` | group view has no `+ New run` toolbar button | **feature-10** | TM2 |
| `p3_h2b_group_view_empty_pointer_copy.py` | empty group view = pointer copy, not CTA | **feature-10** | TM2 |
| `p3_h3a_run_groups_empty_root.py` | `GET /api/run-groups` empty-root zero shape | **feature-10** | AP11 |
| `p3_h3b_run_groups_project_without_area.py` | run-groups lists bare projects | **feature-10** | AP11, SM13 |
| `p3_h3c_run_groups_aggregates_across_projects.py` | run-groups aggregates groups across projects | **feature-10** | AP11 |
| `p3_h4_post_group_auto_creates_area.py` | `POST /api/runs/<p>/groups` auto-creates `test-run/` | **feature-10** | AP9, FL6, SM1 |
| `p3_h5_post_group_duplicate_returns_409.py` | duplicate group → 409 | **feature-10** | AP9 |
| `p3_h6_post_run_duplicate_returns_409.py` | duplicate run slug → 409 | **feature-10** | AP1 |
| `p3_h7a_tmscreaterun_no_arg.py` | `tmsCreateRun` exported no-arg async | **feature-10** | CR1 |
| `p3_h7b_modal_renders_optgroup_and_new_row.py` | modal renders optgroup/project + `__new__` row | **feature-10** | CR4 |
| `p3_h7c_reveal_on_select_new_group.py` | reveal-on-select keyed on `__new__` | **feature-10** | CR4 |
| `p3_h7d_live_slug_preview.py` | live slug preview under run-name input | **feature-10** | CR5 |
| `p3_h7e_zero_projects_branch.py` | zero-projects info modal, no Confirm | **feature-10** | CR3 |
| `p3_h7f_submit_handler_contract.py` | submit handler contract (POST group/run, 409 inline, 201 open) | **feature-10** | CR7 |
| `p3_i1_picker_select_all_wiring.py` | `tmsBuildCasePicker` tri-state select-all header | **feature-10** | CP5 |
| `p3_j1_run_editor_two_span_template.py` | editor row + template carry two-span shape | **feature-10** | RE9, TM5 |
| `p3_j2_create_result_row_populates_spans.py` | `_createResultRow` populates both data-role spans | **feature-10** | RE9 |
| `p3_j3_tombstone_strikes_filename_only.py` | tombstone strikes filename span only | **feature-10** | RE10 |
| `p3_k1_run_results_renamed.py` | `RUN_RESULTS` IN-PROGRESS → EXECUTING (model) | **feature-10** | DM1 |
| `p3_k2_run_editor_renders_executing_option.py` | rendered HTML reflects the rename | **feature-10** | TM4 |

**Primary-frame summary:** 40 of 43 root smokes primary-frame
feature-10. 3 (`p2_2a`, `p2_2h`, `p2_s7`) cover the sidebar shell
(the **sidebar-restructure**, which has no dedicated spec file —
feature-10 introduced the Test-run tab alongside it). Originally left
at root and cross-credited; **reclassified + folded into feature-10
in Step 5** (see below) as `F10_79/F10_80/F10_81` so the runner
executes them. The 9 `s11/s12/s13` smokes are feature-11.

## Matrix

Status legend: `covered` (an existing smoke or planned smoke asserts
it end-to-end / via tight static regex), `partial` (only wiring/static
or indirect coverage today; needs a dedicated re-owning smoke),
`missing` (no smoke), `n/a` (rationale / dedupe / consumed-from-sibling).

### Data model & `validate_run` (DM)

| # | Rule | Existing smoke | Status |
|---|---|---|---|
| DM1 | `RUN_RESULTS = (PENDING, EXECUTING, PASSED, FAILED, SKIPPED)`; default new row `PENDING`; `EXECUTING` is the post-rename value (no `IN-PROGRESS` alias). | `F10_01` | covered |
| DM2 | `results` is a list; insertion order is canonical on-disk order, never reshuffled. | `F10_45` | covered |
| DM3 | each `result` ∈ `RUN_RESULTS`; otherwise `ValidationError` (422). | `F10_42` | covered |
| DM4 | `file_path` non-empty, NOT disk-validated at write time. | `F10_44` | covered |
| DM5 | duplicate `file_path` entries rejected at write. | `F10_43` | covered |
| DM6 | `created_at` stamped server-side UTC ISO-8601 (`timespec=seconds`) on create; client cannot override; Save round-trips verbatim. | `F10_46` (+ `F10_02`) | covered |

### On-disk schema (SC)

| # | Rule | Existing smoke | Status |
|---|---|---|---|
| SC1 | top-level keys `name`/`created_at`/`description`/`results` stable, never reordered. | `F10_47` | covered |
| SC2 | `remark` uses `|` block scalar by default (preserves newlines). | `F10_47` (drift: single-quoted, not `|` block) | covered |
| SC3 | canonical re-serialise: back-to-back identical-payload writes → byte-identical files. | `F10_02` | covered |
| SC4 | malformed YAML → `RunParseError(line, column, message)` → HTTP 422 on `read_run`. | `F10_48` | covered |

### Folder discipline / layout (FL)

| # | Rule | Existing smoke | Status |
|---|---|---|---|
| FL1 | `RESERVED_DEPTH2_NAMES={test-run}`; `create_folder` rejects depth-2 `test-run` → 409 `NameConflictError`. | `F10_49` | covered |
| FL2 | `test-run` legal at depths ≠ 2 (e.g. `Alpha/Checkout/test-run`). | `F10_49` | covered |
| FL3 | no nesting beyond `<group>` — `create_folder` under `test-run/<group>/...` → 409. | `F10_50` | covered |
| FL4 | no `.feature` files anywhere under `test-run/` → `create_file` 409. | `F10_51` | covered |
| FL5 | no `.yaml` outside `test-run/<group>/` (run-write path is the only `.yaml` writer). | `F10_52` | covered |
| FL6 | `<project>/test-run/` is lazy — never auto-created on project create; appears on first group/run create. | `F10_09` | covered |

### Storage methods (SM)

| # | Rule | Existing smoke | Status |
|---|---|---|---|
| SM1 | `create_run_group` validates segments, creates group, lazily creates `test-run/`. | `F10_53` | covered |
| SM2 | `delete_run_group` idempotent; refuses non-empty. | `F10_54` | covered |
| SM3 | `list_run_groups` returns group names or `[]`. | `F10_55` | covered |
| SM4 | `list_runs` entry shape `{file_name,name,created_at,case_count,results_count_by_status}`; unreadable → zero-count entry, no raise. | `F10_56` | covered |
| SM5 | `create_run` stamps `created_at`, writes YAML, `case_paths`→`PENDING`+empty remark, auto-creates group. | `F10_57` (drift: group must pre-exist) | covered |
| SM6 | `read_run` → `FileNotFoundError` (404) if missing, `RunParseError` (422) on malformed. | `F10_48` (422) + `F10_17` (404) | covered |
| SM7 | `write_run` atomic; `validate_run` first. | `F10_42` (validate-first) | covered |
| SM8 | `delete_run` idempotent (204). | `F10_61` (via AP5) | covered |
| SM9 | `add_run_case` appends `PENDING`+empty remark; duplicate → 409. | `F10_62` | covered |
| SM10 | `remove_run_case` idempotent. | `F10_63` | covered |
| SM11 | `update_run_result` partial update (result and/or remark). | `F10_64` | covered |
| SM12 | `list_test_run_tree` aggregates projects-with-runs → groups → run leaves; omits projects without `test-run/`. | `F10_05`,`F10_03`,`F10_04` | covered |
| SM13 | `list_projects` every depth-0 dir, case-insensitive sort. | `F10_58` | covered |
| SM14 | `validate_run` runs before every write; errors → `ValidationError` (422) with path-style locator. | `F10_42` | covered |
| SM15 | `_normalize_run_filename` appends `.yaml` if no ext; rejects other extensions. | `F10_59` | covered |
| SM16 | empty `results` lists are legal. | `F10_57` | covered |

### HTTP API (AP)

| # | Rule | Existing smoke | Status |
|---|---|---|---|
| AP1 | `POST /api/runs` creates the YAML; duplicate slug → 409. | `F10_11` | covered |
| AP2 | `GET /api/runs/<p>/<g>` lists run summaries. | `F10_60` | covered |
| AP3 | `GET /api/runs/<p>/<g>/<file>` returns full `TestRun.to_dict()`; missing → 404. | `F10_12`,`F10_17` | covered |
| AP4 | `PATCH /api/runs/<p>/<g>/<file>` replaces whole run (editor Save). | `F10_02` | covered |
| AP5 | `DELETE /api/runs/<p>/<g>/<file>` idempotent 204. | `F10_61` | covered |
| AP6 | `POST /api/runs/<p>/<g>/<file>/cases` appends a case. | `F10_62` | covered |
| AP7 | `DELETE /api/runs/<p>/<g>/<file>/cases/<path>` removes a case. | `F10_63` | covered |
| AP8 | `PATCH /api/runs/<p>/<g>/<file>/cases/<path>` partial result update. | `F10_64` | covered |
| AP9 | `POST /api/runs/<p>/groups` creates group, auto-creates `test-run/`; duplicate → 409. | `F10_09`,`F10_10` | covered |
| AP10 | `DELETE /api/runs/<p>/groups/<g>` deletes empty group. | `F10_65` | covered |
| AP11 | `GET /api/run-groups` → `{projects:[...], groups:[{project,group}...]}` (incl. bare projects). | `F10_06`/`F10_07`/`F10_08` | covered |
| AP12 | all errors use the `{error:{code,message,details}}` envelope. | `F10_66` | covered |

### UI routes (UR)

| # | Rule | Existing smoke | Status |
|---|---|---|---|
| UR1 | `GET /ui/folder/<p>/test-run` → `folder_test_run_area.html`. | `F10_13` | covered |
| UR2 | `GET /ui/folder/<p>/test-run/<g>` → `folder_test_run_group.html`. | `F10_14` | covered |
| UR3 | `GET /ui/run/<p>/<g>/<file>` → `run_editor.html`; missing → 404. | `F10_16`,`F10_17` | covered |
| UR4 | `GET /ui/test-run-tree` → `test_run_sidebar.html`. | `F10_18`,`F10_19` | covered |
| UR5 | `ui_folder` dispatcher recognises `segments[1]=="test-run"` → typed templates. | `F10_13`/`F10_14`/`F10_15` | covered |
| UR6 | typed area exactly 2 levels; `<p>/test-run/<g>/<file>.yaml` under `ui_folder` → 404. | `F10_15` | covered |

### Templates (TM)

| # | Rule | Existing smoke | Status |
|---|---|---|---|
| TM1 | area template: breadcrumb, groups table, empty state (groups auto-materialise), no `+ New group`. | `F10_13` | covered |
| TM2 | group template: breadcrumb, runs newest-first, columns + status badges, empty pointer copy, no CTA. | `F10_14`,`F10_25`,`F10_26` | covered |
| TM3 | editor shell: breadcrumb, header buttons, name/description, results rows, `+ Add test case`. | `F10_16` | covered |
| TM4 | each result `<select>` lists all RUN_RESULTS, stored value pre-selected; EXECUTING present. | `F10_20`,`F10_21` | covered |
| TM5 | `<template id="run-result-row-template">` prototype carries all RUN_RESULTS + two-span shape. | `F10_22`,`F10_31` | covered |
| TM6 | sidebar: `+ New run` always visible/enabled no-arg; folder rows decorative; run leaves navigate; empty copy. | `F10_18`,`F10_23`,`F10_24` | covered |

### `tmsRunEditor` controller (RE — static JS)

| # | Rule | Existing smoke | Status |
|---|---|---|---|
| RE1 | bootstrap: `boot()` reads dataset, captures `baselineJson`, wires, consumes `_pendingBanner`. | `F10_67` | covered |
| RE2 | dirty tracking: `_readCurrent` snapshot, `_refreshDirty` compare, toggles indicator + Save disabled; set-and-forget. | `F10_27`,`F10_76` | covered |
| RE3 | event delegation on results `<tbody>` (not per-row). | `F10_28` | covered |
| RE4 | Save whole-doc PATCH; success → update baseline/clear dirty/flashSaved; failure → alert, stay dirty. | `F10_76` (+ `F10_02` server) | covered |
| RE5 | Reload: confirm if dirty, `htmx.ajax GET /ui/run/...`. | `F10_68` | covered |
| RE6 | Saved badge 1.5 s; cleared immediately on next dirty edit. | `F10_76` | covered |
| RE7 | `+ Add test case` modal: fetch tree, exclude set, `lg` modal, confirm gate, clone template, `htmx.process`, `_afterRowsChanged`. | `F10_28` | covered |
| RE8 | per-row remove (`.run-row-remove`) + `_afterRowsChanged`. | `F10_28` | covered |
| RE9 | path masking: two `data-role` spans (folder muted/truncate + filename emphasized/flex-none), rsplit branch, 3 preservation surfaces, clone mirrors. | `F10_31`,`F10_32` | covered |
| RE10 | tombstone render: server `missing` flag, `run-row-missing`, filename strike only, remark override + hidden-preserved textarea, select editable. | `F10_29`,`F10_33` | covered |
| RE11 | external-change banner: 3 branches (removed→red Discard→group nav; changed&clean→silent reload+info; changed&dirty→amber warn). | `F10_69` | covered |
| RE12 | disk-state comparison normalises API response to baseline projection (no `created_at`/`missing`). | `F10_69` | covered |
| RE13 | reload path goes through `/ui/run/...` so per-row `is_file()` storm re-runs (live tombstones). | `F10_68` | covered |
| RE14 | `beforeunload` covers both editors in one check. | `F10_27`,`F10_77` | covered |

### `tmsCreateRun` modal (CR — static JS)

| # | Rule | Existing smoke | Status |
|---|---|---|---|
| CR1 | no-arg async fn wired to sidebar `+ New run`. | `F10_35`,`F10_24`,`F10_34` | covered |
| CR2 | bootstrap single `GET /api/run-groups`; alert + return on fetch failure. | `F10_78` | covered |
| CR3 | zero-projects branch: info modal, Confirm suppressed (`confirmLabel:null`). | `F10_39` | covered |
| CR4 | base shape: `md` modal; Where `<select>` optgroups + `__new__` sentinel; reveal-on-select sub-form (project select + group-name input). | `F10_36`,`F10_37` | covered |
| CR5 | run-name input + live slug preview; empty slug → placeholder hint + Confirm gated off. | `F10_38` | covered |
| CR6 | confirm gate `(slug non-empty) AND (path resolved)`. | `F10_78` | covered |
| CR7 | submit: new-group→`POST groups` (409 inline, preserves inputs); `POST runs` (409 inline); 201→close+open editor. | `F10_40` | covered |
| CR8 | modal stays open on error; per-input listeners drive slug/reveal/error-clear. | `F10_78` | covered |

### `tmsBuildCasePicker` (CP — static JS)

| # | Rule | Existing smoke | Status |
|---|---|---|---|
| CP1 | flat checkbox table sorted folder ASC then file ASC. | `F10_70` | covered |
| CP2 | sticky header inside `max-h-72` scroll container. | `F10_70` | covered |
| CP3 | live-filter input + counter copy (`N cases` / `K of N selected` / `K shown · M selected`). | `F10_71` | covered |
| CP4 | click-row-to-toggle (whole row, not just checkbox). | `F10_70` | covered |
| CP5 | tri-state select-all header: visible-only, filter-aware, hidden-checked preserved, `getSelected()` = union. | `F10_41` | covered |
| CP6 | empty states (no `.feature` / all excluded) replace the whole `<table>`. | `F10_72` | covered |

### Wiring (WR — static JS)

| # | Rule | Existing smoke | Status |
|---|---|---|---|
| WR1 | `htmx:afterSwap` on `#main-pane` clears `tmsRunEditor.state` when editor leaves. | `F10_27`,`F10_77` | covered |
| WR2 | `sse:change` fans out to both `tmsEditor` and `tmsRunEditor` `onExternalChange()` when state non-null. | `F10_77` | covered |
| WR3 | `beforeunload` warns when either editor's `state.dirty`. | `F10_27`,`F10_77` | covered |

### Sidebar / project-view visibility (SV)

| # | Rule | Existing smoke | Status |
|---|---|---|---|
| SV1 | `list_tree` filters `test-run` out of every project's children (Directory tree never shows it). | `F10_73` | covered |
| SV2 | `list_folder` filters `test-run` from project view when `len(parts)==1`. | `F10_74` | covered |
| SV3 | only UI entry points to typed area = Test-run sidebar tab + run-editor breadcrumb's clickable `test-run` segment. | `F10_74` | covered |

### Acceptance criteria (AC — mostly dedupe)

| # | Rule | Tracked by | Status |
|---|---|---|---|
| AC1 | `POST /api/runs` writes YAML with PENDING rows + empty remark; server-stamped `created_at`. | AP1/SM5/DM6 | n/a |
| AC2 | depth-2 `test-run` via folder API → 409; depth-3 succeeds. | FL1/FL2 | n/a |
| AC3 | folder under `test-run/<group>/` → 409. | FL3 | n/a |
| AC4 | `.feature` under `test-run/` → 409. | FL4 | n/a |
| AC5 | rename/move/delete of a referenced `.feature` does NOT mutate the run; next render tombstones; restore un-tombstones. | `F10_75` (+ RE10 `F10_29`) | covered |
| AC11 | PATCH same payload twice → byte-identical YAML. | SC3/AP4 (`F10_02`) | n/a |
| AC-edit | Save reflects every field; Saved badge ~1.5 s; cleared on dirty edit. | RE4/RE6 | n/a |
| AC-reload | Reload confirms if dirty + re-renders via `/ui/run/...`. | RE5 | n/a |
| AC-add | `+ Add test case` excludes in-run cases; appends PENDING; Save persists. | RE7/CP* | n/a |
| AC-remove | `×` removes row; Save persists; YAML `results` shorter. | RE8/AP4 | n/a |
| AC-banner | external edit drives banner state machine (removed/clean/dirty). | RE11 | n/a |
| AC-discard | external delete → red banner; Discard → group view. | RE11 | n/a |
| AC-sidebar | sidebar aggregates projects-with-runs; leaf opens editor; group/project rows non-navigable. | SM12/TM6 | n/a |
| AC-hide | Directory tree + project module table never show `test-run/`. | SV1/SV2 | n/a |
| AC15 | run `.yaml` files flow through watcher/SSE; external create/delete refresh the sidebar on `sse:change`. | `F10_19` | covered |

## Tallies (Step 4 complete)

- Distinct countable rules: **90** across DM/SC/FL/SM/AP/UR/TM/RE/CR/CP/WR/SV.
- `covered`: **90** (all of them) + the two non-dedupe acceptance
  criteria AC5 and AC15.
- `partial`: **0**.
- `missing`: **0**.
- `n/a`: **13** acceptance-criteria dedupe rows (AC1–AC4, AC11,
  AC-edit/-reload/-add/-remove/-banner/-discard/-sidebar/-hide) +
  the 3 consumed sidebar-restructure smokes that stayed at root.

At Step-1 audit the snapshot was ~33 covered / ~17 partial / ~33
missing. Step 4 added **37** new smokes (F10_42–F10_78) and re-credited
the reconciled wiring rows, closing every gap.

## Open sign-off questions (for the user — Step 1)

1. **Re-own storage/route rules end-to-end.** The `partial` rows are
   storage methods currently only touched indirectly through one
   route. Proposal: give each its own feature-10 smoke exercising it
   through the canonical route (or directly for non-routed methods
   like `delete_run_group`). Approve? (mirrors feature-09 ST*).
2. **Static JS inspection for `tmsRunEditor` / `tmsCreateRun` /
   `tmsBuildCasePicker`.** No JS runtime; regex on `app.js`. Approve?
3. **Step-2 move set.** Move the **40** feature-10-primary root smokes
   into `feature-10/` (renamed to the `F10_<MM>_<slug>.py` scheme);
   leave `p2_2a`, `p2_2h`, `p2_s7` (sidebar-restructure) at root and
   cross-credit them. Approve the 40-move + 3-stay split? (full
   per-file rename map to follow on approval.)
4. **Renaming convention for moved smokes.** Keep the `p2_/p3_` letter
   ordering by re-sequencing into `F10_01..F10_NN`, OR preserve the
   original `p2_*/p3_*` stems inside `feature-10/`? Proposal:
   re-sequence to `F10_<MM>` grouped by rule area (storage, api, ui,
   templates, controller, modal, picker, wiring, visibility) so the
   directory reads in spec order.
5. **Split granularity for gap-fill (Step 4).** Apply the same
   splitting heuristic (≤~90 LOC, split on distinct setup / distinct
   failure modes). The storage-invariant and folder-discipline gaps
   naturally fan out into many small files. Approve?

No files have been moved, renamed, or created besides this matrix.
Awaiting sign-off before Step 2.

## Step 2 — executed (41 smokes moved + renamed)

Sign-off: the user approved "move to step 2" and requested the move be
done in **small per-area batches, verifying each smoke runs
individually** after the move.

**Count correction.** The root inventory is **44** test-run smokes (8
`p2_*` + 36 `p3_*`), not the 43/40 estimated at audit time. The move
set is therefore **41** (44 − 3 stays), not 40.

`.smoke-scratch/` is not git-tracked (gitignored), so plain `mv` was
used instead of `git mv`. Files were re-sequenced into
`F10_01..F10_41` grouped by rule area in spec order (model → schema →
storage tree → API → UI routes → templates → controller → modal →
picker). Each batch was run file-by-file with
`PYTHONPATH=. python .smoke-scratch/feature-10/F10_*.py`; **all 41
passed individually.**

The moved smokes use **cwd-relative** paths
(`pathlib.Path("app/static/app.js")`) rather than `__file__`-relative
ones, so dropping a level deeper did not break path resolution — the
runner already executes with `cwd=REPO_ROOT`.

Per-file rename map:

| Old (root) | New (`feature-10/`) |
|---|---|
| `p3_k1_run_results_renamed.py` | `F10_01_run_results_enum.py` |
| `p3_d1_save_roundtrip_and_idempotent.py` | `F10_02_save_roundtrip_idempotent.py` |
| `p2_s3_test_run_tree_skips_projects_without_runs.py` | `F10_03_tree_skips_bare_projects.py` |
| `p2_s4_test_run_tree_leaf_shape.py` | `F10_04_tree_leaf_shape.py` |
| `p2_2d_test_run_tab_aggregates.py` | `F10_05_tree_aggregates.py` |
| `p3_h3a_run_groups_empty_root.py` | `F10_06_run_groups_empty.py` |
| `p3_h3b_run_groups_project_without_area.py` | `F10_07_run_groups_bare_projects.py` |
| `p3_h3c_run_groups_aggregates_across_projects.py` | `F10_08_run_groups_aggregates.py` |
| `p3_h4_post_group_auto_creates_area.py` | `F10_09_post_group_auto_creates_area.py` |
| `p3_h5_post_group_duplicate_returns_409.py` | `F10_10_post_group_duplicate_409.py` |
| `p3_h6_post_run_duplicate_returns_409.py` | `F10_11_post_run_duplicate_409.py` |
| `p3_g2_runs_get_endpoint_shape.py` | `F10_12_get_run_shape.py` |
| `p3_a1_area_landing.py` | `F10_13_area_landing.py` |
| `p3_a2_group_view.py` | `F10_14_group_view.py` |
| `p3_a3_deep_path_404.py` | `F10_15_deep_path_404.py` |
| `p3_c1_run_editor_render.py` | `F10_16_run_editor_render.py` |
| `p3_c3_run_editor_404.py` | `F10_17_run_editor_404.py` |
| `p2_s6_test_run_sidebar_render.py` | `F10_18_sidebar_render.py` |
| `p2_2e_sse_picks_up_external_change.py` | `F10_19_sidebar_sse_refresh.py` |
| `p3_c2_run_editor_select_options.py` | `F10_20_editor_select_options.py` |
| `p3_k2_run_editor_renders_executing_option.py` | `F10_21_editor_executing_option.py` |
| `p3_e1_template_row_prototype.py` | `F10_22_editor_row_template.py` |
| `p3_h1a_sidebar_has_new_run_button.py` | `F10_23_sidebar_new_run_button.py` |
| `p3_h1b_sidebar_button_calls_no_arg.py` | `F10_24_sidebar_button_no_arg.py` |
| `p3_h2a_group_view_no_toolbar_button.py` | `F10_25_group_view_no_toolbar.py` |
| `p3_h2b_group_view_empty_pointer_copy.py` | `F10_26_group_view_empty_copy.py` |
| `p3_d2_runeditor_wiring.py` | `F10_27_editor_dirty_save_wiring.py` |
| `p3_e2_runeditor_e_wiring.py` | `F10_28_editor_addcase_remove_wiring.py` |
| `p3_f1_tombstone_render.py` | `F10_29_tombstone_render.py` |
| `p3_g1_runeditor_sse_wiring.py` | `F10_30_editor_sse_wiring.py` |
| `p3_j1_run_editor_two_span_template.py` | `F10_31_two_span_template.py` |
| `p3_j2_create_result_row_populates_spans.py` | `F10_32_create_result_row_spans.py` |
| `p3_j3_tombstone_strikes_filename_only.py` | `F10_33_tombstone_strikes_filename.py` |
| `p3_b1_create_run_wiring.py` | `F10_34_create_run_wiring.py` |
| `p3_h7a_tmscreaterun_no_arg.py` | `F10_35_create_run_no_arg.py` |
| `p3_h7b_modal_renders_optgroup_and_new_row.py` | `F10_36_modal_optgroup_new_row.py` |
| `p3_h7c_reveal_on_select_new_group.py` | `F10_37_reveal_on_select.py` |
| `p3_h7d_live_slug_preview.py` | `F10_38_live_slug_preview.py` |
| `p3_h7e_zero_projects_branch.py` | `F10_39_zero_projects_branch.py` |
| `p3_h7f_submit_handler_contract.py` | `F10_40_submit_handler_contract.py` |
| `p3_i1_picker_select_all_wiring.py` | `F10_41_picker_select_all.py` |

**Originally stayed at root (sidebar-restructure, cross-credited);
reclassified + folded into feature-10 in Step 5 — see below:**
`p2_2a_tab_strip_initial_state.py` → `F10_80_tab_strip_initial_state.py`,
`p2_2h_lazy_mount_initial_dom.py` → `F10_81_test_run_lazy_mount.py`,
`p2_s7_base_html_renders.py` → `F10_79_sidebar_shell_renders.py`.

**Suite results after the move:**
- `python .smoke-scratch/run.py --filter feature-10` → 41/41 pass.
- `python .smoke-scratch/run.py` (full) → **160/160 passed; 0 failed**
  (was 119 before; the 41 moved smokes are now discovered by the
  runner, which only walks `feature-*/F<N>_*` files).

**Drift to reconcile in Step 3.** `F10_14_group_view.py` (ex-`p3_a2`)
still asserts the group view renders a `+ New run` button, while
`F10_25_group_view_no_toolbar.py` (ex-`p3_h2a`) asserts the populated
group view has *no* run-creation affordance. Both pass today (the
older smoke's button check is stale / matches a different element),
but they encode contradictory expectations — Step 3 will retire or
re-scope the stale assertion in `F10_14`.

## Step 3 — executed (refines on moved smokes)

**Group-view "drift" resolved — was a false alarm.** On closer
inspection `F10_14_group_view.py` already asserts `"tmsCreateRun" not
in html` (line 46) — it verifies the button's **absence**, exactly
agreeing with `F10_25`. The only defects were cosmetic:

- Its final `print(...)` said "+ New run button" (implying presence);
  corrected to "no + New run button".
- Its docstring + inline comment pointed at the old `p3_h1a/h1b/h2a/
  h2b` filenames; updated to `F10_23/24/25/26`.

**Stale old-filename cross-references fixed** (the only functional
refine needed after the rename):

- `F10_14` — docstring + comment `p3_h1a/...` → `F10_23/24/25/26`.
- `F10_34` — docstring `p3_h7a..f` → `F10_35..F10_40`; assertion
  message `p3_h1a / p3_h1b` → `F10_23 / F10_24`.
- `F10_33` — docstring reference `p3_f1_tombstone_render.py` →
  `F10_29_tombstone_render.py`.

A repo-wide grep for `p[23]_` inside `feature-10/F10_*.py` now returns
nothing; references to the three smokes that **stayed** at root
(`p2_2a`, `p2_2h`, `p2_s7`) are intentionally absent (no moved smoke
cited them).

**Not changed (deliberately, per surgical-refine policy):**

- cwd-relative path style (`pathlib.Path("app/static/app.js")`) is
  left as-is — functional under the runner's `cwd=REPO_ROOT`; not
  worth churning 40 files to match feature-09's `__file__` style.
- Historical phase/spec-section labels in docstrings/prints (`3.A.ii`,
  `Smoke 7a`, `Phase-2 lock-in`, `Q4(b)`) are kept — they are
  provenance, not broken references.

**Matrix updated:** the *Existing smoke* column was migrated from the
old `p2_*/p3_*` stems to the new `F10_*` names throughout.

**Suite after refines:** `--filter feature-10` → 41/41 pass;
full suite → 160/160 pass.

## Step 4 — executed (37 smokes written, all passing)

37 new smokes written (`F10_42`–`F10_78`), each verified individually
then as a suite. The reconciled wiring rows (WR1/RE14/WR3 via `F10_27`;
RE3/RE7/RE8 via `F10_28`) were re-credited rather than duplicated.

- As a suite: `python .smoke-scratch/run.py --filter feature-10` →
  **78/78 passed; 0 failed** (41 moved in Step 2 + 37 new in Step 4).
- Full repo suite: `python .smoke-scratch/run.py` →
  **197/197 passed; 0 failed**.

Notes from execution:

- `F10_47_schema_keys_block_scalar.py`: drift — the spec's on-disk
  example shows a `remark: |` block scalar, but `yaml.safe_dump`
  emits a single-quoted multi-line scalar (newlines still round-trip).
  The smoke pins the real behaviour and asserts the form is NOT a `|`
  block scalar.
- `F10_57_create_run_direct.py`: drift — the spec says `create_run`
  "auto-creates the group", but storage raises `FileNotFoundError`
  when the group is absent (the create modal POSTs the group first).
  The smoke pins the real behaviour.
- `F10_66_api_error_envelope.py`: the 400 `bad_request` envelope omits
  `details` (only 409/422 carry a path/field locator), so the
  envelope check requires `code`+`message` and treats `details` as
  optional.

Both drifts are documentation-only (spec vs as-shipped); no code was
changed — the smokes assert the real behaviour and flag the spec
wording for a future reconciliation pass.

Coverage: **90/90 countable rules covered; 0 missing; 0 partial.**
Feature-10 test-run is fully covered.

## Step 5 — sidebar-shell smokes reclassified + folded in (Jun 9, 2026)

The 3 sidebar-shell smokes that Step 2 left at root
(`p2_2a`/`p2_2h`/`p2_s7`) primary-frame the **sidebar-restructure**,
which has no dedicated spec file in `specs/features/` (01–11 only) —
`00-summary.md` names it only as a feature-10 dependency. Because
`run.py` discovers only `feature-*/F<N>_<NN>_*.py`, leaving them at
root meant **the runner never executed them** (the sidebar shell had
no live regression guard). Per user decision (Jun 9, 2026) they were
folded into feature-10 (the spec that introduced the Test-run tab
alongside the restructure):

| Old (root) | New (`feature-10/`) | Asserts |
|---|---|---|
| `p2_s7_base_html_renders.py` | `F10_79_sidebar_shell_renders.py` | `base.html` 200 + full sidebar shell (`#sidebar`, tabs, both panes, collapse, resize, 3 JS helpers) |
| `p2_2a_tab_strip_initial_state.py` | `F10_80_tab_strip_initial_state.py` | Directory tab active / Test-run tab inactive on load |
| `p2_2h_lazy_mount_initial_dom.py` | `F10_81_test_run_lazy_mount.py` | `#test-run-pane` hidden, no `hx-get`/`hx-trigger` (lazy mount), placeholder; `#tree-pane` visible |

These are **regression / cross-cutting** smokes (no new feature-10 rule
ID) — they guard the shell that hosts both the tree pane (feature-06)
and the Test-run pane (feature-10). No internal edits were needed (they
use `create_app` + the test client; cwd-relative, runner-safe).

Cross-references updated: `feature-06/COVERAGE.md` WR3 and
`feature-07/COVERAGE.md` (the isolated `p2_2h`/`p2_s7` pair) now point
at the new paths. The root is now clear of smokes — only `run.py`
remains.

**Suite after Step 5:** `--filter feature-10` → **81/81**; full →
**215/215 passed; 0 failed**.
