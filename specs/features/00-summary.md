# Feature summary & relationship map

Aggregated view of every feature spec in `/specs/features/`. Acts as
the inter-feature relationship index and the function-level workflow
map for the codebase.

**Maintenance rule**: this file is updated whenever a feature spec
is added, renamed, or has its three relationship sections changed.
The corresponding spec file remains the source of truth — entries
here are summaries, not duplications.

---

## Feature index

| `NN` | Spec file | One-line summary | Status |
|---|---|---|---|
| 01 | `01-feature-gherkin-io-NEW.md` | Parser + canonical serializer + model validation (pure text↔model). | Spec'd |
| 02 | `02-feature-storage-core-NEW.md` | Path discipline, atomic writes, per-path locks, self-write suppression. | Spec'd |
| 03 | `03-feature-watcher-and-sse-NEW.md` | Observer + debounce + recent-writes TTL + EventBus + SSE heartbeat. | Spec'd |
| 04 | `04-feature-folder-crud-NEW.md` | Folder create / rename / delete with depth 1..10. | Spec'd |
| 05 | `05-feature-testcase-crud-NEW.md` | `.feature` file create / read / update / rename / duplicate / move / delete. | Spec'd |
| 06 | `06-feature-tree-pane-NEW.md` | Left-sidebar tree + SSE-driven refresh + manual refresh button. | Spec'd |
| 07 | `07-feature-folder-views-NEW.md` | Main-pane folder browsing: root / project / module / sub-folder. | Spec'd |
| 08 | `08-feature-file-editor-NEW.md` | Structured tab + raw tab + save flow + dirty tracking + banner + reload. | Spec'd |
| 09 | `09-feature-search-NEW.md` | Search input + scope + match mode + 0 / 1 / ≥2 result UX. | Spec'd |
| 10 | `10-feature-test-run-NEW.md` | Typed-area test runs (`<project>/test-run/<group>/<run>.yaml`) with run editor, tombstone rendering, and external-change banner. | Spec'd |
| 11 | `11-feature-testcase-component-NEW.md` | Test-case project-level enums — generic `Feature.enums` map driven by `enums.yaml` (`<kind>: [- <key>: <label>]` schema; key stored on disk, label is display-only); component is the seeded kind; new kinds ship with zero code change; `# enum.<kind>: <key>` namespaced header-comment encoding (collision-free with regular comments); read-tolerant / write-strict orphan handling. | Spec'd |
| 12 | `12-feature-quality-report-NEW.md` | Persisted **Reports** (new reserved `<project>/report/<file>.yaml` area + sidebar tab) of one immutable `type`: enum-kind ranking, tag ranking, single-case trend (run-set data source), and static tag-presence inventory (folder data source; merges the `test report` item). Results recompute live from run results joined to current `Feature.enums` / tags; distinct-case counting; ≤ 10 runs. | Spec'd |

---

## Relationship sections per feature

Each subsection below mirrors the `## Affects` / `## Depends on` /
`## Surface for follow-up` sections of the corresponding spec.
Populated as each batch lands.

### 01 · gherkin-io

- **Affects**: `02-storage-core` (only caller of parse/serialize),
  `05-testcase-crud` (placeholder scenario construction),
  `08-file-editor` (consumes canonical JSON wire shape; raw-tab save
  triggers parse server-side), `09-search` (consumes parsed
  `Feature` objects).
- **Depends on**: `gherkin-official >=32,<33`; Python `>=3.12`; no FS,
  no network, no Flask.
- **Surface for follow-up**: any new on-disk syntax change starts
  here; new on-disk attributes extend `to_dict`/`from_dict` here
  first (`10-feature-test-run` opted to link cases by external
  `file_path` instead, so the dataclass was untouched); migrating
  off `gherkin-official` is a contained change.

### 02 · storage-core

- **Affects**: `01-gherkin-io` (sole caller of parse/serialize);
  `03-watcher-and-sse` (consumes `was_recently_written` and
  `TEMP_FILE_RE`); `04-folder-crud`, `05-testcase-crud`, `09-search`
  (HTTP routes delegate one-to-one); `06-tree-pane`, `07-folder-
  views` (render `list_tree`/`list_folder` output verbatim).
- **Depends on**: `01-gherkin-io`; `app/errors.py`; Python stdlib
  (`pathlib`, `os`, `secrets`, `time`, `threading`, `weakref`);
  POSIX `os.replace` semantics (same-filesystem only).
- **Surface for follow-up**: `10-feature-test-run` (shipped)
  layered run CRUD + `RESERVED_DEPTH2_NAMES` on top of these
  primitives, preserving the depth-0-is-a-project assumption by
  reserving the `test-run` name rather than introducing a separate
  typed-area concept; cross-device move support would need a
  fallback copy-then-delete; pluggable backends (S3, sqlite) live
  behind this module's surface.

### 03 · watcher-and-sse

- **Affects**: `02-storage-core` (consumes the self-write contract);
  `06-tree-pane` (only feature with `sse-swap="change"` wired today);
  all other UI features indirectly, via tree-driven re-render.
