# 12 · Quality report (run-derived + static reports)

_Forward-looking Investigate-phase spec. Status: **Spec'd**
(Investigate signed off Jun 9, 2026; Plan/Do pending). Kicked off
Jun 9, 2026 from the `IN-PROGRESS.md` "Investigate new feature:
quality report" item, applying a PDCA investigation. Scope broadened
the same day: the sibling "test report" item's tag-presence inventory
was **merged in** as a fourth report type (Option 2), so this one
feature owns all reporting — both run-derived rankings/trends and the
static tag inventory._

## Problem statement

Teams record results in **test runs** (`10-feature-test-run`) and
tag test cases with **project-level enums** — `component`, `sprint`,
`priority`, … (`11-feature-testcase-component`) — and free-form
**tags**. What they cannot do today is *aggregate across runs* to
answer questions like:

- Which **component** fails most across the last few runs?
- Which **sprint** still has the most pending cases?
- Is this one flaky case getting better run-over-run?
- What share of our cases carry `@smoke`?

A **Report** is a saved, named artifact that answers exactly one of
these questions over a chosen data source, recomputed live whenever
the data source changes.

## Out of scope (for this spec)

- Charts / graphs of any kind. Rendering is tables + collapsible
  bullet lists only (mirrors the lock-in on the merged `test report`
  item: "no pie chart").
- A per-project `enums.yaml` CRUD UI — separate Investigate item.
- The `folder-level test case filter` item — distinct surface; this
  spec only *reads* tags, it does not add a filter bar to the tree.
- Editing run **results** — that stays in the run editor
  (`10-feature-test-run`). Reports are read-only over run data.
- Cross-project reports — a report's data source is confined to one
  project (decision Q6).

## Decisions (resolved Jun 9, 2026)

- **D1 — A Report is a persisted entity, mirroring test runs.**
  Stored as one YAML file under a new reserved per-project area
  `<project>/report/<file_name>.yaml`. Reached via a new **Reports**
  sidebar tab, never the Directory tree.
- **D2 — Each report has exactly one immutable `type`,** chosen in
  the create flow. The type fixes the report's *framing*; it cannot
  change after create (delete + recreate to switch).
- **D3 — Four types ship in v1** (Option 2):
  1. `enum_ranking` — rank enum keys of one kind by a chosen status,
     across the run set.
  2. `tag_ranking` — rank tags by a chosen status, across the run
     set (tags are multi-valued).
  3. `case_trend` — one test case's result across the run set, over
     time.
  4. `tag_inventory` — **static** presence % of **one chosen tag**
     (cases carrying it vs not) over the test cases under a folder
     scope (no runs). Merges the sibling `test report` item.
- **D4 — Two data-source shapes.** Types 1–3 take a **run set**
  (`run_paths`, editable after create); Type 4 takes a **folder
  scope** (`scope`, editable after create). A report carries exactly
  one shape.
- **D5 — Results recompute live on every render.** Nothing is cached
  on the report. Editing the run set, or editing the underlying
  `.feature` enums/tags or a run's results, is reflected on the next
  view. This is free: aggregation already reads live (see D6).
- **D6 — Enums/tags are read live, never snapshotted.** Confirmed by
  `11-feature-testcase-component-NEW.md:516-523` (enums are
  *definitional* and travel with the case; run results are
  *historical*) and `:573` (quality-report's bucketing dimension is
  `Feature.enums[kind]`). The join is `RunResult.file_path` →
  current `Feature.enums` / `Feature.tags`.
- **D7 — Count unit = distinct cases.** A case counts once per bucket
  if it hit the chosen status in **at least one** run in the set. The
  per-case run-by-run frequency is the job of `case_trend`, not the
  ranking count.
- **D8 — Config is fixed at create.** Types 1–2 fix `status` (and
  `kind` for Type 1); Type 3 fixes `case_path`; Type 4 fixes `tag`
  (and a `scope` that, like the run set, stays editable). Every
  report is self-describing and reproducible.
