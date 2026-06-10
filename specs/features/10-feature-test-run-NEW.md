# 10 · Test run

_Retroactive spec: documents the as-shipped behaviour. Source files:_
_`app/models/_run.py` (`TestRun`, `RunResult`, `RUN_RESULTS`,_
_`validate_run`), `app/storage/_runs.py` (`create_run`, `read_run`,_
_`write_run`, `delete_run`, `list_run_groups`, `list_runs`,_
_`create_run_group`, `delete_run_group`, `add_run_case`,_
_`remove_run_case`, `update_run_result`, `list_test_run_tree`,_
_`list_projects`, `RESERVED_DEPTH2_NAMES`), `app/errors.py`_
_(`RunParseError`), `app/server/routes_runs.py` (`/api/runs/*`,_
_`/api/run-groups`, `/ui/run/...`, `ui_folder` dispatcher_
_branch, `/ui/test-run-tree`), `app/templates/`_
_(`folder_test_run_area.html`, `folder_test_run_group.html`,_
_`run_editor.html`, `test_run_sidebar.html`), `app/static/06_run_editor.js`_
_+ `04_run_create.js` (`tmsRunEditor`, `tmsCreateRun`, `tmsBuildCasePicker`,_
_`tmsFetchProjectFeaturePaths`, `tmsSlugifyForFilename`)._

## Summary

A **test run** is a stored snapshot of "I executed these test cases
and these were the results". Each run lives as a single YAML file
under its owning project's typed `test-run/` area, organised into
one grouping folder. Runs reference test cases by data-root-relative
file path; per-case results (`PENDING`, `EXECUTING`, `PASSED`,
`FAILED`, `SKIPPED`) and free-form remarks live on the run, never on
the test case. The UI exposes the area through a dedicated **Test
run** sidebar tab and a main-pane run editor whose UX vocabulary
(dirty indicator, Save / Reload, Saved badge, external-change
banner) mirrors `08-file-editor`.

## Scope

In scope:

- On-disk run schema (`<project>/test-run/<group>/<run>.yaml`).
- `TestRun` / `RunResult` dataclasses + `RUN_RESULTS` enum +
  `validate_run` invariants.
- Storage methods covering run CRUD, group CRUD, per-case
  mutation, and the typed-tree aggregator.
- HTTP routes for run lifecycle, per-case mutation, group
  lifecycle, plus the UI partials for the typed area and the
  run editor.
- The depth-2 reservation rule (`test-run` is reserved when it is
  the second segment of a logical path).
- Server-computed `missing: bool` per row (tombstone flag) and
  its template rendering.
- The `tmsRunEditor` JS controller: bootstrap, dirty tracking,
  whole-doc Save, manual Reload, transient Saved badge, Add /
  Remove case, external-change banner, deferred-banner-across-
  htmx-swap.
