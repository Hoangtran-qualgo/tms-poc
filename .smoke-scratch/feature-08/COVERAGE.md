# Feature 08 — File editor — coverage matrix

Spec source: `specs/features/08-feature-file-editor-NEW.md`
Source files in scope:
- `app/templates/file_editor.html` (template; 207 LOC).
- `app/static/app.js`, `tmsEditor` object @ lines ~1534–2922 (~1400 LOC of controller).
- `app/server.py`, `ui_file` route + `_folder_crumbs` helper (`_folder_crumbs` already covered by feature-07 SH1).

## Method

Same as previous features:

- Enumerate rules from the spec with a stable ID per rule.
- One smoke per rule (or per tightly-coupled cluster) under
  `.smoke-scratch/feature-08/F08_<MM>[a-z]?_<slug>.py`.
- Each smoke prints `PASS <id>: <invariant>` and is independently
  runnable.
- Rules headed `## Public surface` → `RT*` (route) / `TP*` (template) /
  `W*` (wiring).
- Rules headed `## Invariants & rules` → grouped by sub-heading:
  `B*` (bootstrap), `D*` (dirty), `TS*` (tab switching),
  `CL*` (cleanup), `SS*` (structured save), `SR*` (raw save),
  `RN*` (rename), `MV*` (move), `RL*` (reload), `EB*` (external
  banner).
- Rules under `## Acceptance criteria` → `AC*`.

Per the **feature-04 Step-1 sign-off** (re-confirmed here): smokes
do **not** spin up a JS runtime. Pure-JS controller rules
(tab-switch confirm, cleanup, banner branches, `beforeunload`, etc.)
are covered by **static regex inspection** of `app/static/app.js`
function bodies; HTTP round-trips use the Flask test client
end-to-end where the rule is observable through the
`/ui/file/<p>` or `/api/files/...` surfaces.

A row is `covered` when:
- An end-to-end render or HTTP round-trip can reach it, OR
- The pure-JS body has a tight, spec-anchored regex assertion in
  the corresponding `F08_*.py` file.

## Matrix