- **D9 — All statuses + all kinds selectable.** Status ∈
  :data:`RUN_RESULTS` (`PENDING / EXECUTING / PASSED / FAILED /
  SKIPPED`); kind ∈ every top-level key in the project's
  `enums.yaml`.
- **D10 — Tag scope = union** of `Feature.tags` and `Scenario.tags`,
  de-duplicated, for both `tag_ranking` and `tag_inventory`.
- **D11 — Synthetic buckets are shown, muted.** `(unset)` (case has
  no value for the kind / no tags) and `(removed)` (the
  `.feature` is missing or unparseable) appear as ranking rows so
  totals reconcile; they render visually de-emphasised.
- **D12 — Hard cap of 10 runs** per run-set report.
- **D13 — Empty data source is legal.** A run-set report created
  before any runs are added (`run_paths: []`) is valid and renders an
  empty state; the user adds runs afterward (mirrors create-run-then-
  add-cases).

## Design

### Data model — `Report` (`app/models/_report.py`)

A single dataclass with a `type` discriminator and a flat optional
config (only the fields relevant to the type are populated):

```python
RUN_SET_TYPES   = frozenset({"enum_ranking", "tag_ranking", "case_trend"})
FOLDER_TYPES    = frozenset({"tag_inventory"})
REPORT_TYPES    = RUN_SET_TYPES | FOLDER_TYPES

@dataclass(slots=True)
class Report:
    type: str = ""               # one of REPORT_TYPES
    title: str = ""              # human label (not the file name)
    created_at: str = ""         # ISO-8601, stamped server-side at create
    # run-set shape (types 1-3); data-root-relative POSIX run paths
    run_paths: list[str] = field(default_factory=list)
    # folder shape (type 4); data-root-relative POSIX folder path that
    # INCLUDES the project (e.g. "Alpha" or "Alpha/Checkout"), non-empty
    scope: str = ""
    # config (D8) — populated per type:
    status: str = ""             # enum_ranking, tag_ranking
    kind: str = ""               # enum_ranking
    case_path: str = ""          # case_trend
    tag: str = ""                # tag_inventory (the surveyed tag)
```

`to_dict` / `from_dict` round-trip every field. Unused fields stay
at their empty default and are omitted from the canonical YAML by the
serializer (see *On-disk schema*).

`validate_report(report)` raises `ValidationError` on:

- `type` not in `REPORT_TYPES`.
- `title` empty-after-strip or multi-line.
- `created_at` empty or multi-line.
- `enum_ranking`: `status` not in `RUN_RESULTS`; `kind` empty or not
  matching the enum identifier regex (`ENUM_IDENTIFIER_RE`).
- `tag_ranking`: `status` not in `RUN_RESULTS`.
- `case_trend`: `case_path` empty.
- `tag_inventory`: `tag` **or** `scope` empty-after-strip →
  `ValidationError`. `scope` is data-root-relative and **includes the
  project** (`Alpha` = the whole project; `Alpha/Checkout` = a
  subtree), consistent with `run_paths` / `case_path`.
- **Run-set types**: `len(run_paths) > 10` (D12); duplicate entries;
  any empty entry. `scope` and `tag` must be empty. An **empty**
  `run_paths` is legal (D13).
- **Folder type**: `run_paths` must be empty.

Cross-checks that need disk/project context (does the `kind` exist in
`enums.yaml`? do the `run_paths` resolve? is `case_path` a real
`.feature`?) are **not** model concerns — they live in storage
(write-time) and the aggregation engine (render-time, tolerant). This
mirrors `validate_feature` vs the storage enum cross-check in spec 11.

### On-disk schema — `<project>/report/<file_name>.yaml`

Canonical YAML, insertion-order keys, block style, UTF-8/LF, exactly
the populated fields. Example (Type 1):