- The `tmsCreateRun` modal (Test-run sidebar button → group
  selector + run name, with a reveal-on-select sub-form for
  new groups and a zero-projects info branch) and the reusable
  `tmsBuildCasePicker` (kept for the run editor's `+ Add test
  case` flow even though creation no longer surfaces a picker).
- The sidebar restructure delta (Test run vertical tab — owned
  by the sibling sidebar-restructure spec; this feature consumes
  it and adds clickable run leaves).

Out of scope (v1):

- Aggregate / cross-run reporting.
- Per-test-case result history across runs.
- Bulk row mutation (mark N rows PASSED in one click); the
  per-row select + per-row PATCH endpoint cover the underlying
  need.
- Run templating (`POST /api/runs?source=<existing>`).
- YAML schema validation beyond dataclass round-trip
  (`validate_run` enforces structural rules; arbitrary YAML
  edits are not anticipated since only the API writes).
- Concurrent multi-tab run editing — last-write-wins carries
  over from the file editor.
- Search across runs (`09-search` is `.feature`-only).

## Data model

```
TestRun
├─ name:        str          # human label; not the file name
├─ created_at:  iso-8601 str # set at create; never edited
├─ description: str          # optional run-level notes
└─ results: list[RunResult]

RunResult
├─ file_path: str            # data-root-relative .feature path
├─ result:    Literal[*RUN_RESULTS]
└─ remark:    str            # freeform, may be ""
```

Constants (`app/models/_run.py`):

- `RUN_RESULTS = ("PENDING", "EXECUTING", "PASSED", "FAILED",
  "SKIPPED")`. The default for a freshly-created or freshly-added
  row is `"PENDING"`.

Invariants (enforced by `validate_run`, called from
`_serialize_run`):

- `results` is a list (insertion order is the canonical
  on-disk order; never reshuffled by storage).
- Each `result` ∈ `RUN_RESULTS`.
- `file_path` is non-empty and not validated against disk at
  write time — tombstone rendering is a UI concern, not a
  storage concern.
- Duplicate `file_path` entries in `results` are rejected at
  write (the same case cannot appear twice in one run).
- `created_at` is stamped server-side in UTC ISO-8601 form
  (`timespec="seconds"`) on create; clients cannot override it.
  Save round-trips the value verbatim.

## On-disk schema

```yaml
name: "Sprint 42 regression"
created_at: "2026-06-05T14:30:00+00:00"
description: |
  Pre-release smoke test for the release candidate.
  Owner: QA team.
results:
  - file_path: "WebStore/Checkout/credit-card.feature"
    result: PASSED
    remark: ""
  - file_path: "WebStore/Checkout/paypal.feature"
    result: FAILED
    remark: |
      Step "user clicks Pay" timed out after 30s.
      Likely sandbox flake; retry in next run.
```

Rules:

- Top-level keys (`name`, `created_at`, `description`,
  `results`) are stable. New keys may be added with forward-
  compatible defaults but never reordered as a breaking change.
- `remark` uses `|` block scalar by default (preserves
  newlines).
- Re-serialise on every write so on-disk bytes are canonical;
  back-to-back saves with the same payload produce byte-
  identical files (idempotence, same policy as `.feature`
  files in `01-gherkin-io`).
- Malformed YAML is surfaced as `RunParseError(line, column,
  message)` (HTTP 422 envelope) on `read_run`.

## Storage layout

```
<data-root>/
├─ WebStore/                            # project (depth 1)
│  ├─ test-run/                         # reserved name (depth 2)
│  │  ├─ release-rc/                    # group (depth 3)
│  │  │  ├─ sprint-42-regression.yaml   # run (depth 4)
│  │  │  └─ rc1-smoke.yaml
│  │  └─ nightly/
│  │     └─ 2026-06-04-nightly.yaml
│  ├─ Checkout/                         # regular module (depth 2)
│  │  └─ credit-card.feature
│  └─ Search/
│     └─ empty-query.feature
```

Constraints (enforced by storage):

- **Reserved name at depth 2 only.** `RESERVED_DEPTH2_NAMES =
  frozenset({"test-run"})`. `create_folder` rejects attempts to
  create a depth-2 folder with this name via the generic folder
  API (raises `NameConflictError`, HTTP 409). Reservation does
  NOT apply at other depths — a sub-folder named `test-run`
  deeper inside a module is legal and carries no semantic
  meaning.
- **No nesting beyond `<group>`.** `create_folder` rejects any
  folder whose parent path is `<project>/test-run/<group>/...`
  (the typed area is exactly two levels deep — group + run
  file).
- **No `.feature` files** anywhere under `<project>/test-run/`.
  `create_file` rejects.
- **No `.yaml` files** outside `<project>/test-run/<group>/`.
  The run-write path is the only writer for `.yaml`; the
  `.feature` writers cannot collide.
- `<project>/test-run/` is **lazy** — never auto-created on
  project create; appears on first `create_run_group` (or
  first `create_run`, which calls `create_run_group`
  implicitly when needed).

## Public surface

### Storage (`app/storage/_runs.py`)

- `create_run_group(project: str, group: str) -> None` —
  validates segments, creates `<project>/test-run/<group>/`,
  lazily creating `<project>/test-run/` along the way.
- `delete_run_group(project: str, group: str) -> None` —
  idempotent; refuses if non-empty (forces explicit run
  deletion first).
- `list_run_groups(project: str) -> list[str]` — group names
  under `<project>/test-run/`, or `[]` if absent.
- `list_runs(project: str, group: str) -> list[dict]` — one
  entry per `.yaml` in the group, with
  `{file_name, name, created_at, case_count,
  results_count_by_status}`. Unreadable runs surface as
  zero-count entries (no exception). Used by the group view.
- `create_run(project, group, name, file_name, case_paths,
  description="") -> None` — stamps `created_at`, writes the
  YAML; `case_paths` becomes `results` with default
  `"PENDING"` and empty `remark`. Auto-creates the group folder
  if missing.
- `read_run(project, group, file_name) -> TestRun` — raises
  `FileNotFoundError` (404) if missing, `RunParseError` (422)
  on malformed YAML.
- `write_run(project, group, file_name, run: TestRun) -> None`
  — atomic write; `validate_run` runs first.
- `delete_run(project, group, file_name) -> None` — idempotent.
- `add_run_case(project, group, file_name, case_path) -> None`
  — appends one `RunResult` with `PENDING` + empty remark;
  raises `NameConflictError` on duplicate.
- `remove_run_case(project, group, file_name, case_path) ->
  None` — idempotent.
- `update_run_result(project, group, file_name, case_path, *,
  result=None, remark=None) -> None` — partial update.
- `list_test_run_tree() -> dict` — aggregates every project's
  typed area for the sidebar tab; root → projects with runs →
  groups → run leaves. Projects without `test-run/` are
  omitted.
- `list_projects() -> list[str]` — every depth-0 directory name,
  case-insensitive sort. Backs `GET /api/run-groups` so the
  create modal's `+ Create new group...` sub-form can target
  bare projects (those without a `test-run/` folder yet).

All run mutations use the existing storage primitives:
`_validate_segment`, per-path locks, `_atomic_write_bytes`,
`_mark_write`.

Error type (`app/errors.py`):

- `RunParseError(line: int, column: int, message: str)` —
  mirrors `GherkinParseError`. Surfaces YAML parse failures as
  HTTP 422 via the blueprint error handler.

### HTTP API (`app/server/routes_runs.py`)

| Method | Path | Effect |
|---|---|---|
| `POST` | `/api/runs` | create run (body: `{project, group, name, file_name, case_paths, description?}`) |
| `GET` | `/api/runs/<project>/<group>` | list runs (summaries) |
| `GET` | `/api/runs/<project>/<group>/<file_name>` | full run (`TestRun.to_dict()`) |
| `PATCH` | `/api/runs/<project>/<group>/<file_name>` | replace whole run (used by editor Save) |
| `DELETE` | `/api/runs/<project>/<group>/<file_name>` | delete run (idempotent 204) |
| `POST` | `/api/runs/<project>/<group>/<file_name>/cases` | append case |
| `DELETE` | `/api/runs/<project>/<group>/<file_name>/cases/<path>` | remove case |
| `PATCH` | `/api/runs/<project>/<group>/<file_name>/cases/<path>` | partial result update |
| `POST` | `/api/runs/<project>/groups` | create group (auto-creates `<project>/test-run/` if absent) |
| `DELETE` | `/api/runs/<project>/groups/<group>` | delete empty group |
| `GET` | `/api/run-groups` | aggregate listing for the create modal — `{projects: [...], groups: [{project, group}, ...]}` |

All errors use the standard `{error: {code, message, details}}`
envelope.

### UI routes (`app/server/routes_runs.py` + `routes_ui.py` dispatch)

| Path | Renders |
|---|---|
| `GET /ui/folder/<project>/test-run` | `folder_test_run_area.html` (groups landing) |
| `GET /ui/folder/<project>/test-run/<group>` | `folder_test_run_group.html` (read-only runs list — creation lives in the sidebar tab) |
| `GET /ui/run/<project>/<group>/<file_name>` | `run_editor.html` (editor) |
| `GET /ui/test-run-tree` | `test_run_sidebar.html` (Test run sidebar tab) |

The `ui_folder` dispatcher recognises `segments[1] == "test-run"`
and routes to the typed-area templates instead of
`folder_module.html` / `folder_subfolder.html`. The typed area
is exactly two levels: requests for `<project>/test-run/<group>/
<file>.yaml` under `ui_folder` 404 — runs are reached via
`/ui/run/...`, not `/ui/folder/...`.

### Templates

- **`folder_test_run_area.html`** — breadcrumb (`Projects /
  <project> /` then heading `test-run`); table of groups;
  empty state explaining groups auto-materialise on run
  create. No `+ New group` button — group creation is
  implicit in run creation.
- **`folder_test_run_group.html`** — read-only view.
  Breadcrumb (`Projects / <project> / test-run / <group>`);
  runs table sorted newest-first by `created_at`, with
  columns `name`, `created_at`, `case_count`, status-
  breakdown badges (`✓`/`✗`/`?`/`⋯`/`⤳`; zero-count statuses
  omitted). No creation affordance: the empty state shows
  "No runs yet in `<group>`. Use the **Test run** sidebar
  tab to create one." rather than a `+ Create the first
  run` CTA.
- **`run_editor.html`** — the editor shell described under
  *Invariants & rules / Run editor* below.
- **`test_run_sidebar.html`** — Test run sidebar partial.
  Header hosts the **`+ New run`** button — the single
  entry point for run creation, always visible / always
  enabled, calls `tmsCreateRun()` with no arguments
  (modal collects project / group itself). Folder rows
  (projects, groups) are decorative — only run leaves
  navigate, linking to `/ui/run/<project>/<group>/<file_name>`.
  Empty state copy points at the same button: "No test runs
  yet. Click **+ New run** above to create one."

### JS controller (`app/static/06_run_editor.js`; create flow in `04_run_create.js`)

- `tmsRunEditor` — singleton mirroring `tmsEditor`:
  `boot()`, `_readCurrent()`, `_wireInputs()`,
  `_wireHeaderButtons()`, `_refreshDirty()`, `_setDirty(d)`,
  `flashSaved()`, `_hideSavedBadge()`, `save()`, `reload()`,
  `_createResultRow(file_path)`, `_afterRowsChanged()`,
  `_onAddCaseClicked()`, `onExternalChange()`,
  `_reloadAndAnnounce(kind, message)`, `_navigateToGroup()`,
  `_showBanner({...})`, `_hideBanner()`.
- `tmsBootRunEditor()` — entry point called by the editor
  template's tail `<script>`.
- `tmsCreateRun()` — no-arg modal opener wired to the
  sidebar's `+ New run` button. See *Invariants & rules /
  Create flow* below for the full state machine.
- `tmsBuildCasePicker(features, opts)` — reusable flat
  checkbox table; `opts.exclude` filters out paths already in
  a run; `opts.onChange` fires after every selection change
  (including bulk toggles from the header). Header row includes
  a tri-state select-all checkbox that respects the live filter.
  Returns `{ node, getSelected(), countVisible() }`. **No
  longer used during run creation** (the create modal asks
  only for group + name); kept because the run editor's
  `+ Add test case` modal still uses it.
- `tmsFetchProjectFeaturePaths(project)` — fetches
  `/api/tree` and returns the project's `.feature` files
  sorted by folder path then file name. Used by the run
  editor's `+ Add test case` flow.
- `tmsSlugifyForFilename(name)` — derives the run's
  `file_name` stem from the human label (`.yaml` is appended
  server-side by `_normalize_run_filename`). Surfaced live
  as a hint under the run-name input ("will save as
  `<slug>.yaml`") so silent slug collisions become visible
  before submit.
- `tmsOpenModal({title, body, size, confirmLabel,
  confirmDisabled, onConfirm})` — `size: "md" | "lg" | "xl"`
  (default `"md"`); `confirmLabel` accepts `null` to suppress
  the Confirm button entirely (used by the zero-projects
  branch of `tmsCreateRun`). The run editor's `+ Add test
  case` picker still requests `"lg"`.

### Wiring (`app/static/09_bootstrap.js`)

- `htmx:afterSwap` on `#main-pane` clears
  `tmsRunEditor.state` when the editor leaves the main pane
  (parallels the existing `tmsEditor.state` cleanup).
- `document.body.addEventListener("sse:change", ...)` fans
  out to **both** `tmsEditor.onExternalChange()` and
  `tmsRunEditor.onExternalChange()` whenever the page
  receives a `"change"` SSE event AND the corresponding
  controller's `state` is non-null.
- `beforeunload` warns when either editor's `state.dirty`
  is true.

## Invariants & rules

### Storage

- `validate_run(run)` runs before every write. Errors raise
  `ValidationError` (HTTP 422) with a path-style locator
  (`results[3].result: ...`).
- `_normalize_run_filename(name)` auto-appends `.yaml` if no
  extension; rejects any other extension.
- Empty `results` lists are legal — runs can be drained to
  zero cases (the editor's empty-state row appears).

### Folder discipline

- The depth-2 reservation is enforced inside `create_folder`
  via `RESERVED_DEPTH2_NAMES`; the same check rejects the
  `test-run` name even if the parent is invalid.
- Path-discipline checks (under `test-run/`) live in
  `create_file` and the run-write path; both reach a 409
  `NameConflictError` for the user-facing message.

### Sidebar visibility

- `Storage.list_tree()` filters `test-run` out of every
  project's children — the Directory tree tab never shows the
  typed area as a folder.
- `Storage.list_folder` filters `test-run` from the project
  view when `len(parts) == 1` — the project's module table
  does not surface it.
- The **only** UI entry points to the typed area are the
  Test run sidebar tab and the run-editor breadcrumb (whose
  `test-run` segment is clickable to land on
  `folder_test_run_area.html`).

### Run editor

**Bootstrap.** The template's tail `<script>` calls
`tmsBootRunEditor()`. `boot()` reads `#run-editor.dataset`
(`project`, `group`, `fileName`, `createdAt`), captures
`baselineJson = JSON.stringify(_readCurrent())`, wires input
listeners + header buttons, then consumes the
`tmsRunEditor._pendingBanner` singleton sentinel if one was
queued by a prior instance.

**Dirty tracking.** `_readCurrent()` snapshots `{name,
description, results: [{file_path, result, remark}]}` from
the live DOM. `_refreshDirty()` stringifies-and-compares the
snapshot against `baselineJson`; toggles
`#run-dirty-indicator` and the Save button's `disabled`
attribute. Set-and-forget; no deep-equality fallback.

**Event delegation.** Input / change / click listeners are
attached to the results `<tbody>`, not per-row, so rows added
by `+ Add test case` are dirty-tracked and removable without
re-wiring.

**Save (whole-doc PATCH).** `save()` PATCHes
`/api/runs/<project>/<group>/<file_name>` with
`{name, created_at, description, results}` — the editor
mirrors the file editor's whole-doc save model. On success:
update `baselineJson` to the just-saved snapshot, clear
dirty, `flashSaved()` for 1.5 s. On failure: `alert(...)`,
buffer stays dirty.

**Reload.** Confirms if dirty
(`"Reload from disk? Your unsaved changes will be
discarded."`). On OK, `htmx.ajax("GET", /ui/run/...)` swaps
the main pane → the tail script re-mounts and captures a
fresh baseline.

**Saved badge.** `flashSaved()` shows `#run-saved-indicator`
for 1.5 s. Any subsequent dirty edit clears the badge
immediately so the two states never overlap.

**`+ Add test case` modal.** `_onAddCaseClicked()` fetches
`/api/tree` via `tmsFetchProjectFeaturePaths(project)`,
builds an exclude set from the editor's current
`data-file-path` values, opens an `lg` modal containing
`tmsBuildCasePicker(features, { exclude, onChange })`.
Confirm is gated on `picker.getSelected().length > 0`. On
Confirm: for each selected path, append a row cloned from
the server-rendered `<template id="run-result-row-template">`
prototype (which carries all `RUN_RESULTS` options so the
JS never duplicates that list), then `htmx.process(tbody)`
so the cloned `hx-get` link is wired, then
`_afterRowsChanged()` (toggle table / empty-state
visibility, refresh dirty).

**Per-row remove.** Class-delegated click on
`.run-row-remove`: removes the `<tr>`,
`_afterRowsChanged()`. Idempotent in the sense that the row
disappears regardless of dirty state.

**Folder grouping + filename-only rows (test-case column).**
_Superseded the original two-span path-masking by tech-02 E2
(`specs/tech/02-tech-ui-styling-enhancement-NEW.md`)._ Rows
are grouped by folder: the server emits one plain
`run-group-head` heading row per folder (first-seen folder
order, within-folder order preserved; folder shown as a
badge), and each result row renders **filename-only** inside
the link (`<span data-role="filename">`, `truncate min-w-0`),
since the heading now carries the folder. The defensive
`rsplit('/', 1)` / JS `lastIndexOf("/")` branch handles
zero-slash file_paths (hand-edited YAML) by grouping them
under an empty-folder heading and putting the whole string
in the filename. Three preservation surfaces keep the full
path for non-display use: `<tr data-file-path>` (serialize /
dirty-snapshot), `<td title>` (tooltip), and
`<a hx-get="/ui/file/…">` (click-through). The clone path
(`_createResultRow` + `_insertResultRow`) mirrors the
server-rendered shape — filename-only rows landing in their
folder group, creating a heading when the folder is new.

**Tombstone rendering.** Computed server-side in `ui_run`:
each result dict gains `missing: bool` via
`(storage.root / file_path).is_file()`. Recomputed every
render; the storage layer never auto-mutates a run when its
underlying cases vanish.

When `r.missing`:

- `<tr>` gains `run-row-missing` + `data-missing="1"`.
- The **filename span** swaps to `line-through
  text-slate-400` so the case identity reads as removed (the
  folder context lives in the group heading, per tech-02 E2).
- The remark cell shows a fixed override `<span
  class="run-remark-override">test case was removed</span>`;
  the `<textarea class="run-remark">` is hidden but **stays
  in the DOM with the stored remark value**, so the editor's
  Save round-trips the original note verbatim. Restoring
  the file un-tombstones the row on the next render and the
  preserved remark reappears.
- The result `<select>` stays editable — the user may still
  flip the row to `SKIPPED` (or any other status) before
  cleaning up the run.

**External-change banner (`onExternalChange`).** Triggered by
the body-level `sse:change` listener when
`tmsRunEditor.state != null`. Branches:

1. **Run removed on disk** (GET `/api/runs/...` → 404) →
   red error banner "This run was removed on disk." with a
   `Discard` button. Discard navigates the main pane to
   `/ui/folder/<project>/test-run/<group>` (the group view),
   not the global root.
2. **Run changed AND buffer NOT dirty** → silent reload via
   `_reloadAndAnnounce("info", "Run was updated externally;
   the editor reloaded.")`. Queues the message into
   `tmsRunEditor._pendingBanner`, then `htmx.ajax("GET",
   /ui/run/...)` re-renders the partial — the freshly-mounted
   instance picks up the banner via `boot()`'s pending-
   banner consumption.
3. **Run changed AND buffer dirty** → amber warn banner
   "Run changed externally while you have unsaved changes."
   with `Reload (discard mine)` and `Keep editing`.
   `Reload (discard mine)` clears dirty and queues the info
   banner "Run reloaded from disk; your edits were
   discarded." across the swap.

Disk-state comparison normalises the API response into the
same projection `baselineJson` uses (no `created_at`, no
`missing`), so the equality check is apples-to-apples.

The reload path goes through `/ui/run/...` (the UI partial)
rather than the JSON API, so the server re-runs the per-row
`is_file()` storm — tombstone state is always live with
respect to the filesystem.

**`beforeunload`.** Browser-native confirm fires when
`tmsRunEditor.state.dirty` (or the file editor's state is
dirty); the handler covers both editors in a single check.

### Create flow (`tmsCreateRun`)

`tmsCreateRun()` is wired to the Test-run sidebar header's
`+ New run` button and takes no arguments. The modal lives
outside any project context — it asks the user where the run
should go, then opens the run editor on the result so the
user can add description / cases / set results afterwards.

**Bootstrap (single round-trip).** Fetches `GET
/api/run-groups`, which returns
`{projects: [...], groups: [{project, group}, ...]}`. On
fetch failure, surfaces a plain `alert(...)` and returns
without opening a modal.

**Branch — zero projects.** If `projects.length === 0`,
opens an information-only modal with the copy "No projects
yet — create one first." and a Cancel-only footer. The
Confirm button is suppressed via
`tmsOpenModal({confirmLabel: null})`. This keeps the
sidebar button's "always enabled" promise honest while
preventing nonsense submits when there is nothing to
target.

**Branch — base shape.** Otherwise, opens an `md`
`tmsOpenModal` titled "Create test run" with two fields:

1. **Where** — a single native `<select>`. Existing groups
   are emitted as `<optgroup label="<project>">
   <option value="<project>|<group>"><group></option>
   </optgroup>`; the dropdown ends with a non-grouped
   `<option value="__new__">+ Create new group...</option>`.
   Selecting that sentinel reveals an inline sub-form below
   the `<select>` containing:
   - **Project** — `<select>` listing every existing
     project (sourced from the endpoint's `projects` field,
     including bare projects without a `test-run/` folder).
     Project creation is **out of scope** for this modal.
   - **Group name** — free-text `<input>`. Permissive
     character rules — storage's existing folder-name
     guards are the only gate. Trimmed; non-empty enforced
     client-side.
2. **Run name** — free-text `<input>`. The slug derived by
   `tmsSlugifyForFilename` is rendered live under the input
   ("will save as `<slug>.yaml`") so silent slug collisions
   become visible before submit. Empty slug surfaces the
   placeholder hint "(enter a name to see the file name)"
   and gates Confirm off.

**Confirm gate.** `(slug non-empty) AND (path resolved)`,
where "path resolved" means either an existing
`proj|group` pair is selected or both project + group-name
inputs are non-empty in the new-group branch.

**Submit.** The handler clears all inline errors, then:

1. If the user picked the new-group branch, `POST
   /api/runs/<project>/groups` with `{name: <group>}`. On
   409, surfaces "Group already exists in this project."
   under the group-name input and returns; the user's
   other inputs (project select, run name) are preserved.
   On other failures, surfaces the server's message verbatim.
   The endpoint auto-creates `<project>/test-run/` if absent.
2. `POST /api/runs` with `{project, group, name, file_name,
   case_paths: [], description: ""}`. On 409, surfaces "A
   run with this name already exists in this group." under
   the run-name input and returns; on other failures,
   surfaces the server's message under the same input.
3. On 201, closes the modal and issues
   `htmx.ajax("GET", "/ui/run/<project>/<group>/<file_name>.yaml",
   {target: "#main-pane", swap: "innerHTML"})` to open the
   run editor where the user fills in description, adds
   cases, and sets results.

The modal stays open on any error so the user can correct
just the offending input. The slug preview, the reveal-on-
select toggle, and the inline-error clearing are all
driven by simple per-input listeners (`change` on the
`<select>`s; `input` on the text inputs).

### Case picker (`tmsBuildCasePicker`)

- Flat checkbox table sorted by folder path ASC, then file
  name ASC.
- Sticky header inside a `max-h-72` scroll container.
- Live-filter input above the table; counter reads
  `"N cases"` / `"K of N selected"` / `"K shown · M
  selected"` depending on filter state.
- Click-row-to-toggle (not just the checkbox) for cheaper
  selection.
- Header-row tri-state checkbox (`<input data-role="select-all"
  aria-label="Select all visible">`) toggles every **currently
  visible** row in one click. Respects the live filter — when a
  filter narrows the set, the checkbox toggles only the rows that
  match. State reflects only visible rows: `0/N` → unchecked,
  `N/N` → checked, `1..N-1` → indeterminate. Hidden-but-checked
  selections are preserved across filter changes and across
  bulk toggles; `getSelected()` continues to return the union of
  visible + hidden checked rows. The header is checkbox-only as a
  click target (not the whole `<th>`) so accidental bulk
  operations are rarer; with zero visible rows it stays enabled
  and clicks are a self-correcting no-op.
- Empty states: `"No .feature files in this project yet."`
  if the project has nothing; `"All test cases are already
  in this run."` if every case is in the exclude set. The
  empty-state path replaces the entire `<table>` so no header
  checkbox is rendered.

## Affects

- **`02-storage-core`** — new run-related methods, the depth-
  2 reservation rule, `RESERVED_DEPTH2_NAMES` constant,
  `validate_run`, `_normalize_run_filename`. New error type
  `RunParseError`.
- **`04-folder-crud`** — `create_folder` rejects depth-2
  `test-run` and anything under `test-run/<group>/...`.
- **`05-testcase-crud`** — `create_file` rejects `.feature`
  files anywhere under `test-run/`.
- **`06-tree-pane`** — `list_tree` skips `test-run` at depth 1.
  The pane lives in the **Directory tree** sidebar tab; the
  sibling **Test run** tab is owned by the sidebar-restructure
  spec.
- **`07-folder-views`** — the `ui_folder` dispatcher gains the
  `segments[1] == "test-run"` branch; the project view filters
  `test-run` out of its module table.
- **`08-file-editor`** — no direct contract change. The run
  editor borrows the dirty / Save / Reload / Saved badge /
  external-change banner vocabulary verbatim so the two
  editors feel like one product.

## Depends on

- `02-storage-core` primitives — per-path locks, atomic
  writes, `_mark_write`, `_validate_segment`.
- `03-watcher-and-sse` — `.yaml` files inside the data root
  flow through the same watcher / debounce / EventBus
  pipeline as `.feature` files (no watcher changes were
  needed — debounce is path-agnostic).
- The sidebar-restructure spec for the **Test run** sidebar
  tab (this feature only consumes it and wires its leaves).
- `tmsOpenModal` (modal primitive in `app/static/03_folder_actions.js`),
  `htmx.ajax` for the post-save / post-reload navigation,
  Tailwind for layout.
- `pyyaml` (`requirements.txt`).

## Surface for follow-up

- The reserved-name rule sets a precedent. A future
  `test-report/` typed area will likely want the same
  mechanism — generalise `RESERVED_DEPTH2_NAMES` into
  `RESERVED_TYPED_AREAS: dict[str, TypedAreaSpec]` if a
  second area lands.
- Tombstone-on-render is an `is_file()` per row at render
  time. Cheap for typical runs (<200 cases); becomes O(N)
  storm at larger sizes. Consider caching keyed by
  `_mark_write` invalidation if it matters.
- **Same-process SSE suppression caveat.** The watcher's
  `was_recently_written` is per-`Storage` instance, not per-
  tab. With one Flask process serving multiple browser
  tabs, tab A's Save silences the SSE event for **both**
  tabs — the spec's "open in two tabs and Save in A → B
  sees the banner" smoke only fires end-to-end for
  out-of-band edits (`git restore`, terminal `vim`, another
  Flask process). Same caveat applies to `08-file-editor`;
  not a Phase 3 regression. Fixing it (per-session
  suppression) is its own decision.
- **Bulk row mutation.** Selecting N rows and flipping them
  to `PASSED` in one click is a high-value affordance the
  per-row PATCH endpoint already supports. Add a row-
  selection column + a "Set selected to..." toolbar in the
  editor when prioritised.
- **Run templating.** `POST /api/runs?source=<existing>`
  would clone an existing run's case list into a new run
  with all rows reset to `PENDING`. Useful for "weekly
  regression" workflows.
- **Conflict UX for concurrent editors.** Currently silent
  last-write-wins. Same as `08-file-editor`.
- **Per-row keyboard navigation.** `Tab` between selects /
  remarks works via native focus order, but `j/k` row
  navigation or `Enter`-to-next-row would speed bulk
  triage.
- **Project creation from the create modal.** The current
  zero-projects branch is a dead-end ("No projects yet —
  create one first."). A future iteration could let the
  user create a project inline by replacing the project
  `<select>` with a combobox-style input that accepts new
  names; right now project creation happens through the
  Directory tree only. (The earlier "surface the slug as a
  hint" follow-up shipped as the live "will save as
  `<slug>.yaml`" preview under the run-name input.)
- **Status rename history.** The `EXECUTING` value was
  previously called `IN-PROGRESS`; renamed Jun 8, 2026 as a
  hard cutover with no read-time alias. Pre-rename YAMLs
  containing `result: IN-PROGRESS` fail `validate_run` with
  HTTP 422 — see `DONE.md` § Must have for context.

## Acceptance criteria

- `POST /api/runs` writes a YAML file at
  `<data-root>/<project>/test-run/<group>/<file_name>.yaml`
  with the supplied `case_paths` as `PENDING` rows and an
  empty remark; `created_at` is stamped server-side.
- Attempting to create a depth-2 folder named `test-run`
  via the generic folder API returns HTTP 409 via
  `NameConflictError`. The same name at depth 3 (e.g.
  `Alpha/Checkout/test-run`) succeeds.
- Attempting to create a folder anywhere under
  `<project>/test-run/<group>/` returns 409.
- Attempting to create a `.feature` file under
  `<project>/test-run/...` returns 409.
- Renaming, moving, or deleting a `.feature` file whose
  path appears in a run does **not** mutate the run. The
  next render of the run shows the now-missing case as
  tombstoned with strike-through, the
  `"test case was removed"` override, the hidden-but-
  preserved textarea, and the still-editable result select.
  Restoring the file at the original path un-tombstones the
  row on the next render and the stored remark reappears.
- PATCH-ing the same run payload twice in a row produces
  byte-identical YAML (canonical idempotence).
- The editor's Save reflects every field — `name`,
  `description`, each row's `result` and `remark` — and the
  `Saved` badge flashes ~1.5 s on success. Subsequent
  dirty edits clear the badge immediately.
- The editor's Reload confirms if the buffer is dirty and
  re-renders the partial via `/ui/run/...`, capturing a
  fresh baseline.
- `+ Add test case` opens the picker filtered to exclude
  cases already in the run; selected rows are appended as
  `PENDING` with empty remark; Save persists them.
- `×` on a row removes it from the editor; Save persists
  the removal; the YAML's `results` list is correspondingly
  shorter on the next read.
- External edit of the open run (via `git restore`,
  terminal `vim`, or another Flask process) drives the
  banner state machine: removed → red Discard banner;
  changed & clean → silent reload + blue info banner;
  changed & dirty → amber warn banner with Reload (discard
  mine) / Keep editing.
- External delete of the open run shows the red banner;
  clicking Discard navigates to the group view.
- The Test run sidebar tab aggregates every project with a
  `test-run/` folder; projects without one are omitted.
  Clicking a run leaf opens the editor in the main pane;
  clicking a group / project row is a non-navigable header
  in v1.
- The Directory tree sidebar tab and the project view's
  module table never show `test-run/` as a folder.
- Run files inside `test-run/<group>/` flow through the
  shared watcher / SSE pipeline; external creates / deletes
  of run files refresh the Test run sidebar tab on
  `sse:change`.