| # | Rule | Spec § | Smoke file | Status |
|---|---|---|---|---|
| RT1 | `GET /ui/file/<path:p>` (`ui_file`): for `.feature` paths renders `file_editor.html` with `file_path`, `crumbs`, `file_name`, `feature = Feature.to_dict()`, `raw = read_raw()`. Non-`.feature` → `unsupported.html`. Parse errors hit the UI catch-all `Exception` handler → **500** (spec updated to match; the 422 `parse_error` envelope is the JSON API surface, not this HTML route). | Public surface → Route | `F08_01_route.py` | covered |
| TP1 | Topbar buttons: breadcrumb, `#dirty-indicator`, `#saved-indicator`, `#btn-rename`, `#btn-move`, `#btn-reload`, `#btn-save`. | Public surface → Template | `F08_02_topbar.py` (+ cross-credit `F05_03_ui_gaps.py`) | covered |
| TP2 | Banner slot `#editor-banner`, empty by default; populated by `tmsEditor._showBanner`. | Public surface → Template | `F08_03_banner_slot.py` | covered |
| TP3 | Tabs `#tab-btn-structured`, `#tab-btn-raw`. | Public surface → Template | `F08_04_tabs.py` | covered |
| TP4 | Structured tab content: feature description textarea, feature-tag chips, background card (steps + `+ Add background step`), scenario card (kind toggle, name, tags chips, steps, examples). | Public surface → Template | `F08_05_structured_tab.py` (+ cross-credit `feature-11/F11_08_editor_scaffold.py` step 4) | covered |
| TP5 | Raw tab: textarea, error display (`#raw-error`), `#btn-save-raw`. | Public surface → Template | `F08_06_raw_tab.py` | covered |
| TP6 | Embedded JSON payload `#editor-data` (`type="application/json"`) carrying `path`, `file_name`, `feature`, `raw`; consumed by `tmsEditor.boot()` via `JSON.parse(textContent)`. | Public surface → Template | `F08_07_editor_data_payload.py` (+ cross-credit `F11_08` step 5 + `F11_09` step 6) | covered |
| W1 | `htmx:afterSwap` on `#main-pane` clears `tmsEditor.state` when the main pane swaps to anything other than the editor. | Public surface → Wiring | `F08_08_wiring.py` | covered |
| W2 | `document.body` `sse:change` listener calls `tmsEditor.onExternalChange()` whenever the page receives a `change` SSE event AND `tmsEditor.state` is non-null. | Public surface → Wiring | `F08_08_wiring.py` | covered |
| B1 | `tmsBootEditor()` is called by `file_editor.html` after the partial is swapped in. | Invariants → Bootstrap | `F08_09_bootstrap.py` | covered |
| B2 | `boot()` reads `#editor-data`, hydrates `state = {path, file_name, feature, raw, snapshotJson, snapshotRaw, dirty: false, tab: "structured"}`. The two snapshots drive external-change detection. | Invariants → Bootstrap | `F08_09_bootstrap.py` | covered |
| D1 | Every editable widget calls `this.markDirty(true)` on change. | Invariants → Dirty tracking | `F08_10a_dirty_static.py` | covered |
| D2 | `markDirty(d)` toggles `#dirty-indicator`, recomputes Save button enabled state, clears the `Saved` badge. | Invariants → Dirty tracking | `F08_10a_dirty_static.py` | covered |
| D3 | Save button is **disabled** when `Feature.description` is empty / whitespace-only. | Invariants → Dirty tracking | `F08_10b_save_disabled_empty_desc.py` | covered |
| D4 | `beforeunload` warns when the buffer is dirty. | Invariants → Dirty tracking | `F08_10a_dirty_static.py` | covered |
| TS1 | `state.tab ∈ {"structured", "raw"}`; visible content swaps but buffer (`state.feature` + `state.raw`) persists across tab switches **iff** the buffer is clean. | Invariants → Tab switching | `F08_11_tab_switch.py` | covered |
| TS2 | If `state.dirty` when the user clicks the other tab, `switchTab` shows `confirm("You have unsaved changes in the current tab. Switching tabs will discard them. Continue?")`. Cancel → abort. OK → reset to snapshots (both `feature` and `raw`), `markDirty(false)`, both tabs re-render, then switch proceeds. No merge. | Invariants → Tab switching | `F08_11_tab_switch.py` | covered |
| TS3 | `save()` dispatches to `saveRaw()` when `state.tab === "raw"`. | Invariants → Tab switching | `F08_11_tab_switch.py` (+ cross-credit `F05_02_ui_triggers.py` UI4) | covered |
| CL1 | `cleanupBuffer` drops any step whose `text` is empty / whitespace-only. | Invariants → Cleanup | `F08_12_cleanup.py` | covered |
| CL2 | `cleanupBuffer` drops any examples row consisting entirely of empty cells (header preserved). | Invariants → Cleanup | `F08_12_cleanup.py` | covered |
| CL3 | For each step's `data_table`: if every row (header AND body) is all-empty → `data_table = null`. Else keep the header and filter all-empty body rows; header-with-content but zero body rows stays as `[header]`. | Invariants → Cleanup | `F08_12_cleanup.py` | covered |
| CL4 | Outline-only refusal: if `kind === "outline"` AND `examples.length === 0` after row filter, abort save with `alert("Cannot save: An outline must have at least one Examples block.")`. Outline blocks with empty rows (but with a header) are NOT rejected client-side. | Invariants → Cleanup | `F08_12_cleanup.py` | covered |
| SS1 | `save()`: if `state.tab === "raw"` → dispatch to `saveRaw()`. | Invariants → Save flow (structured) | duplicates TS3; tracked there | n/a |
| SS2 | `save()` runs `cleanupBuffer()`; on error, shows `alert("Cannot save: …")` and aborts (no inline error display on the structured path). | Invariants → Save flow (structured) | `F08_13_save_flow.py` | covered |
| SS3 | After cleanup, save re-renders steps + examples so user sees the cleaned buffer before PATCH. | Invariants → Save flow (structured) | `F08_13_save_flow.py` | covered |
| SS4 | PATCH `/api/files/<state.path>` with `JSON.stringify(state.feature)`. | Invariants → Save flow (structured) | `F08_13_save_flow.py` (+ cross-credit `F05_02_ui_triggers.py` UI4) | covered |
| SS5 | On 2xx: `await _refreshFromDisk()` (refetches `/api/files/<p>` and `/api/files/<p>/raw`, refreshes `state.feature`, `state.raw`, both snapshots, `markDirty(false)`, re-renders both tabs); then `flashSaved()` for the 1.5 s badge. | Invariants → Save flow (structured) | `F08_13_save_flow.py` | covered |
| SS6 | On non-2xx: `alert("Save failed: " + (server error message || statusText))`. Buffer stays dirty (no refresh, no `markDirty(false)`). | Invariants → Save flow (structured) | `F08_13_save_flow.py` | covered |
| SR1 | `saveRaw()`: `hideRawError()`, then PUT `/api/files/<state.path>/raw` with `state.raw` as `text/plain`. | Invariants → Save flow (raw) | `F08_14_save_raw_flow.py` (+ cross-credit `F05_02_ui_triggers.py` UI5) | covered |
| SR2 | Server parses + re-serialises. On 422 (`parse_error` / `validation_error`), response includes `details.line` / `details.column` for parse errors; `showRawError` renders the formatted message inline at `#raw-error` (`"Line N, col M: <message>"` for parse errors; plain message otherwise). | Invariants → Save flow (raw) | `F08_14_save_raw_flow.py` | covered |
| SR3 | On 2xx: `await _refreshFromDisk()` so the structured tab also reflects canonical form; `flashSaved()`. | Invariants → Save flow (raw) | `F08_14_save_raw_flow.py` | covered |
| RN1 | `rename()` uses `window.prompt` (legacy v1; create uses `tmsOpenModal`, rename does not). | Invariants → Rename | `F08_15_rename.py` (strict per Step-1 sign-off Q5) | covered |
| RN2 | PATCH `/api/files/<p>/rename` with `{file_name}`. | Invariants → Rename | `F08_15_rename.py` (+ cross-credit `F05_02_ui_triggers.py` UI2) | covered |
| RN3 | On success, navigates to `/ui/file/<newpath>` via `htmx.ajax(...)`. | Invariants → Rename | `F08_15_rename.py` | covered |
| MV1 | `move()` confirms when `state.dirty` (`"Discard unsaved changes and move the file?"`). | Invariants → Move | `F08_16_move.py` | covered |
| MV2 | Fetches `/api/tree`, walks the result to collect every folder at depth `2..MAX_FOLDER_DEPTH`, opens `tmsOpenModal` with `<select>` (current parent disabled, prompt option keeps Confirm disabled until a real target is picked). | Invariants → Move | `F08_16_move.py` | covered |
| MV3 | PATCH `/api/files/<p>/move` with `{parent}`. | Invariants → Move | `F08_16_move.py` (+ cross-credit `F05_02_ui_triggers.py` UI3) | covered |
| MV4 | On success, navigates to the file at its new path via `htmx.ajax('GET', '/ui/file/<newpath>', ...)`. | Invariants → Move | `F08_16_move.py` | covered |
| MV5 | On failure, error renders inline in the modal so the user can correct + retry. | Invariants → Move | `F08_16_move.py` | covered |
| MV6 | A project `<select>` defaults to the source file's current project (`segments[0]`); the walker also collects depth-1 folders as projects. | Move modal enhancement (Jun 11, 2026) | `F08_16_move.py` | covered |
| MV7 | The folder `<select>` is scoped to the selected project; option text is the project-relative path (prefix stripped) while the option value stays the full path. | Move modal enhancement (Jun 11, 2026) | `F08_16_move.py` | covered |
| MV8 | On success, the directory tree is refreshed deterministically via `tmsRefreshTreePane('tree-pane')` (not only the SSE `change` event). | Move modal enhancement (Jun 11, 2026) | `F08_16_move.py` | covered |
| RL1 | `reload()` confirms when `state.dirty` (`"Discard unsaved changes and reload from disk?"`). | Invariants → Reload | `F08_17_reload.py` | covered |
| RL2 | Calls `_refreshFromDisk()` (shared with the post-save reload). | Invariants → Reload | `F08_17_reload.py` | covered |
| RL3 | Clears banner, raw-error region, lingering `Saved` badge. | Invariants → Reload | `F08_17_reload.py` | covered |
| RL4 | Failure surfaces via `alert("Reload failed: …")`. | Invariants → Reload | `F08_17_reload.py` | covered |
| EB1 | **File removed on disk** → red error banner: "This file was removed on disk." with `Discard` action only. | Invariants → External-change banner | `F08_18_external_banner.py` | covered |
| EB2 | **File changed AND buffer NOT dirty** → silently overwrite snapshots + re-render; show dismissable info banner "File was updated externally; the editor reloaded." | Invariants → External-change banner | `F08_18_external_banner.py` | covered |
| EB3 | **File changed AND buffer dirty** → amber warn banner "File changed externally while you have unsaved changes." with two actions: `Reload (discard mine)` and `Keep editing`. | Invariants → External-change banner | `F08_18_external_banner.py` | covered |
| EB4 | Save button is **not** explicitly disabled while the banner is up (the editor's validation gates indirectly enforce the same effect). | Invariants → External-change banner | `F08_18_external_banner.py` | covered |
| AC1 | Opening a parseable `.feature` shows the structured tab by default, populated from `Feature.to_dict()`, with `Save` disabled until the description is non-empty. | Acceptance criteria | `F08_19a_open_default.py` (+ D3 / F08_10b for the Save-disabled half) | covered |
| AC2 | Editing any field toggles the dirty indicator on; clearing the field back to its original value leaves the indicator on (no deep equality — `markDirty` is set-and-forget). | Acceptance criteria | `F08_19b_dirty_setforget.py` | covered |
| AC3 | Structured save with an empty-step text drops that step silently and writes the cleaned result. | Acceptance criteria | `F08_19c_structured_cleanup.py` | covered |
| AC4 | Attempting to save an outline-kind scenario after cleanup has removed every examples block shows `alert("Cannot save: An outline must have at least one Examples block.")` and aborts (no PATCH issued). | Acceptance criteria | duplicates CL4; tracked there | n/a |
| AC5 | Switching tabs with a dirty buffer prompts a `confirm` and discards (resets to snapshots) on OK. | Acceptance criteria | duplicates TS2; tracked there | n/a |
| AC6 | Raw save of a file with a parse error returns 422 and renders the message at `#raw-error`; buffer remains dirty. | Acceptance criteria | `F08_19d_raw_parse_error.py` | covered |
| AC7 | After a successful save, `Saved` badge appears for ~1.5 s then disappears; next dirty edit clears it immediately. | Acceptance criteria | `F08_19e_saved_badge.py` | covered |
| AC8 | External rename of the open file with a clean buffer triggers the "updated externally" info banner and silently reloads the editor. | Acceptance criteria | duplicates EB2; tracked there | n/a |
| AC9 | External delete of the open file triggers the red "removed" banner; the buffer remains in memory and the user can copy values out before discarding. | Acceptance criteria | duplicates EB1 + adds "buffer remains in memory" claim → folded into `F08_18_external_banner.py` | n/a |
| AC10 | Manual reload with a dirty buffer prompts to confirm before discarding. | Acceptance criteria | duplicates RL1; tracked there | n/a |
| AC11 | Move success navigates the editor to the new path; failure keeps the modal open with the server's error inline. | Acceptance criteria | duplicates MV4 + MV5; tracked there | n/a |

## Summary

- Total rules: **47** countable (1 RT + 6 TP + 2 W + 2 B + 4 D + 3 TS + 4 CL + 6 SS + 3 SR + 3 RN + 5 MV + 4 RL + 4 EB + 11 AC, with 8 AC entries flagged `n/a` as duplicates of behaviour rules).
- Distinct work units: **39** (47 − 8 dedupe).
- `covered`: **39** — every distinct work unit owns a feature-08
  smoke; rules with cross-credit (TP4, TP6, TS3, SS4, SR1, RN2, MV3)
  flipped from `partial` once the dedicated `F08_*.py` shipped.
- `partial`: **0**.
- `missing`: **0**.
- `n/a`: **8** (AC dedupe rows).
- **Smoke files written:** 24 (`F08_01..F08_19[a-e]`).

Feature-08 has the largest controller in the codebase
(`tmsEditor`, ~1400 LOC). The largest cohort of new smokes is static
JS-body inspection (12 files target the controller). End-to-end
Flask-test-client smokes cover the route (RT1, AC1), the editor-data
payload (TP6), the rendered topbar (TP1, TP3, TP5), the disabled-state
Tailwind classes (D3), and the raw-PUT 422 parse-error envelope
(SR2, AC6). The AC3 smoke runs the full save flow: it asserts the
server REJECTS uncleaned payloads (proving cleanup is required), then
mirrors `cleanupBuffer` in Python and confirms the cleaned PATCH
succeeds with the empty step gone from disk.

## Step 4 execution log

1. **24 smokes drafted** (`F08_01..F08_19e`) per the planned file map
   with the D-row split applied upfront.
2. **First full-suite run (24 smokes):** 20 pass, 4 fail.
   - `F08_05_structured_tab.py` — TP4 radio regex hardcoded
     attribute order; the actual HTML places `id="kind-scenario"`
     after `type`/`name`/`value`. Relaxed to per-attribute checks on
     the matched `<input>` block.
   - `F08_10a_dirty_static.py` — D1 spot check for the kind toggle
     assumed `getElementById("kind-scenario") -> markDirty(true)`
     within 400 chars, but the toggle wires through `_setKind(kind)`.
     Split into two assertions: the wire to `_setKind` AND a static
     check that `_setKind` body calls `markDirty(true)`.
   - `F08_16_move.py` — MV4 success-branch regex capped the distance
     between `close()` and `htmx.ajax(...)` at 200 chars, but the
     body has a multi-line comment that pushes the gap past 200.
     Replaced bounded quantifier with `[\s\S]+?` to accept the gap.
   - `F08_19c_structured_cleanup.py` — AC3 originally assumed the
     server would silently clean empty-text steps on PATCH. The
     server actually returns 422 `validation_error` and the cleanup
     is purely client-side (`cleanupBuffer`). Rewrote to a 3-step
     test: (a) confirm the server rejects uncleaned payloads,
     (b) mirror `cleanupBuffer` in Python, (c) PATCH the cleaned
     payload and verify the empty step is dropped on disk.
3. **Second full-suite run (24 smokes):** 24 pass.
4. **Full repo suite (100 smokes across features 01-08):** 100 pass.

## Drifts surfaced

- **RT1 parse-error branch — RESOLVED (spec updated):** the spec
  originally said "Parse errors propagate as a 422 envelope via the
  UI blueprint error handler" but the UI blueprint registers no
  `@ui.errorhandler(GherkinParseError)` (only ValueError → 400 and
  FileNotFoundError → 404), so the catch-all Exception handler
  returns a generic 500. Per the user's decision (Jun 9), the
  **spec was amended** (`08-feature-file-editor-NEW.md` Route §) to
  document the 500 fallback as the intended HTML-route contract and
  to clarify that the 422 `parse_error` envelope belongs to the
  JSON API surface (`PUT /api/files/<p>/raw`). `F08_01_route.py`
  asserts the observed behaviour (status ≥ 400 + no editor
  scaffold), now matching the spec.
- **AC1 PATCH with empty description:** the spec says Save is
  "disabled until the description is non-empty" (purely client-side
  via `updateSaveButton`). The server PATCH endpoint also rejects
  empty descriptions (`validation_error`). Not a contradiction, just
  belt-and-suspenders. `F08_19a_open_default.py` falls back to a
  non-empty description if the PATCH returns 422, so the rendered
  page can still be asserted on.
- **AC3 server-side validation:** see Step-4 fix-up #4 above. The
  server is stricter than the spec suggests; cleanup is mandatory at
  the client. `F08_19c_structured_cleanup.py` documents this.

## Step 2 — executed (no moves)

No existing smokes have feature-08 as their **primary** frame:

- `.smoke-scratch/feature-05/F05_02_ui_triggers.py` — primary
  frame is **feature-05** (testcase-CRUD's API consumption from
  the JS layer). UI2–UI5 assertions cross-credit feature-08 rules
  (RN2, MV3, SS4, SR1, TS3) but the docstring anchors on
  testcase-CRUD's contract. Stays in feature-05.
- `.smoke-scratch/feature-05/F05_03_ui_gaps.py` — primary frame
  is **feature-05** (testcase-CRUD's "no UI for delete/duplicate").
  Cross-credits feature-08 "no `#btn-delete` / `#btn-duplicate`
  in topbar". Stays in feature-05.
- `.smoke-scratch/feature-11/F11_08_editor_scaffold.py` — primary
  frame is **feature-11** (`feature-enums` section). Regression
  steps 4–5 cross-credit TP4 / TP6. (Moved from root `s13_b` to
  `feature-11/` in feature-11 Step 2.)
- `.smoke-scratch/feature-11/F11_09_editor_controller.py` — primary
  frame is **feature-11** (`tmsEditor` enums controller wiring).
  Regression step 6 cross-credits TP6 `feature.enums` sub-payload.
  (Moved from root `s13_c` to `feature-11/` in feature-11 Step 2.)

Cross-feature partial credit will be **noted in the matrix** (TP4,
TP6, TS3, SS4, SR1, RN2, MV3 above) but each gets a dedicated
feature-08 smoke that owns the rule end-to-end.

## Step 3 — executed (no refines)

No moves → no refines.

## Step 4 — file map (executed)

19 planned files: `F08_01..F08_19[a-e]_*.py`. Per the **feature-07
mid-Step-4 splitting heuristic** (memorialised in the smoke-suite
memory), the AC section is split into per-AC sub-files
(`F08_19a..e_*.py`) because the surviving AC rows (AC1, AC2, AC3,
AC6, AC7) each have distinct setups (render → dirty render →
PATCH round-trip → static `flashSaved` body → static
`markDirty` body inspection). The remaining sections (TP, D,
TS, CL, SS, SR, RN, MV, RL, EB) each get a single file unless
their planned LOC blows past ~150.

Tentative file map:

| File | Rules | Frame |
|---|---|---|
| `F08_01_route.py` | RT1 | end-to-end |
| `F08_02_topbar.py` | TP1 | render-and-grep |
| `F08_03_banner_slot.py` | TP2 | render + static `_showBanner` body |
| `F08_04_tabs.py` | TP3 | render-and-grep |
| `F08_05_structured_tab.py` | TP4 | render-and-grep (positive controls) |
| `F08_06_raw_tab.py` | TP5 | render-and-grep |
| `F08_07_editor_data_payload.py` | TP6 | render-and-grep + JSON.parse |
| `F08_08_wiring.py` | W1, W2 | static JS body inspection |
| `F08_09_bootstrap.py` | B1, B2 | render-and-grep + static `boot()` body |
| `F08_10a_dirty_static.py` | D1, D2, D4 | static body inspection |
| `F08_10b_save_disabled_empty_desc.py` | D3 | static + end-to-end render check |
| `F08_11_tab_switch.py` | TS1, TS2, TS3 | static `switchTab` + `save` body |
| `F08_12_cleanup.py` | CL1, CL2, CL3, CL4 | static `cleanupBuffer` body |
| `F08_13_save_flow.py` | SS2, SS3, SS4, SS5, SS6 | static `save()` body |
| `F08_14_save_raw_flow.py` | SR1, SR2, SR3 | static `saveRaw()` body + end-to-end PUT (SR2) |
| `F08_15_rename.py` | RN1, RN2, RN3 | static `rename()` body |
| `F08_16_move.py` | MV1, MV2, MV3, MV4, MV5 | static `move()` body + tree walker |
| `F08_17_reload.py` | RL1, RL2, RL3, RL4 | static `reload()` body |
| `F08_18_external_banner.py` | EB1, EB2, EB3, EB4 | static `onExternalChange()` body |
| `F08_19a_open_default.py` | AC1 | end-to-end render |
| `F08_19b_dirty_setforget.py` | AC2 | static |
| `F08_19c_structured_cleanup.py` | AC3 | end-to-end PATCH |
| `F08_19d_raw_parse_error.py` | AC6 | end-to-end PUT |
| `F08_19e_saved_badge.py` | AC7 | static |

That's **24 files** for **39 distinct work units** (including the
upfront-split `F08_10a` / `F08_10b`). Will trigger
the same per-rule split mid-Step-4 if any file's failure mode would
mask sibling rules (e.g. `F08_16_move.py` covers 5 distinct claims;
already a strong candidate for `a/b/c/d/e`).

## Notes & flags

- **No JS runtime.** Confirmed at feature-04 Step-1 sign-off and
  carried through every feature since. The controller surface is
  ~1400 LOC of JS; static regex inspection of function bodies is
  the only mechanically-checkable shape we have for `confirm()`,
  `alert()`, `setTimeout`, DOM mutation, and the
  `htmx:afterSwap` / `sse:change` event handlers.
- **Cross-credit policy.** A rule is marked `partial` (not
  `covered`) when its cross-feature smoke directly asserts a
  *subset* of the rule's claims. The feature-08 dedicated smoke
  is still required for full coverage; the cross-credit reduces
  the *amount* of new assertions required, not the number of
  files.
- **`unsupported.html` branch of RT1.** Out of scope for the
  feature-08 smoke (the spec only commits "non-`.feature` paths
  render `unsupported.html`"; the actual `unsupported.html`
  shape is a follow-up). The RT1 smoke asserts it serves *some*
  HTML (status 200) for a non-feature file under the `/ui/file/<p>`
  URL space, plus the `.feature` happy path.
- **Spec gaps surfaced during Step-1 read-through.**
  - The spec lists `tmsEditor` methods at the public-surface level
    but does NOT commit to their exact names being part of the
    contract. The smokes follow the spec's *named* methods
    (`renderStructured`, `cleanupBuffer`, etc.) — if the
    controller is later refactored to a class with different
    method names, the smokes will fail and surface the drift.
  - The "rename uses `window.prompt`" rule (RN1) is explicitly
    flagged in the spec's **Surface for follow-up** as a future
    migration target. The smoke asserts the *current* shape.
  - The 1.5 s `Saved` badge timer (AC7 / SS5) — the spec says
    "~1.5 s"; the smoke asserts `1500` ms in the `setTimeout`
    call (the literal currently in `app.js`). If the value
    changes (1000 ms / 2000 ms / etc.), the smoke flags the drift.

## Step 1 sign-off — recorded Jun 8, 2026

Approved with defaults + D-row split:

1. **Step 2: no moves.** Audited candidates (`F05_02_ui_triggers.py`,
   `F05_03_ui_gaps.py`, `feature-11/F11_08_editor_scaffold.py`,
   `feature-11/F11_09_editor_controller.py`) — none primary-frame
   feature-08; cross-credit retained in the matrix.
2. **Cross-credit policy:** rules with cross-feature `partial`
   (TP4, TP6, TS3, SS4, SR1, RN2, MV3) flip to `covered` once
   the feature-08 dedicated smoke exists and adds non-identical
   assertions (controller-specific behaviour the cross-credit
   smoke does not assert).
3. **AC dedupe:** 5 surviving AC rows (AC1/2/3/6/7); 6 AC rows
   flagged `n/a` as duplicates of behaviour rules (AC4=CL4,
   AC5=TS2, AC8=EB2, AC9=EB1, AC10=RL1, AC11=MV4+MV5).
4. **Splitting heuristic:** `F08_10` split upfront into
   `F08_10a_dirty_static.py` (D1/D2/D4 static) +
   `F08_10b_save_disabled_empty_desc.py` (D3 end-to-end render).
   Other multi-rule files stay grouped; split mid-Step-4 only if
   a regression in one rule masks sibling rules.
5. **RN1 strict.** Smoke asserts the current `window.prompt(`
   literal in the `rename()` body. A future migration to
   `tmsOpenModal` will fail-loud and surface the drift.

## Step 1 sign-off questions (archived)

Please confirm:

1. **No moves.** Per the audit above, no existing smoke
   primary-frames feature-08 (the closest candidates anchor on
   features 05 and 11). Confirm Step 2 is a no-op?
2. **Cross-credit as `partial`.** Rules TP4, TP6, TS3, SS4, SR1,
   RN2, MV3 are partially covered by smokes in features 05 and 11.
   The plan keeps them as `partial` until feature-08 has its own
   dedicated smoke (which then flips them to `covered`). The
   cross-credit notes stay in the matrix so the relationship is
   visible. Acceptable, or want a stricter "must be feature-08-
   primary-only" rule?
3. **AC dedupe count.** 8 of 11 AC rows are flagged `n/a` as
   duplicates of behaviour rules (CL4=AC4, TS2=AC5, EB2=AC8,
   EB1+memory=AC9, RL1=AC10, MV4+MV5=AC11). Surviving AC smokes
   are AC1, AC2, AC3, AC6, AC7. Confirm the dedupe boundary or
   keep AC4/5/8/9/10/11 as separate end-to-end smokes that
   complement the static behaviour check?
4. **Per-rule split heuristic timing.** Initial plan groups 4–5
   rules per file (e.g. `F08_16_move.py` covers MV1–MV5). Apply
   the splitting heuristic upfront (split `F08_16` into
   `F08_16a..e` from the start) or wait for Step 4 to discover
   which files genuinely need the split? Recommendation: **wait**
   — feature-07's splits emerged organically because failures
   surfaced distinct issues; preemptive splitting risks creating
   noise without separation benefit.
5. **`window.prompt` for rename (RN1).** Spec says this is a
   legacy v1 affordance the team intends to migrate. Smoke
   asserts the **current** `window.prompt` shape so any
   migration to `tmsOpenModal` will fail-loud. Acceptable, or
   should the smoke be lenient (assert "either `window.prompt`
   or `tmsOpenModal`")?

Once signed off, Step 2 (no-op) is recorded, Step 3 (no-op) is
recorded, and Step 4 writes the ~23 `F08_*.py` files.
