# 04 · Test-case detail (editor) revamp — tech spec

_Status: **Shipped Jun 13, 2026** (D1–D5, RG1, Option B, OQ1–OQ8 all
resolved and implemented, plus three follow-ups: text search over the
scenario name, the editor placeholder, and the folder-detail list column).
Kicked off Jun 13, 2026 from the `IN-PROGRESS.md` Must-have "Investigate:
revamp test-case detail (editor)" item. Coverage:
`.smoke-scratch/tech-04/COVERAGE.md`; one-time migration via
`scripts/backfill_scenario_names.py`; full suite 275/275._

## Scope

The single-file `.feature` editor rendered into `#main-pane`
(`app/templates/file_editor.html` + controller `app/static/08_file_editor.js`)
and the create-test-case modal (`app/static/03_folder_actions.js`). Five
asks, in order:

1. **Re-size the feature description and mark it optional.**
2. **Scenario name becomes the required field on create** (instead of the
   feature description).
3. **Hide the file-name header at the top.**
4. **Structured view: compact feature description + feature tags + Enums**
   to give Background and the scenario steps more screen room.
5. **Raw view: unchanged.**

Out of scope (separate Must-have backlog items, their own specs): the
test-case **list** revamp and the **import test cases** feature.

## Current state (grounded)

- **File-name header**: `app/templates/file_editor.html:78` —
  `<h2 id="file-name-display" …>{{ file_name }}</h2>`. No JS references
  `file-name-display` (grep clean), so the rename flow does **not** update
  it; removing/hiding it is self-contained. The breadcrumb above
  (`:44-53`) ends with a trailing `/` and **omits** the file name today.
- **Feature description**: `file_editor.html:90-95` — a `rows="3"`
  textarea (`#feature-description`). Rendered from `f.description`
  (`08_file_editor.js:153`); input handler at `:623-626`.
- **Feature tags**: `file_editor.html:97-107` (`#feature-tags-chips`).
- **Enums**: `file_editor.html:109-133` (`#feature-enums`), pickers built
  dynamically by `renderEnums` (`08_file_editor.js:994-1037`).
- **Save-gate (R3 / "D3")**: `updateSaveButton` (`08_file_editor.js:142-147`)
  disables `#btn-save` when `feature.description` is empty/whitespace.
- **Model invariant**: `validate_feature` (`app/models/_feature.py:341-345`)
  **raises** `ValidationError` when `description.strip()` is empty. The
  serializer calls it before every write (`gherkin_io.py:372`), so an empty
  description currently cannot be persisted by either Save or create.
- **Serializer**: `gherkin_io.py:390` emits `f"Feature: {…}"`. With an
  empty description this becomes the bare line `Feature:`.
- **Parser**: `parse_feature` → `_assemble_description(name, body)`
  (`gherkin_io.py:98-101, 268`); name comes from `feature_ast["name"]`.
- **Create flow**: modal `tmsCreateFile` (`03_folder_actions.js:183-260`)
  collects **File name + Description**, both required (non-empty after
  trim, `:226-229`). `POST /api/files` (`routes_files.py:20-41`) requires
  a non-empty `description` (`:25-26`) and calls
  `create_file(parts, description)` (`storage/_features.py:40-78`), which
  builds `Feature(description=…, scenario=Scenario(kind="scenario",
  name=""))` (`:68-71`). **Scenario name is always empty on create today.**
- **Raw view**: `file_editor.html` raw tab + `wireRawInputs`
  (`08_file_editor.js:729-737`). Untouched by this work.

## Impact: the "optional description" change is a model-level change

Making the feature description optional is **not** a UI-only tweak. The
non-empty rule is enforced in four layers and pinned by smokes:

| Layer | Location | Smoke that pins "description required" |
| --- | --- | --- |
| Model | `_feature.py:341-345` | `feature-01/F01_02_validate_time.py:49-54` (V1) |
| Serializer (calls model) | `gherkin_io.py:372` | (via V1) |
| Create route | `routes_files.py:25-26` | `feature-05/F05_07_create_body.py` |
| Editor Save-gate | `08_file_editor.js:144-146` | `feature-08/F08_10b_save_disabled_empty_desc.py`; AC1 `F08_19a` |

Relaxing it means **re-pinning** those smokes to the new rule (not deleting
them — they flip from "rejects empty" to "accepts empty").

Two further impacts surfaced during self-investigation:

- **D1 also adds a data migration.** Existing files carry their identifier
  in `description`; D1 moves it into `scenario.name`. That is a one-time
  backfill over every `.feature` file (precedent:
  `scripts/backfill_enums.py`), with non-trivial edge cases (OQ1–OQ3).
- **D5 redesigns the Enums UI**, which re-pins shipped **feature-11**
  contracts (`F11_08`/`F11_09`/`F11_14`/`F11_15`) — see *Affected tests*.

## Proposed approach (per resolved decisions D1–D5)

### A. Feature description → optional + 1-line; existing files migrated (D1)

- Drop the description-non-empty check in `validate_feature`
  (`_feature.py:341-345`); empty description becomes legal across model,
  serializer, create route, and editor.
- `serialize_feature` already emits a clean `Feature:` line for empty
  description; verify the round-trip (U1) in DO-0.
- Editor: `#feature-description` becomes a 1-line `textarea` (`rows=1`),
  label marked optional; Save-gate changes per D3.
- Existing files: a one-time migration sets `scenario.name` from the
  current `description` so scenario name is the primary identifier going
  forward (move rule + edge cases → §F and OQ1–OQ3).

### B. Create flow — 3-field modal, scenario name required (D2, D3)

- Modal `tmsCreateFile`: three fields, top-down order **File name***
  (required), **Feature description** (optional), **Scenario name***
  (required). Gate Confirm on File name + Scenario name non-empty after
  trim; no other client-side validation.
- `POST /api/files`: add `scenario_name`, **optional** at the API
  (default `""`, type-checked), `description` also optional (default `""`).
  _Decision (Jun 13, 2026) — **Option B**: the API stays as permissive as
  the model (`validate_feature` V5 allows an empty scenario name) and as
  the edit path (RG1 made the editor gate UI-only). "Required scenario
  name" is enforced **only by the create modal** (client-side). Hard
  API-level enforcement is filed as a separate Must-have ("Require
  scenario_name at API") so the 41 setup-only smokes that create files via
  `POST /api/files` are not churned now._
- `create_file(parts, description="", *, scenario_name="")`: build
  `Scenario(kind="scenario", name=scenario_name)`.
- Re-pin `feature-05` create-body smoke(s).

### C. Hide the file-name header entirely (D4)

- Remove `<h2 id="file-name-display">` (`file_editor.html:78`); do **not**
  add a breadcrumb crumb. File identity comes from the tree highlight (+
  the browser title — but the title is static today; see OQ5).

### D. Compact Structured metadata (D5)

- **Feature description:** 1-line `textarea` (`rows=1`) by default.
- **Feature tags:** unchanged.
- **Enums:** redesigned into a borderless, up-to-3-column grid of enum
  rows. Each row = a **kind** dropdown (enabled) + a **value** dropdown
  (disabled until a kind is chosen, then enabled). One empty row by
  default; a **"+ Add enum"** control appends rows; existing
  `feature.enums` entries render as pre-filled rows. "Manage…" deep-link
  unchanged. This replaces the current "one auto-shown `<select>` per
  defined kind" model (`renderEnums`/`_buildEnumPicker`,
  `08_file_editor.js:994-1096`) — see *Affected tests* + OQ4/OQ6/OQ7.

### E. Raw view (ask 5)

- No change. Guarded by re-running the feature-08 raw smokes.

### F. One-time migration script (D1)