```yaml
# Alpha/report/failed-by-component.yaml
type: enum_ranking
title: Most-failed components — Sprint 12
created_at: "2026-06-09T09:00:00+00:00"
status: FAILED
kind: components
run_paths:
  - Alpha/test-run/regression/2026-06-01.yaml
  - Alpha/test-run/regression/2026-06-08.yaml
```

Type 4:

```yaml
# Alpha/report/smoke-coverage.yaml
type: tag_inventory
title: Smoke coverage
created_at: "2026-06-09T09:05:00+00:00"
tag: smoke
scope: Alpha/Checkout
```

`_serialize_report` calls `validate_report` first (invalid reports
never reach disk) and emits only the fields relevant to `type`.
`_parse_report` wraps `yaml.YAMLError` and "root is not a mapping"
into a new `ReportParseError` (line/column when PyYAML pins one),
exactly like `_parse_run` / `RunParseError`.

### Aggregation engine — `app/reporting.py` (new, pure)

A new module of pure functions that take a `Storage` for reads and a
`Report`, and return a JSON-serialisable **view model**. Kept out of
`storage.py` so it is independently unit-testable and so persistence
stays focused on I/O.

```
compute_report(storage, project, report) -> dict
```

Common helpers:

- `_runs(storage, report)` — read each path in `report.run_paths` via
  `Storage.read_run`, ordered by `created_at` ASC (ties broken by
  path). A path that fails to resolve/parse is recorded as a
  `(removed)` run and skipped for counting but listed in the view's
  `warnings`.
- `_case_enums(storage, file_path)` / `_case_tags(...)` — read the
  `.feature` once (memoised per call) → `Feature.enums` /
  `union(Feature.tags, Feature.scenario.tags)`. `FileNotFoundError` /
  `GherkinParseError` → the case is bucketed `(removed)` (D11).

Per type:

- **`enum_ranking`** — collect the set of `file_path`s that recorded
  `status` in ≥ 1 run (D7). For each, bucket by
  `_case_enums(...).get(report.kind)` → key, or `(unset)` if empty /
  absent, or `(removed)` if unreadable. Emit buckets sorted by count
  DESC then label ASC, each with `{value, label, count, pct,
  cases:[{file_path, label}]}` where `pct = count / total_distinct`.
  `label` resolves the enum key→label from
  `Storage.read_project_enums(project)` (key shown verbatim if the
  vocabulary is missing the key).
- **`tag_ranking`** — same case set, but bucket by **every** tag in
  the case's union tag set (multi-valued, D10) — a case increments
  every tag bucket it carries; a case with no tags → `(untagged)`.
  `total_distinct` is still the count of distinct qualifying cases, so
  bucket percentages can sum to > 100 % (documented in the view as
  "cases may carry multiple tags").
- **`case_trend`** — for `report.case_path`, walk the ordered runs and
  emit `{run: <file_name>, created_at, result}` where `result` is the
  case's `RunResult.result` in that run or `"—"` (absent from that
  run). Also emit the case's current enums/tags for context, and a
  `tombstoned` flag if the `.feature` is now missing.
- **`tag_inventory`** — iterate `.feature` files under `report.scope`
  (via the public `Storage.iter_feature_paths(scope)` helper, see
  *Storage surface*); `total = count of cases`. Split into two
  buckets — **carrying** `report.tag` vs **not** (tag membership uses
  the union set, D10) — each `{count, pct}`, plus the matching-case
  lists. Unreadable files are counted into `warnings`, not the
  denominator.

The view model always carries `{type, title, created_at, total,
buckets|trend, warnings, params}` so the template branches on `type`.

### Storage surface (extends `02-storage-core`, mirrors `10-test-run`)

New reserved area constant and CRUD, structurally parallel to the
test-run methods in `app/storage/_runs.py`:

- `_REPORT_AREA = "report"`; add `"report"` to
  `RESERVED_DEPTH2_NAMES` (`app/storage/_core.py`). This **alone**
  hides the area from `list_tree` (depth-1 filter), the
  project module listing, and blocks generic creation of a
  `report` module — `_reject_reserved_typed_area`
  already reads the frozenset generically, so **no function change
  is needed**, exactly like `test-run`.
- `iter_feature_paths(scope) -> Iterator[str]` — a thin **public**
  wrapper over the existing private `_iter_feature_files` (`app/storage/_search.py`)
  + `_resolve`, returning data-root-relative POSIX paths under a
  folder scope. Added so the new `app/reporting.py` does not reach
  into storage privates (used by Type 4).
- `create_report(project, file_name, report)` — stamps `created_at`
  server-side (UTC ISO-8601, seconds), validates, atomic-writes.
  Auto-creates `<project>/report/` lazily (single intended writer,
  like `create_run_group` for `test-run/`). `NameConflictError` if
  the file exists; `FileNotFoundError` if the project is missing.
- `read_report(project, file_name) -> Report`.
- `write_report(project, file_name, report)` — atomic whole-doc
  replace of an existing file (the edit path for `run_paths` / `scope`
  / `title`); `FileNotFoundError` if missing.
- `delete_report(project, file_name)` — idempotent.
- `list_reports(project) -> list[dict]` — summary dicts
  `{file_name, title, type, created_at, source}` where `source` is
  `len(run_paths)` (run-set types) or the `scope` string (Type 4).
  Reports are **flat** under `<project>/report/` (no `group` level,
  unlike runs). Unparseable files listed with empty fields
  (best-effort, like `list_runs`).
- `list_report_tree() -> dict` — aggregated `report/` subtree across
  projects for the sidebar, mirroring `list_test_run_tree`
  (`app/storage/_listing.py`) but **two levels** (project → report leaf,
  no group level). Leaf rows are `type: "report"` and link to
  `/ui/report/<project>/<file_name>`.

**Write-time cross-checks** (in `create_report` / `write_report`,
after `validate_report`):

- `enum_ranking.kind` must be a top-level kind in the project's
  `enums.yaml`; missing-file or unknown-kind → `ValidationError`
  pointing at the kind (reuses the spec-11 pattern).
- Each `run_path` must live under `<project>/test-run/…` and resolve
  to an existing run file → else `ValidationError`.
- `case_trend.case_path` and `tag_inventory.scope` must resolve inside
  the report's project (first path segment == `<project>`) and exist
  at create time.
- Empty `run_paths` is accepted at create (D13); the cross-checks
  above apply per-entry only when entries exist.

Report filenames are normalised the same way as runs (`<slug>.yaml`,
reusing the `_normalize_run_filename` logic, generalised or
duplicated as `_normalize_report_filename`).

### HTTP surface (`app/server/routes_reports.py`)

JSON on the `api` blueprint, HTML partials on `ui`, matching the
project-scoped naming of `/api/runs/<project>/…` and `/api/enums/
<project>`:

- `POST /api/reports/<project>` — body `{file_name, title, type, …
  config}`. 201 on create; 409 on name conflict; 422 on validation /
  cross-check failure.