- **Depends on**: `02-storage-core`; `watchdog >=4,<7`; Python stdlib
  (`queue`, `threading`, `time`); single-process threaded Flask
  runtime (in-memory `EventBus`).
- **Surface for follow-up**: per-event payloads (`{kind, path}`)
  not emitted today — the four current consumers (tree pane,
  test-run sidebar, file editor, run editor) all refetch their
  full state on any `"change"` message; a future feature that
  needs to react to a specific file change must extend the bus
  protocol; multi-process deployment would require swapping the
  in-memory bus (e.g. Redis); bounded subscriber queues are
  wired in shape but not in value.

### 04 · folder-crud

- **Affects**: `02-storage-core` (one-line route delegations);
  `06-tree-pane` (every mutation → SSE "change" → tree refresh);
  `07-folder-views` (host the create buttons and re-render after
  mutation).
- **Depends on**: `02-storage-core`; `app/errors.py` (NameConflictError
  → 409, ValueError → 400); `app/static/03_folder_actions.js` (`tmsOpenModal` for
  sub-folder, `window.prompt` for project/module — legacy v1).
- **Surface for follow-up**: folder rename and delete UI buttons
  missing (API already exists); folder *move* not implemented;
  `10-feature-test-run` (shipped) layered a depth-2 reservation
  (`RESERVED_DEPTH2_NAMES = {"test-run"}`) and the
  "no folders under `<project>/test-run/<group>/`" rule on top
  of `create_folder`; unifying prompt-based vs modal-based create
  flows is cosmetic v1 debt.

### 05 · testcase-crud

- **Affects**: `01-gherkin-io` (every read/write parses or serialises
  through it); `02-storage-core` (eight underlying methods + atomic
  writes); `06-tree-pane` and `07-folder-views` (each mutation
  triggers tree + folder-view refresh); `08-file-editor` (rename /
  move / save / save-raw are invoked from the editor topbar).
- **Depends on**: `01-gherkin-io` (parse/validate/serialize);
  `02-storage-core` (eight file methods + locks);
  `app/static/03_folder_actions.js` (`tmsOpenModal`); editor topbar markup
  (`#btn-rename`, `#btn-move`, `#btn-save`, `#btn-save-raw`).
- **Surface for follow-up**: no UI surface for delete or duplicate
  today (API-only); `10-feature-test-run` (shipped) chose
  tombstone-on-render instead of run-list mutation, so rename /
  move / delete here are **not** coordinated with run files —
  orphaned rows render struck through on the next run-editor
  render; bulk operations would compose per-file methods;
  `PUT …/raw` is the only path exposing 422 parse_error to end
  users.

### 06 · tree-pane

- **Affects**: `02-storage-core` (consumes `list_tree()` output
  shape); `03-watcher-and-sse` (sole subscriber of the `"change"`
  event in v1 — every other feature relies on tree-refresh side
  effect); `07-folder-views` and `08-file-editor` (every link in
  the tree invokes their UI routes via HTMX).
- **Depends on**: `02-storage-core` (`list_tree`);
  `03-watcher-and-sse` (`sse:change` trigger); HTMX 2.x +
  `htmx-ext-sse@2`; `app/static/01_tree.js`
  (`toggleTreeFolder`, `tmsRestoreTreeState`, `tmsExpandedFolders`).
- **Surface for follow-up**: per-event SSE payloads would let the
  tree re-render only affected sub-trees instead of a full
  refetch; "current open file" highlight needs editor cooperation;
  drag-and-drop reorder/move not implemented (`05-testcase-crud`
  exposes the API); sidebar filter / search-as-you-type not
  implemented — users go through top-bar `09-search`.

### 07 · folder-views