- New idempotent offline script mirroring `scripts/backfill_enums.py`:
  walk every `.feature` file, set `scenario.name` from `description` per
  the move rule (OQ1–OQ3), re-serialize. Run via
  `.venv/bin/python scripts/<name>.py`; re-runnable safely.

## Decisions (resolved Jun 13, 2026)

- **D1 — Optional description + migrate to scenario name.** Existing files:
  move the current feature `description` into `scenario.name`; scenario
  name becomes the primary identifier. New files: only File name +
  Scenario name required; feature description optional, editable later.
  Move-rule edge cases → OQ1–OQ3.
- **D2 — Create-modal fields.** File name (required) + Scenario name
  (required) + Description (optional).
- **D3 — Create-modal validation + order.** One modal; require File name +
  Scenario name, Description optional; no other validation. Field order
  top-down: File name*, Feature description, Scenario name*.
- **D4 — File name in detail view.** Hidden entirely; rely on the tree
  highlight + browser title.
- **D5 — Structured layout.** Feature description = 1-line textarea
  default; feature tags as-is; Enums = up-to-3-column borderless grid;
  default one row (kind enabled, value disabled → value enables after kind
  picked); "+ Add enum" to add rows; keep "Manage…".

## Affected tests (re-pin to the new contract, do not delete)

- **feature-01** `F01_02` (V1): empty description now **accepted** (model
  rule removed).
- **feature-05** `F05_07_create_body`: create now requires `scenario_name`;
  description optional.
- **feature-08** `F08_10b` (D3 save-gate), `F08_19a` (AC1): Save-gate no
  longer keyed on description.
- **feature-11** `F11_08` (scaffold sub-elements), `F11_09` (controller:
  `renderEnums`/`_buildEnumPicker`/picker change), `F11_14` (ED11
  empty-disabled), `F11_15` (ED12 not-set option): the Enums-picker
  structure changes under D5 — re-pin to the two-dropdown/add-row UI while
  preserving the data contract (`feature.enums` dict, key/label split,
  orphan save-block).
- Folder-list / search smokes that assert the description column stay
  unchanged for THIS item (display-swap there belongs to the separate
  list-revamp item — see OQ8).

## Assumptions + open questions

Verified-low-risk (carry into DO):

- **U1 (medium).** `parse_feature` round-trips a bare `Feature:` line.
  Retired by DO-0 round-trip smoke before any model edit.
- **U2 (low).** No JS depends on `#file-name-display` (grep clean) — safe
  to remove.
- **U3 (low).** feature-08 scaffold smokes assert `#editor-data`/`#btn-save`,
  not the `<h2>` — header removal won't break them.

Resolved (Jun 13, 2026):

- **OQ1 — Multi-line on migrate:** join lines with a `" / "` separator.
- **OQ2 — Existing scenario name:** skip — only set `scenario.name` when it
  is currently empty (never clobber).
- **OQ3 — Description after move:** keep a copy (description remains as an
  optional/supplementary field).
- **OQ4 — Enums grid:** a 3-column visual grid with unlimited rows.
- **OQ5 — Browser title:** leave static; do **not** set `document.title`.
- **OQ6 — Kind reuse:** exclude an already-chosen kind from other rows'
  kind dropdowns.
- **OQ7 — Orphan / missing / empty states:** keep all three, restyled into
  the grid; preserve the save-block.
- **OQ8 — Display swap:** the **search-results list** now displays the
  scenario name instead of the feature description (in THIS item). The
  folder-list column swap stays with the separate list-revamp item.

Derived migration rule (OQ1+OQ2+OQ3): for each `.feature`, if
`scenario.name` is empty, set it to `description` with newlines replaced by
`" / "`; leave `description` unchanged. Idempotent (skips files that
already have a name).

## Implementation detail (grounded Jun 13, 2026)

### A. Description + header (ask 1, D4)

- `validate_feature` (`_feature.py:341-345`): remove the
  description-non-empty block. `Scenario.name` empty is already legal
  (V5; `F01_02:91-92`), so no other model change.