- `GET /api/reports/<project>` — `{reports: [...summary]}`.
- `GET /api/reports/<project>/<file_name>` — the `Report` dict.
- `PATCH /api/reports/<project>/<file_name>` — whole-doc replace
  (edit `run_paths` / `scope` / `title`). The route **loads the
  existing report first** and returns 422 if the incoming `type` or
  `created_at` differs from stored; `created_at` is preserved from
  disk regardless (matches the run editor's immutable `created_at`).
- `DELETE /api/reports/<project>/<file_name>` — 204, idempotent.
- `GET /ui/reports-tree` — Reports sidebar partial (mirrors
  `/ui/test-run-tree`).
- `GET /ui/report/<project>/<file_name>` — the detail view; calls
  `reporting.compute_report` and renders the per-type template. 404 if
  the report is missing.

New `@api.errorhandler(ReportParseError)` returns `422
report_parse_error` with `{line, column}` when available, registered
next to `RunParseError` / `EnumsParseError` (`app/server/errors.py`).

### UI surface (extends `base.html`, `app/static/02_sidebar.js` + `05_report_flows.js`)

- **Third sidebar tab.** Add a `data-sidebar-tab="reports"` button to
  `#sidebar-tabs` and a lazy-mounted `#reports-pane` `<aside>` to
  `#sidebar-panels` (`base.html:79-120`). Extend `tmsSwitchSidebarTab`
  (`02_sidebar.js`) to toggle the third pane and add
  `tmsActivateReportsPane` (clone of `tmsActivateTestRunPane`,
  `02_sidebar.js`) that attaches `hx-get="/ui/reports-tree"` +
  `hx-trigger="sse:change"` on first activation.
- **`reports_sidebar.html`** — clone of `test_run_sidebar.html`;
  project → report leaves; header has a `+ New report` button
  (`tmsCreateReport()`) and a refresh button. Empty state mirrors the
  run tab's.
- **`tmsCreateReport()`** — `tmsOpenModal` form: project select (when
  ambiguous), **file name** (live `<slug>.yaml` preview via
  `tmsSlugifyForFilename`, `04_run_create.js`), **title**, and a **type**
  `<select>`. On type change, reveal the type-specific config:
  - `enum_ranking` → status `<select>` + kind `<select>` (kinds from
    `GET /api/enums/<project>`).
  - `tag_ranking` → status `<select>`.
  - `case_trend` → a single-select case picker (reuse
    `tmsFetchProjectFeaturePaths` + `tmsBuildCasePicker`,
    `04_run_create.js`).
  - `tag_inventory` → a folder `<select>` (project modules /
    subfolders) + a tag `<input>` (the surveyed tag).
  POSTs `/api/reports/<project>`, then navigates `#main-pane` to
  `/ui/report/…` (same pattern as `tmsCreateRun`'s post-create nav).
- **Add / remove data source.** The detail view (run-set types) has a
  `+ Add runs` button opening a multi-select **run picker** modal
  (project → group → run, with a filter box and the ≤ 10 guard) built
  analogously to `tmsBuildCasePicker`; selections PATCH the report's
  `run_paths`. Removing a run is an inline row action. Type 4 exposes
  an editable `scope` select instead.
- **Detail templates** — one `report_detail.html` that branches on
  `view.type`:
  - ranking (Types 1, 2): a table `rank | value | count | %`, each
    row a collapsible disclosure revealing the matching cases (all
    collapsed by default; the `test report` render lock-in).
    `(unset)` / `(removed)` / `(untagged)` rows are muted. Matching
    cases are **grouped by folder** (filename-only items under a
    folder badge heading) per tech-02 E2.
  - inventory (Type 4): two collapsible rows — `carrying @<tag>` and
    `not carrying` — each with count / % and a folder-grouped
    matching-case list (tech-02 E2).
  - trend (Type 3): a table with one row per run (`created_at | run |
    result`), result cells colour-coded by status via the shared
    single-source `data-status` palette (tech-02 E4 / palette
    foundation); a tombstone banner if the case is missing.
  All run-set detail views (Types 1–3) carry `hx-trigger="sse:change"`
  → re-`GET /ui/report/...` so an edit to the underlying runs /
  `.feature` data refreshes the open report live (D5); an empty run
  set renders an empty state with the `+ Add runs` call to action
  (D13).

### Error handling

- Missing / unparseable run in a run-set report → that run is dropped
  from the computation and surfaced in the view's `warnings` strip
  (the report file itself is untouched — tombstone is render-time,
  matching the run-editor's case-tombstone model in spec 10).
- Missing / unparseable `.feature` for a counted case → bucketed
  `(removed)` (D11).
- A `kind` that was removed from `enums.yaml` after create → ranking
  still renders, keys shown verbatim, a warning notes the kind is no
  longer in the vocabulary. (Saving an *edit* that introduces an
  unknown kind is still blocked by the write-time cross-check.)

## Discoveries from the existing codebase

- Runs link to cases by external `file_path` only
  (`RunResult`, `app/models/_run.py`); there is no enum/tag copy on
  the run, so live reads are mandatory — which matches the definitional
  /historical split called out in spec 11 (`:516-523`).
- The reserved-typed-area machinery (`RESERVED_DEPTH2_NAMES`,
  `list_test_run_tree`, `list_runs`, `create_run*`) generalises
  cleanly to a second area; `report/` is a near-mechanical clone of
  `test-run/`.
- The sidebar already supports exactly two tabs with one lazy-mounted
  pane (`base.html:79-120`, `tmsActivateTestRunPane`); a third tab is
  additive.
- `Storage._iter_feature_files` + `read_feature` already back the
  search feature (`app/storage/_search.py`) and give Type 4 its
  folder walk for free.

## Affects

- `app/models/_report.py` — new `Report` dataclass + `validate_report` +
  `REPORT_TYPES` constants.
- `app/storage/` (`_reports.py` + `_REPORT_AREA` in `_core.py`) — `"report"` added to
  `RESERVED_DEPTH2_NAMES`; `_serialize_report` / `_parse_report`;
  `create_report` / `read_report` / `write_report` / `delete_report` /
  `list_reports` / `list_report_tree`; new public `iter_feature_paths`
  helper (Type 4 folder walk, so `reporting.py` avoids privates);
  `list_tree` + `list_folder` filtering and
  `_reject_reserved_typed_area` already key off `RESERVED_DEPTH2_NAMES`,
  so they pick up `report/` with no code change.
- `app/reporting.py` — **new** pure aggregation module.
- `app/errors.py` — new `ReportParseError` (alongside `RunParseError`,
  `EnumsParseError`).
- `app/server/routes_reports.py` — new `/api/reports/*` and `/ui/report*` routes; new
  `ReportParseError` errorhandler.
- `app/templates/` — new `reports_sidebar.html`, `report_detail.html`;
  `base.html` gains the third tab + pane.
- `app/static/02_sidebar.js` + `05_report_flows.js` — `tmsSwitchSidebarTab` extended;
  `tmsActivateReportsPane`, `tmsCreateReport`, run-picker helpers.
- `IN-PROGRESS.md` — the `test report` item is marked merged here as
  Type 4 (`:33-46`).
- `specs/features/00-summary.md` — must gain a `12` entry mirroring
  the three relationship sections below.

## Depends on

- `10-feature-test-run` — `TestRun` / `RunResult` schema, the
  `RUN_RESULTS` vocabulary, `list_runs` / `read_run`, and the
  reserved-area + sidebar-tab patterns this spec clones.
- `11-feature-testcase-component` — `Feature.enums`,
  `read_project_enums`, and the definitional-vs-historical decision
  that licenses live enum reads (no snapshot).
- `01-gherkin-io` / `app/models/` — `Feature.tags` /
  `Scenario.tags` for the tag dimension; `read_feature` parsing.
- `02-storage-core` — atomic-write + per-path lock primitives;
  `_iter_feature_files` (wrapped by the new public
  `iter_feature_paths`); the generic `RESERVED_DEPTH2_NAMES` filtering
  this area plugs into.
- `03-watcher-and-sse` — `sse:change` keeps the Reports tab and any
  open detail view fresh.
- `pyyaml` (already pinned).

## Surface for follow-up

- **Saved multi-view dashboards** — the original "Option 3": one
  report rendering several (status × dimension) sections. The `type`
  field makes this an additive 5th type, not a migration.
- **Expand-state persistence** for the Reports tab — same backlog
  shape as the existing Test-run tab item.
- **CSV / clipboard export** of a ranking table.
- **Trend across non-result metrics** (e.g. case count per run) once
  runs grow richer metadata.
- **Bulk run selection by filter** (e.g. "all runs in group X",
  "newest 5") layered on the add-runs picker — v1 is manual select
  only.
- Renaming the project folder carries `report/` with it by
  construction (sibling area), like `test-run/`.

## Operational notes

- **Reports are cheap to recompute, never cached** (D5). The detail
  view recomputes on every `GET /ui/report/...`; with the ≤ 10-run
  cap (D12) and per-call `.feature` memoisation, cost is bounded.
- **`created_at` and `type` are immutable** after create; `PATCH`
  rejects changes to either (422), matching the run editor's
  treatment of `created_at`.
- **Plan/Do slicing (suggested), strict linear order**, each slice
  independently smoke-testable under `.smoke-scratch/`:
  - **S1 — Model + aggregation.** `Report` + `validate_report`
    (`app/models/_report.py`); `app/reporting.py` for all four types. No HTTP,
    no storage. Smokes: distinct-case counting (D7), multi-valued tag
    buckets (D10, sum > 100 %), `(unset)`/`(removed)`/`(untagged)`
    buckets (D11), trend ordering + absent-run `"—"`, inventory %.
    **Blocks S2.**
  - **S2 — Storage + persistence.** `_REPORT_AREA`, reserved-name
    add, serialize/parse, `ReportParseError`, the CRUD methods,
    `list_report_tree`, write-time cross-checks. Smokes: round-trip,
    reserved-area hidden from tree + module listing, validation matrix
    (bad type, > 10 runs, empty run set is OK, unknown kind, missing
    `tag` for inventory, non-existent run/scope), PATCH rejects a
    changed `type` / `created_at`.
    **Depends on S1; blocks S3.**
  - **S3 — HTTP + UI.** `/api/reports/*` + `/ui/report*` routes,
    errorhandler, the third sidebar tab + lazy pane, `tmsCreateReport`
    + run-picker, the per-type detail templates. Smokes:
    create→navigate, sidebar aggregation, each type's rendered detail,
    add/remove runs PATCH. **Depends on S2.**

## Acceptance criteria

- Creating a report writes `<project>/report/<slug>.yaml` with the
  exact populated fields for its `type`, a server-stamped
  `created_at`, and round-trips byte-stably through PATCH → GET.
- The `report/` area never appears in the Directory tree or the
  project module listing; reports are reachable only via the Reports
  sidebar tab and `/ui/report/...`.
- `enum_ranking` over a run set ranks the project's enum keys for the
  chosen status by **distinct qualifying cases** (D7), shows labels
  resolved from `enums.yaml`, and includes muted `(unset)` /
  `(removed)` rows so counts reconcile against the total.
- `tag_ranking` buckets a case into **every** tag it carries (union of
  feature + scenario tags); a no-tag case lands in `(untagged)`.
- `case_trend` shows the selected case's result across the run set in
  `created_at` order, with `"—"` for runs that don't include it and a
  tombstone indicator if the `.feature` is gone.
- `tag_inventory` reports the count / % of cases **carrying** its
  chosen `tag` vs not, over the cases under its `scope`, with no
  dependency on any run; creating one without a `tag` returns 422.
- An empty-`run_paths` report is created successfully (D13) and its
  detail view renders an empty state with an `+ Add runs` action.
- Adding or removing a run (or editing the underlying `.feature`
  enums/tags, or a run result) changes the rendered report on the next
  view, with no edit to the report file required.
- Creating a run-set report with more than 10 runs, an unknown enum
  `kind`, or a non-existent run/scope returns 422 and writes nothing.
- A run path that no longer resolves is dropped from the computation
  and surfaced as a warning; the report file is left unchanged.