- **Affects**: `02-storage-core` (every render is one `list_folder`
  call; return shape is the rendering contract); `04-folder-crud`
  and `05-testcase-crud` (host the create-button entry points;
  consume `tmsRefreshFolder` to repaint after mutations);
  `08-file-editor` (every feature row's `hx-get` opens the editor);
  `06-tree-pane` (shares `hx-get="/ui/folder/<path>"` navigation
  with tree folder-name spans).
- **Depends on**: `02-storage-core` (`list_folder`,
  `_folder_crumbs`); `04-folder-crud`/`05-testcase-crud` JS
  handlers; HTMX 2.x for row navigation; Tailwind CDN.
- **Surface for follow-up**: no per-row rename / delete / move /
  duplicate actions today (APIs exist); no column sort / filter;
  no multi-select bulk operations; `10-feature-test-run`
  (shipped) extended the dispatcher with a `segments[1] ==
  "test-run"` branch and added two typed-area templates
  (`folder_test_run_area.html`, `folder_test_run_group.html`).
  The typed area is exactly two levels under `ui_folder`; runs
  themselves are reached via the separate `/ui/run/...` route.

### 08 · file-editor

- **Affects**: `05-testcase-crud` (primary UI surface invoking
  rename/move/save/save-raw routes; renders their error envelopes
  inline); `01-gherkin-io` (consumes `Feature.to_dict()` shape;
  raw-save bytes feed server `parse_feature`); `06-tree-pane`
  (shares the page-level SSE connection; other tabs' trees refresh
  on save while writing tab's tree updates via post-save routing);
  `07-folder-views` (every feature-row click opens the editor).
- **Depends on**: `05-testcase-crud` (every HTTP route the editor
  calls); `01-gherkin-io` (wire-shape contract on structured tab);
  `03-watcher-and-sse` (`sse:change` listener for external-change
  detection); `tmsOpenModal` (move folder-picker); HTMX 2.x for
  post-save reroute; Tailwind CDN.
- **Surface for follow-up**: rename still uses `window.prompt`
  (should migrate to `tmsOpenModal`); no Delete / Duplicate
  buttons (APIs exist); external-change banner ignores parse
  state on disk; `10-feature-test-run` (shipped) opted for
  tombstone-on-render so this editor's post-rename / post-move
  hooks do **not** need to coordinate with open runs — the run
  editor recomputes `missing` per row every render; multi-tab
  editing of same file is permitted with silent last-write-wins.

### 09 · search

- **Affects**: `02-storage-core` (`Storage.search` is the entire
  backend); `07-folder-views` (main pane swaps to search results,
  then back via row clicks); `08-file-editor` (every result row's
  hx-get opens the editor); `06-tree-pane` (not directly affected;
  tree stays in place during search — only `#main-pane` swaps).
- **Depends on**: `02-storage-core` (`Storage.search` + data-root
  walk); `01-gherkin-io` (parsed `Feature` objects are what's
  searched); `tmsWireSearch` (debounce + Enter + on-change logic);
  HTMX `htmx.ajax(...)` for the swap; Tailwind CDN.
- **Surface for follow-up**: step text, feature tags, and examples
  tags not searched in v1 (would need new `match` values + new
  `matched_field` values); no regex / boolean / phrase operators
  (substring only); no result ranking; pending `test-report` reuses
  `Storage.search` with tag-presence aggregation; pending folder-
  level filter Investigate item likely extends search with
  contain/not-contain rules over tag groups (substring-only model
  would need an upgrade).

### 10 · test-run

- **Affects**: `02-storage-core` (new run CRUD methods +
  `RESERVED_DEPTH2_NAMES` constant + `_normalize_run_filename` +
  `RunParseError`); `04-folder-crud` and `05-testcase-crud`
  (depth-2 reservation + no-`.feature`-under-`test-run/` rules
  surfaced via `NameConflictError`); `06-tree-pane`
  (`list_tree` filters `test-run` at depth 1; the **Test run**
  sidebar tab lives alongside the Directory tree tab);
  `07-folder-views` (`ui_folder` branches on `segments[1] ==
  "test-run"` → `folder_test_run_area.html` /
  `folder_test_run_group.html`); `08-file-editor` (UX vocabulary
  borrowed — dirty, Save, Reload, Saved badge, external-change
  banner — for the parallel run editor).
- **Depends on**: `02-storage-core` primitives (locks, atomic
  write, `_mark_write`, `_validate_segment`);
  `03-watcher-and-sse` (`.yaml` events flow through the existing
  pipeline; no watcher changes needed); the sidebar-restructure
  spec (Test run tab lives in the vertical-tab sidebar);
  `tmsOpenModal` (create + add-case modals); `pyyaml` (pinned
  in `requirements.txt`).
- **Surface for follow-up**: `RESERVED_DEPTH2_NAMES` would
  generalise into a typed-area registry if a second area (e.g.
  `test-report/`) lands; tombstone-on-render is O(N) `is_file()`
  per render — may need caching at larger run sizes; bulk row
  mutation (set N rows to PASSED), run templating
  (`POST /api/runs?source=<existing>`), and per-row keyboard
  navigation are obvious next steps; same-process SSE
  suppression silences both tabs on the writer's own save
  (shared caveat with `08-file-editor`).

### 11 · testcase-component

_Spec'd Jun 8, 2026 — forward-looking Investigate spec.
Q1–Q5 all resolved; scope broadened same day from
single-`component` field to **generic enum map** driven by
`enums.yaml`. Plan/Do shipped Jun 8, 2026 in three slices
(S1 model, S2 storage, S3 HTTP + editor); see `DONE.md`
for the full as-shipped breakdown._

- **Affects**: `01-gherkin-io` / `app/models/` (new
  `Feature.enums: dict[str, str]` field, stores selected
  **keys** only; parser pre-parse scan for
  `# enum.<kind>: <key>` namespaced directives; serializer
  emits one alphabetically-ordered line per non-empty entry);
  `02-storage-core` (new `read_project_enums: dict[str,
  dict[str, str]]` and `init_project_enums`
  — `write_project_enums` is deferred to the CRUD-UI
  follow-up; `create_folder` depth-1 branch
  auto-writes the default `enums.yaml`; `write_feature`
  per-kind cross-check on **keys** only — labels are display-
  only); `04-folder-crud` (project create auto-init side
  effect; `enums.yaml` reserved at the project root);
  `05-testcase-crud` (422 on unknown kinds / keys, full
  `enums` map surfaced in `GET /api/files/<p>`); `06-tree-pane`
  / `07-folder-views` (`list_tree` / `list_folder` filter
  `enums.yaml` out of project-root listings — no UI surface
  for the file in v1 beyond the editor's init action);
  `08-file-editor` (structured-tab `Enums` section with one
  `<select>` per kind dynamically generated from the project's
  `enums.yaml`, fetched once per (project, session) and cached
  client-side, rendering `<option value="<key>">{label}` pairs;
  orphan warning badges; `Initialize enums file` legacy-project
  action); `09-search` (future filter-by-`<kind>`,
  follow-up).
- **Depends on**: `pyyaml` (already pinned); `02-storage-core`
  atomic-write + per-path lock primitives; `gherkin-official`
  continuing to tolerate leading `# enum.<kind>:` comments
  (same shape as the existing `# language:` directive).
- **Surface for follow-up**: unblocks the `quality-report`
  Investigate item (bucketing dimension =
  `Feature.enums["components"]`); a CRUD UI for `enums.yaml`
  is the obvious next step once hand-editing the YAML proves
  insufficient; a second enum kind (e.g. `priorities`) ships
  with **zero code change** — only product behaviour layered
  on a specific kind is new work; bulk-edit across N test cases
  is the obvious next ergonomic step once teams adopt a new
  kind retroactively.

### 12 · quality-report

_Spec'd Jun 9, 2026 — forward-looking Investigate spec (PDCA
investigation). Q1–Q5 + 8 follow-ups resolved same day; scope
broadened to merge the sibling `test report` tag-presence
inventory as a 4th report type (Option 2). Plan/Do shipped
Jun 10, 2026 in three slices (S1 model+aggregation, S2 storage,
S3 HTTP+UI); verified at 17/17 feature-12 + 236/236 full suite.
As-built deltas vs spec: added `GET /api/runs/<project>` for the
run picker, `case_trend` create uses a native `<select>`, the run
picker is flat-with-filter, the `sse:change` re-GET covers all
types (D5), and `tag_inventory` scope is editable via an
`Edit scope` action._

- **Affects**: `app/models/` (new `Report` dataclass +
  `validate_report` + `REPORT_TYPES`); `02-storage-core` (new
  `_REPORT_AREA`, `"report"` added to `RESERVED_DEPTH2_NAMES`,
  `create_report` / `read_report` / `write_report` /
  `delete_report` / `list_reports` / `list_report_tree`, new
  public `iter_feature_paths` helper, write-time cross-checks;
  `list_tree` / `list_folder` + `_reject_reserved_typed_area`
  hide / block the area via the existing reserved-name filter,
  no code change); `app/reporting.py`
  (**new** pure aggregation module); `app/errors.py` (new
  `ReportParseError`); `app/server/routes_reports.py` (`/api/reports/*` +
  `/ui/report*` routes + errorhandler); `base.html` (third
  sidebar tab + lazy `#reports-pane`); `app/static/02_sidebar.js` +
  `05_report_flows.js` (`tmsSwitchSidebarTab` extended, `tmsActivateReportsPane`,
  `tmsCreateReport`, run-picker); new `reports_sidebar.html` /
  `report_detail.html` templates; `IN-PROGRESS.md` (`test report`
  item merged here as Type 4).
- **Depends on**: `10-feature-test-run` (`TestRun` / `RunResult`,
  `RUN_RESULTS`, `list_runs` / `read_run`, reserved-area +
  sidebar-tab patterns this clones); `11-feature-testcase-
  component` (`Feature.enums`, `read_project_enums`, and the
  definitional-vs-historical decision licensing live enum reads);
  `01-gherkin-io` (`Feature.tags` / `Scenario.tags`,
  `read_feature`); `02-storage-core` (atomic write + locks,
  `_iter_feature_files`); `03-watcher-and-sse` (`sse:change`
  keeps the tab + detail view fresh); `pyyaml`.
- **Surface for follow-up**: saved multi-view dashboards become an
  additive 5th `type` (the original "Option 3", no migration);
  Reports-tab expand-state persistence (same shape as the Test-run
  tab item); CSV / clipboard export of a ranking; bulk run
  selection by filter on the add-runs picker (v1 is manual
  select); non-result trend metrics once runs carry richer
  metadata.

---

## Workflow relationships

End-to-end function chains for user-visible operations. Each
workflow names the modules / functions touched, in execution order.
Resolution target: 5–10 numbered steps each, enough to know which
3–4 modules a feature spans and in what order — not a full call
graph.

Twelve workflows populated (W1–W9 cover the file / folder / search /
SSE features; W10–W12 cover the test-run feature).

### W1 · App boot & initial render

1. `app/__main__.py` calls `create_app()`.
2. `create_app` resolves data root (`./project/`, created if
   missing), then `storage.cleanup_orphan_temp_files(root)` deletes
   any leftover `*.tmp.<pid>.<uuid>` files from a prior crash.
3. `Storage(root)` is constructed; `EventBus()` and
   `Watcher(storage, bus)` are constructed; `watcher.start()`
   spawns the `watchdog.Observer` daemon thread, scheduled
   recursively on the data root.
4. Blueprints `api` and `ui` are registered; the `/` route renders
   `templates/base.html` with `tree = storage.list_tree()`
   (server-side initial paint, no HTMX request needed).
5. Browser loads `/`, runs HTMX SSE setup against `/api/events`.
6. `sse_response(bus)` subscribes a fresh queue, yields
   `: connected\n\n`, blocks on the queue.
7. From here on the page is idle until either (a) a watcher event
   fires `bus.publish("change")` and HTMX swaps the tree pane, or
   (b) the user interacts with a control.

### W2 · Create a test case (file)

1. User clicks `+ Create test case` in `folder_module.html` (or
   `folder_subfolder.html`); the button's `onclick` calls
   `tmsCreateFile(parent)`.
2. `tmsCreateFile` opens a `tmsOpenModal` form with file-name +
   description fields; Confirm gated on both fields non-empty.
3. On Confirm, JS POSTs `/api/files` with `{file_name, description,
   parent}`.
4. `server.post_file` validates depth `2..10`, then delegates to
   `Storage.create_file`.
5. `create_file` normalises the leaf (auto-appends `.feature`),
   validates each segment, resolves under the data root, acquires
   the per-path `_PathLock`.
6. Constructs `Feature(description=…, scenario=Scenario(kind=
   "scenario", name=""))`, calls `serialize_feature` (from
   `01-gherkin-io`), then `_atomic_write_bytes` (write → fsync →
   `os.replace`), then `_mark_write(target)`.
7. Watcher observes the new file via `watchdog` but the path is in
   `_recent_writes` so `_should_emit` drops it. No SSE event for the
   writing tab.
8. Other open tabs receive a coalesced `"change"` event after
   `DEBOUNCE_SECONDS` and refresh the tree via `sse-swap="change"`
   wired to `#tree-pane`.
9. JS closes the modal and calls `tmsRefreshFolder(parent)` so the
   originating tab's main pane also reflects the new file.

### W3 · Rename / move / duplicate / delete a file

_Common shape: one storage method per operation, one HTTP route per
operation. Diverges only in which UI surface invokes it._

1. **Rename** — user clicks `#btn-rename` in `file_editor.html`;
   `tmsEditor.rename()` PATCHes `/api/files/<p>/rename` with
   `{file_name}`. `Storage.rename_file` acquires src+dst locks in
   sorted order, checks for name conflicts in the same parent,
   `os.replace`, `_mark_write` on both sides. Editor re-routes to
   `/ui/file/<newpath>` on success.
2. **Move** — `#btn-move` opens a tree-picker modal; on Confirm,
   `tmsEditor.move()` PATCHes `/api/files/<p>/move` with
   `{parent}`. `Storage.move_file` validates dest parent depth
   `2..10`, rejects same-parent attempts, acquires src+dst locks,
   `os.replace`, `_mark_write` on both.
3. **Duplicate** — API-only in v1 (no UI). POST
   `/api/files/<p>/duplicate` with `{file_name}`. `duplicate_file`
   acquires src+dst locks, copies bytes via
   `_atomic_write_bytes(target, source.read_bytes())`,
   `_mark_write(target)`.
4. **Delete** — API-only in v1 (no UI). DELETE `/api/files/<p>`.
   `delete_file` is idempotent: missing target returns 204.
   Otherwise `target.unlink()` + `_mark_write(target)`.
5. In every case the writing tab sees zero SSE events (self-write
   suppression); other tabs receive one coalesced `"change"`
   event.

### W4 · Edit & save a test case (structured)

1. User clicks a feature row in the tree or a folder view; HTMX
   GETs `/ui/file/<p>`; `ui_file` calls `storage.read_feature(p)`
   + `read_raw(p)`, renders `file_editor.html` with both shapes
   embedded as JSON in `#editor-data`.
2. `tmsBootEditor()` runs `tmsEditor.boot()`; state is hydrated
   with `feature`, `raw`, snapshots, `dirty: false`, default tab
   `structured`. Structured tab renders chips, steps, examples
   grids, data tables.
3. User edits any field; the field's `input`/`change` listener
   mutates `state.feature` and calls `markDirty(true)`. Save
   button enables (subject to non-empty description).
4. User clicks `#btn-save`; `tmsEditor.save()` runs
   `cleanupBuffer()` — drops empty steps, all-empty examples
   rows, all-empty body rows of each step's `data_table`. A
   data table whose every row (header AND body) is all-empty
   collapses to `data_table: null`. If kind=outline and zero
   examples blocks remain, abort via browser `alert`.
5. PATCH `/api/files/<p>` with `state.feature`. `server.patch_file`
   calls `Feature.from_dict(body)` then `storage.write_feature(p,
   feature)`.
6. `write_feature` validates (`validate_feature` from
   `01-gherkin-io`), `serialize_feature`s, `_atomic_write_bytes`,
   `_mark_write(target)`.
7. On 2xx, editor calls `_refreshFromDisk()` — refetches both
   `/api/files/<p>` and `/api/files/<p>/raw`, updates snapshots,
   `markDirty(false)`, re-renders both tabs — then `flashSaved()`
   (1.5 s badge). On non-2xx, browser `alert("Save failed: ...")`;
   buffer stays dirty (no refresh, no `markDirty(false)`).
8. Watcher emits `"change"` after debounce; other tabs refresh
   tree + (if open) the editor on those tabs runs
   `onExternalChange()` and silently reloads (clean buffer
   branch). Writing tab sees no SSE event.

### W5 · Edit & save a test case (raw)

1. User switches to the Raw tab; `tmsEditor` toggles `state.tab =
   "raw"` and renders the textarea with `state.raw`.
2. User edits the textarea; `markDirty(true)` fires on input.
3. User clicks `#btn-save-raw`; `tmsEditor.saveRaw()` PUTs
   `/api/files/<p>/raw` with the textarea's value as
   `text/plain`.
4. `server.put_file_raw` calls `storage.write_raw(p, text)`.
   `write_raw` invokes `parse_feature(text)` (canonicalises EOL,
   rejects `Rule:` blocks / multi-scenario), then
   `serialize_feature(feature)` (canonical form),
   `_atomic_write_bytes`, `_mark_write`. The bytes on disk MAY
   differ from the bytes sent.
5. On `GherkinParseError` → 422 `parse_error`; on `ValidationError`
   → 422 `validation_error`. Both render inline at `#raw-error`;
   buffer remains dirty.
6. On 2xx, editor calls `_refreshFromDisk()` so the structured tab
   also reflects the canonical form; `flashSaved()`.
7. SSE behaviour identical to W4.

### W6 · External rename / delete of the open file (banner)

1. External actor (terminal, IDE, another tab) renames or deletes
   the open file. `watchdog` observes the event; filters allow it
   through (not a temp file; not a self-write).
2. After `DEBOUNCE_SECONDS`, `bus.publish("change")` fires on the
   editor's tab. Both the tree pane (HTMX `sse-swap`) and the
   editor (JS `document.body` listener) react.
3. Editor: `tmsEditor.onExternalChange()` fetches
   `/api/files/<state.file_path>`. The server returns either the
   new content or a 404 (FileNotFoundError) for a removed file.
4. **Removed branch** (HTTP 404): editor shows a red banner
   "This file was removed on disk." with a `Discard` action. The
   in-memory buffer remains so the user can copy values out.
5. **Changed-and-clean branch** (`!state.dirty`): editor silently
   overwrites `state.feature` + `state.raw` + snapshots,
   re-renders both tabs, and shows a dismissable info banner
   "File was updated externally; the editor reloaded."
6. **Changed-and-dirty branch** (`state.dirty`): editor shows an
   amber warn banner "File changed externally while you have
   unsaved changes." with two actions: `Reload (discard mine)`
   (overwrites buffer + snapshots, hides banner) and `Keep
   editing` (hides banner without touching state).
7. The writing tab (the actor) never enters this workflow —
   `_mark_write` suppressed the watcher event for self-writes.

### W7 · Folder CRUD (create / rename / delete)

1. **Create** — user clicks `+ New project` / `+ New module` /
   `+ Sub-folder` in the corresponding `folder_*.html`.
   `tmsCreateProject` / `tmsCreateModule` use `window.prompt`;
   `tmsCreateSubfolder` uses `tmsOpenModal`. All POST
   `/api/folders` with `{name, parent}`.
2. `server.post_folder` delegates to `Storage.create_folder(parts)`.
   Storage validates each segment, enforces `1..10` depth, takes the
   per-path lock, `target.mkdir(parents=False, exist_ok=False)`,
   `_mark_write(target)`.
3. **Rename** — API-only in v1. PATCH `/api/folders/<p>` with
   `{name}`. `Storage.rename_folder` acquires src+dst locks in
   sorted order, checks parent-scoped name uniqueness,
   `os.replace`, `_mark_write` on both sides.
4. **Delete** — API-only in v1. DELETE `/api/folders/<p>`.
   `Storage.delete_folder` is idempotent on missing target;
   otherwise `shutil.rmtree(target)` + `_mark_write(target)`.
5. JS calls `tmsRefreshFolder` after create so the active main
   pane reflects the new folder.
6. Watcher suppresses the writing tab's events; other tabs get one
   coalesced `"change"` event → tree refresh.

### W8 · Search (text and tag)

1. User types in `#search-q`. `tmsWireSearch` schedules a fire
   after 300 ms (or immediately on Enter / scope-match-case
   change).
2. `fire()` runs `htmx.ajax("GET", "/ui/search?q=…&scope=…&
   match=…&case=…", { target: "#main-pane" })`.
3. `server.ui_search` reads query params, calls
   `storage.search(q, scope=…, match=…, case_sensitive=…)`,
   renders `search_results.html` with `hits` + `query`.
4. `Storage.search` walks the data root, parses each `.feature`
   via `01-gherkin-io`, applies the scope filter, then:
   `match="text"` substring-checks `Feature.description` (one hit
   max per file); `match="tag"` substring-checks each
   `Scenario.tags` value (one hit per matching tag).
5. Result variants render in `search_results.html`:
   - `len(hits)==0`: "No matches" message.
   - `len(hits)==1`: inline `<script>` calls
     `htmx.ajax("GET", "/ui/file/<file_path>", {target:
     "#main-pane"})` — auto-navigates to the editor.
   - `len(hits)>=2`: table with file path / first-line
     description / `@<matched tag>` or text badge; each row is an
     `hx-get` to the editor.
6. User clicks a row → editor opens (`08-file-editor` W4).

### W9 · SSE-driven refresh & manual refresh

_Two paths share the same target route (`/ui/tree`) and the same
state-restoration hook; they differ only in what triggers the
swap._

1. **Auto path** — an external FS change (terminal `touch`, IDE
   save, etc.) reaches `watchdog`. `_Handler._should_emit` filters
   out temp-file paths and self-writes; survivors call
   `_emitter.trigger()`.
2. After `DEBOUNCE_SECONDS` of quiet, `_DebouncedEmitter._fire`
   runs `bus.publish("change")`.
3. Every subscriber queue receives `"change"`; `sse_response`
   yields `event: change\ndata: \n\n` to each open tab.
4. HTMX SSE ext sees `sse-swap="change"` (via the
   `hx-trigger="sse:change"` on `#tree-pane`) and issues
   `GET /ui/tree`; server renders `tree.html` from
   `storage.list_tree()`; the partial replaces `#tree-pane`'s
   innerHTML.
5. The page's `htmx:afterSwap` listener detects `#tree-pane` was
   the target and calls `tmsRestoreTreeState()`, re-expanding any
   path still in `tmsExpandedFolders`.
6. **Manual path** — user clicks the `↻` button inside
   `tree.html`; HTMX issues `GET /ui/tree` directly
   (`hx-target="#tree-pane"`). Steps 4–5 above run identically.
7. The writing tab (when the change originated from this tab) sees
   *neither* path — `_mark_write` suppressed the watcher event;
   any UI refresh on that tab came from `tmsRefreshFolder` or a
   post-save reroute, not from SSE.

### W10 · Create a test run

1. User clicks `+ New run` in the Test-run sidebar tab header
   (the single, always-visible entry point). The button's
   `onclick` calls `tmsCreateRun()` with no arguments — the
   modal lives outside any project context.
2. `tmsCreateRun` fetches `GET /api/run-groups`, which returns
   `{projects: [...], groups: [{project, group}, ...]}`. If
   `projects.length === 0`, opens an info-only modal ("No
   projects yet — create one first.") with no Confirm button
   (`tmsOpenModal({confirmLabel: null})`) and stops here.
3. Otherwise, opens an `md` `tmsOpenModal` with two fields:
   - **Where** — `<select>` whose existing rows are emitted as
     `<optgroup label="<project>"><option value="proj|grp"
     >grp</option></optgroup>`, with a trailing non-grouped
     `+ Create new group...` option (`value="__new__"`).
     Selecting `__new__` reveals an inline sub-form with a
     project `<select>` (every existing project, including
     bare ones with no `test-run/` folder) and a free-text
     group-name `<input>`.
   - **Run name** — text `<input>`; the slug from
     `tmsSlugifyForFilename` renders live underneath as
     "will save as `<slug>.yaml`".
   Confirm is gated on `(slug non-empty) AND (path resolved)`.
4. On Confirm:
   - If the user picked `__new__`, JS POSTs
     `/api/runs/<project>/groups` with `{name: <group>}` first.
     `server.post_run_group` delegates to
     `Storage.create_run_group`, which auto-creates
     `<project>/test-run/` if missing. On 409 (`NameConflictError`)
     the message "Group already exists in this project."
     renders under the group-name input and submit aborts.
   - Then JS POSTs `/api/runs` with `{project, group, name,
     file_name, case_paths: [], description: ""}`.
     `server.post_run` delegates to `Storage.create_run`,
     which stamps `created_at` (UTC ISO-8601, seconds
     precision), constructs the `TestRun` with empty
     `results`, calls `validate_run`, then
     `_atomic_write_bytes` + `_mark_write(target)`. On 409,
     "A run with this name already exists in this group."
     renders under the run-name input.
5. On 201, JS closes the modal and
   `htmx.ajax`-navigates the main pane to
   `/ui/run/<project>/<group>/<file_name>.yaml`. The user
   fills in description, adds cases (via the run editor's
   `+ Add test case` flow, which reuses
   `tmsBuildCasePicker`), and sets results there.
6. Watcher emits `"change"` after debounce; other tabs' Test
   run sidebars refresh. Writing tab sees no SSE event
   (`_mark_write` suppression).

### W11 · Edit & save a test run

1. User opens a run editor — either by clicking a leaf in the
   Test run sidebar tab, by clicking a row in the group view,
   or as the post-create navigation from W10. HTMX GETs
   `/ui/run/<project>/<group>/<file_name>`.
2. `server.ui_run` calls `Storage.read_run(...)`, then for each
   row computes `missing = not (storage.root /
   r.file_path).is_file()` (tombstone-on-render). Renders
   `run_editor.html` with `run = TestRun.to_dict()` enriched
   with `missing` per row, plus `results_options = list(
   RUN_RESULTS)`.
3. The template's tail `<script>` calls `tmsBootRunEditor()`.
   `tmsRunEditor.boot()` reads `#run-editor` data-attributes
   (`project`, `group`, `file_name`, `created_at`), captures
   `baselineJson = JSON.stringify(_readCurrent())`, wires
   inputs + header buttons. The results `<tbody>` uses event
   delegation so rows added by `+ Add test case` are dirty-
   tracked + removable without per-row hookup.
4. User edits any field (`run-name`, `run-description`, per-row
   `.run-result-select` or `.run-remark`); `_refreshDirty()`
   stringifies the live DOM and compares against `baselineJson`,
   toggling `#run-dirty-indicator` and the Save button.
5. **Add case** path: `+ Add test case` calls
   `_onAddCaseClicked()`. Picker reuses `tmsBuildCasePicker`
   with the editor's current case paths as the exclude set. On
   Confirm, each selected path is cloned from the
   `<template id="run-result-row-template">` prototype
   (`PENDING` default), appended to the tbody, then
   `htmx.process(tbody)` rewires the new `hx-get` links.
   `_afterRowsChanged()` toggles table / empty-state visibility
   and refreshes dirty.
6. **Remove case** path: per-row `×` click bubbles through the
   tbody delegation; the `<tr>` is removed, then
   `_afterRowsChanged()`.
7. **Tombstone path**: rows with `missing` carry
   `run-row-missing` + `data-missing="1"` and render
   strike-through file path + `"test case was removed"`
   override; the `<textarea class="run-remark hidden">` is
   present-but-hidden so Save round-trips the stored remark
   verbatim.
8. **Save** path: `save()` PATCHes
   `/api/runs/<project>/<group>/<file_name>` with `{name,
   created_at, description, results}`. `server.patch_run` calls
   `TestRun.from_dict(body)`, then `Storage.write_run`, which
   runs `validate_run`, serialises (canonical YAML), and
   `_atomic_write_bytes` + `_mark_write`. On 2xx: update
   baseline, clear dirty, `flashSaved()` (1.5 s badge). On
   non-2xx: `alert(...)`, buffer stays dirty.
9. **Reload** path: confirms if dirty, then `htmx.ajax("GET",
   /ui/run/...)` re-renders the partial; the tail script
   re-mounts with a fresh baseline; tombstones are recomputed
   server-side.
10. Other tabs receive one coalesced `"change"` event →
    sidebar refresh + (if open on the same run) editor's
    `onExternalChange()` fires (W12).

### W12 · External change on the open run (banner)

1. External actor (terminal `vim`, `git restore`, another
   Flask process) modifies or deletes the run YAML. `watchdog`
   observes, filters allow it through, `bus.publish("change")`
   fires after debounce.
2. Body-level `sse:change` listener calls
   `tmsRunEditor.onExternalChange()` (and
   `tmsEditor.onExternalChange()` for the file editor; both
   are no-ops when their state is null).
3. The handler GETs `/api/runs/<project>/<group>/<file_name>`.
   On 404 → removed branch; otherwise normalises the response
   into the same shape `baselineJson` uses and compares.
4. **Removed** branch: red banner "This run was removed on
   disk." with `Discard` action. Discard navigates the main
   pane to `/ui/folder/<project>/test-run/<group>` (the group
   view), not the global root.
5. **No real change** (disk JSON equals baseline): no-op.
6. **Changed-and-clean**: `_reloadAndAnnounce("info", "Run was
   updated externally; the editor reloaded.")` stores the
   banner message in the `tmsRunEditor._pendingBanner`
   singleton sentinel, then `htmx.ajax("GET", /ui/run/...)`
   re-renders the partial. The freshly-mounted instance picks
   up the deferred banner inside `boot()` and shows it with a
   Dismiss action.
7. **Changed-and-dirty**: amber warn banner "Run changed
   externally while you have unsaved changes." with two
   actions: `Reload (discard mine)` (clears dirty, then takes
   the same `_reloadAndAnnounce` path) and `Keep editing`
   (hides banner without touching state).
8. The writing tab (same Flask process) never enters this flow
   for its own Save — `_mark_write` suppressed the watcher
   event for self-writes; multi-process or
   out-of-band edits are required to drive the banner end-to-
   end (same caveat as `08-file-editor` W6).