- `file_editor.html:92`: `#feature-description` `rows="3"` → `rows="1"`;
  mark the label optional. The editor **already** has a `#scenario-name`
  input (`file_editor.html:162`, placeholder "(optional)") — no new editor
  field needed.
- `file_editor.html:78`: remove `<h2 id="file-name-display">`. This
  template has no breadcrumb (just the h2 + tab bar), so nothing else to
  touch (D4 = hidden entirely).

### B. Create modal (D2, D3) — `tmsCreateFile` (`03_folder_actions.js:183-260`)

- Body: three fields, order **File name** (req) → **Feature description**
  (optional) → **Scenario name** (req); reuse the existing markup idiom.
- Gate: `setConfirmDisabled(!(fileName && scenarioName))` — description no
  longer gates (`:226-231`).
- POST body (`:210-214`): add `scenario_name`; `description` may be `""`.
- Keyboard chain (`:242-256`): name Enter → focus description → focus
  scenario name; Ctrl/Cmd+Enter submits from any field.

### C. Backend create (D2)

- `routes_files.py:24-26`: today rejects an empty `description`; swap that
  requirement onto a new non-empty `scenario_name`, make `description`
  optional (`""`), and pass `scenario_name` into the `create_file` call
  (currently `:40`, positional `description` only).
- `create_file(parts, description="", *, scenario_name="")`:
  `Scenario(kind="scenario", name=scenario_name)`.

### D. Enums redesign (D5) — keep the ids, replace the builders

- **Preserve** `#feature-enums` + `#feature-enums-missing/empty/pickers/
  orphans` + `#feature-enums-manage` + `#feature-enums-init-btn`
  (`file_editor.html:115-133`) so **F11_08 stays green by design**.
- Replace the `renderEnums` "one picker per kind" loop
  (`08_file_editor.js:1032-1034`) and `_buildEnumPicker` (`:1039-1096`)
  with a **row-grid builder** mounted in `#feature-enums-pickers`:
  - 3-column grid, unlimited rows (OQ4).
  - Each row = a **kind** `<select>` (enabled; options = vocab kinds minus
    kinds chosen in other rows, OQ6) + a **value** `<select>` (disabled
    until a kind is chosen).
  - Value `<select>` once enabled: leads with `— not set —` (value `""`),
    then `<option value=key>label</option>` per `vocab[kind]`, stored key
    pre-selected (**ED12 preserved**). Empty kind (`vocab[kind] == {}`) →
    value `<select>` disabled + "No <kind> entries…" hint (**ED11
    preserved**).
  - Pre-fill one row per existing `feature.enums` entry + one blank
    trailing row; **"+ Add enum"** appends a blank row; per-row `×` clears
    that kind.
  - Change handler writes `state.feature.enums[kind]=value` +
    `markDirty(true)` + `_renderEnumOrphans()` (**F11_09 picker-change
    contract preserved**, just relocated to the row model).
- `_renderEnumOrphans` (`:1106-1145`), missing/empty states, Manage…,
  Initialize, and the save-block (`Storage._cross_check_enums`) — all
  unchanged. Data contract `state.feature.enums = {kind: key}` unchanged.

### E. Editor Save-gate — RESOLVED (RG1 = gate on scenario name)

`updateSaveButton` currently disables Save when `state.feature.description`
is empty-after-trim (`F08_10b:44-53`, `F08_19a`). **Decision (RG1 = option
b): move the gate to scenario name** — Save is enabled only when
`state.feature.scenario.name` is non-empty after trim. Concretely:
`updateSaveButton` reads `this.state?.feature?.scenario?.name || ""`,
`.trim()`, `btn.disabled = !name`. Scenario name is the new required
identity field, so this keeps Save tied to a meaningful invariant.

**Consistency tradeoff (new, non-blocking).** The old gate was backed by a
server invariant (V1: description required). The new scenario-name gate is
**UI-only** — `validate_feature` V5 still permits an empty `scenario.name`
(`F01_02:88-93`), and this plan does **not** change that. In practice empty
names don't arise (post-migration every file has one; the create modal
requires one). If defence-in-depth is wanted, a follow-up could add a
write-time "scenario name required" invariant — but that re-pins V5 and is
out of scope for this item. Flagging so the asymmetry is a conscious
choice, not an oversight.

## Smoke re-pin map (grounded)

- **`F01_02`** (V1, `:49-54`): invert — empty / whitespace `description`
  now validates cleanly; keep V5 (empty scenario name allowed).
- **`F05_07`** (CB1): invert — `description` optional (missing / empty no
  longer 400 on its own); `scenario_name` now **required** (missing /
  empty → 400); created-shape assertion changes from `scenario.name == ""`
  (`:89-91`) to `== <provided name>`.
- **`F08_10b` + `F08_19a`**: re-pin `updateSaveButton` to the **scenario-
  name** gate (reads `feature.scenario.name`, trims, `btn.disabled =
  !name`); the description no longer gates Save.
- **`F11_08`**: unchanged — the redesign keeps the four container ids + the
  init button.
- **`F11_14`** (ED11): re-pin to the new value-`<select>` empty-kind
  disabled + hint.
- **`F11_15`** (ED12): re-pin to the new value-`<select>` `— not set —` +
  key/label split + pre-select.
- **`F11_09`**: re-pin only the `_buildEnumPicker` change-handler slice to
  the row model; the vocab-cache / `_loadEnums` / `renderEnums`-in-
  `renderStructured` / orphan / init assertions stay valid.

## Confidence

**High**. OQ1–OQ8 **and RG1** are resolved, and every code claim in the
Implementation-detail / Smoke-re-pin sections is source-verified, so the
plan is fully executable. The two remaining cost/risk centres are the Enums
UI redesign (D5 + OQ4/OQ6/OQ7, which re-pins shipped feature-11 contracts)
and the **net-new** migration script — both well-specified but the larger
build items. Backend optionality, the create flow, header removal, the
scenario-name Save-gate, and the search-results display swap (OQ8) are
low-risk. One optional, non-blocking follow-up surfaced: whether to also
enforce "scenario name required" server-side (V-rule) to match the UI gate.
The test-run / test-report column requests are **out of scope for this
item** — see `tech-05` / `tech-06`.

## As-built (shipped Jun 13, 2026)

- **DO-1 backend:** dropped the description-non-empty rule in
  `validate_feature`; `create_file(parts, description="", *,
  scenario_name="")` + `POST /api/files` accept an optional, type-checked
  `scenario_name` (**Option B** — required only client-side).
- **DO-2 migration:** `scripts/backfill_scenario_names.py` (idempotent);
  run once over `./project` (36 migrated, 3 skipped).
- **DO-3 create modal:** 3-field `tmsCreateFile` (File name, Feature
  description optional, Scenario name); gate on name + scenario.
- **DO-4 editor:** 1-line optional description; file-name `<h2>` removed;
  Save-gate on scenario name (RG1); `#scenario-name` placeholder reads
  "Scenario name".
- **DO-5 enums:** `_renderEnumRows` / `_buildEnumRow` / `_commitEnumRows`
  3-column (kind, value) grid with `+ Add enum` / per-row remove; OQ6 kind
  exclusion; ED11/ED12 + orphan handling preserved; scaffold ids intact.
- **DO-6 search (OQ8):** `SearchHit.scenario_name`; results list shows the
  scenario name; text search matches description **or** scenario name.
- **Folder-detail list:** the test-case list's middle column shows the
  scenario name (`Storage.list_folder` carries `scenario_name`).
- **CHECK:** new `tech-04/T04_01..03`; re-pinned
  feature-01/02/05/07/08/09/11; full suite **275/275**.
- **Deferred:** hard `scenario_name` enforcement at the API → separate
  Must-have. See `.smoke-scratch/tech-04/COVERAGE.md`.
