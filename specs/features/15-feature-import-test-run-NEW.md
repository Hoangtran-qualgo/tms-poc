# 15 · Import a test run (upload an Allure HTML report → TMS test run)

_**SHIPPED Jun 15, 2026.** Pure Allure-2 parser (`parse_allure_report`) in
`app/allure_io.py`; storage write path (`import_test_run`) in
`app/storage/_runs.py` + project-wide name resolver (`resolve_scenarios`) in
`app/storage/_search.py`; API (`POST /api/runs/import/preview` +
`POST /api/runs/import`, 30 MB cap on both, all-or-nothing → 422
`import_validation_error {reasons}`) in `app/server/routes_runs.py`; UI
(top-bar `tmsImportRun()` modal) in `app/static/04_run_create.js` +
`app/templates/base.html`. The uploaded report is parsed in-memory and never
persisted — only the run `.yaml` is written. Covered by `F15_01`..`F15_06`
smokes (`.smoke-scratch/feature-15/COVERAGE.md`); full suite 295/295.
Decisions IR-1..IR-6 signed off Jun 15, 2026 (see §5, §8). Reference data:
`specs/sample-data/allure-report-single/index.html`._

## 1. Goal (from the backlog)

- The user uploads a generated **HTML test report**; the system transforms it
  into a TMS **test run** written under a chosen project's `test-run/` area.
- **Import modal inputs:** run **file name** (required) + run **name**
  (required); run **description** (optional). The user selects a **project**
  and a **destination directory** (the run **group** under
  `<project>/test-run/`).
- **Size limit = 30 MB** for the uploaded HTML.
- **created_at = the report's created time** (read from the report), not
  server-now.
- **Scenario mapping:** each report scenario maps to a TMS case **by scenario
  name**, **case-insensitive** (explicitly *temporary*).
- **Result mapping:** each report scenario's status maps to the run's per-case
  result (`RunResult.result`).
- **The raw report is transient.** The uploaded HTML is parsed **in-memory**
  for the request only; it is **never persisted** anywhere in the project (no
  archive, no attachment to the run). Only the resulting run `.yaml` is
  written. On success the modal also clears the file input client-side.
- **Open the imported run by default.** On success the new run opens in the
  main pane (run editor), same landing as the "+ New run" flow.

## 2. Why this is non-trivial (the core tensions)

1. **The report is not plaintext JSON.** The sample is an **Allure 2
   single-file report** (~2.6 MB `index.html`). All data is embedded as
   `d('<path>', '<base64-of-JSON>')` calls inside a deferred `<script>`
   (`window.reportData[name] = value`). Extracting anything requires
   collecting those calls, base64-decoding, and JSON-parsing — there is no
   naive JSON/regex shortcut. _(Verified: **40** embedded `d('<path>','<b64>')`
   keys incl. `data/suites.json`, `data/behaviors.json`,
   `widgets/summary.json`, and one `data/test-cases/<uid>.json` per test;
   report `allureVersion: 2.42.0`, `single_file: true`.)_
2. **`created_at` is server-stamped today.** `Storage.create_run` stamps
   `created_at = datetime.now(UTC)` and *callers cannot override it*
   (`root/app/storage/_runs.py:227-275`).
   Honoring the report's time needs a new/extended write path.
3. **The report gives names; a run needs case paths.** `RunResult.file_path`
   is a data-root-relative `.feature` path
   (`root/app/models/_run.py:17-36`), but
   the report only carries scenario **names**. We must resolve name → case
   path by scanning the project, case-insensitively — and decide what happens
   for **unmatched**, **duplicate**, and **ambiguous** names.
4. **Run invariants constrain the mapping.** `validate_run` requires a
   non-empty single-line `name` + `created_at`, **unique non-empty
   `file_path`s**, and each `result ∈ RUN_RESULTS`
   (`root/app/models/_run.py:83-143`;
   `RUN_RESULTS = PENDING|EXECUTING|PASSED|FAILED|SKIPPED`,
   `root/app/models/_common.py:40-46`).
   Two report scenarios resolving to the same case path would violate the
   uniqueness rule.

## 3. Current state (grounded)

- **Allure single-file format (verified against the sample):**
  - Loader: `<script async>` defines `d(name,value)`; a deferred
    `Promise.allSettled([...])` runs one `d('<path>','<b64>')` per data file
    (`index.html` lines ~44-52).
  - `widgets/summary.json` → `{reportName, statistic{passed,failed,broken,
    skipped,unknown,total}, time{start,stop,duration,...}}`. **`time.start`
    is epoch-ms of the run start** = the natural created time.
  - `data/suites.json` → tree `{uid,name,children[...]}`; **leaves** carry
    `{name, uid, status, time{start,stop,duration}, flaky, tags}`. The sample
    flattens to 10 unique leaves, all `passed`.
  - Per-test `data/test-cases/<uid>.json` → `{name, fullName, status, ...}`
    where `name` is the scenario name and `fullName` is `"<Feature>: <name>"`.
- **Run model / storage:** `TestRun{name, created_at, description,
  results[RunResult{file_path,result,remark}]}`; `create_run(project, group,
  name, file_name, case_paths, description)` seeds every result `PENDING` and
  server-stamps `created_at`; `write_run(...)` does a whole-doc replace of an
  **existing** file (`_runs.py:227-315`). Destination = a **group** folder
  under `<project>/test-run/`; groups are created by `create_run_group`
  (lazy-creates `test-run/`).
- **Project-wide case walker exists:** `Storage.iter_feature_paths(scope)`
  yields every `.feature` path under a scope (e.g. the project)
  (`root/app/storage/_search.py:151-169`) —
  the basis for the name→path resolver (read each, key on
  `feature.scenario.name`).
- **Import precedent (feature-14) to mirror:** preview + commit endpoints with
  a byte-size cap measured on the UTF-8 payload
  (`_MAX_IMPORT_BYTES`, `routes_files.py:22-37`); an **all-or-nothing**
  storage method that runs a **collect-all pre-flight** and raises
  `ImportValidationError{reasons[]}` (422) before any write
  (`import_feature_cases`, `_features.py:120-261`); a top-bar modal
  (`tmsImportFile`) with project + destination-folder selectors, a file
  input, a preview table, server-delegated validation
  (`03_folder_actions.js:281-624`). The run-create modal (`tmsCreateRun` +
  `GET /api/run-groups`) is the precedent for the **project + group** picker.

## 4. Decisions (LOCKED — signed off Jun 15, 2026)

- **IR-1 — Report formats supported (v1). [LOCKED: Allure 2 single-file only.]**
  Reject anything without the `d('...')` loader + `widgets/summary.json` with a
  clear `bad_request` ("unsupported report format"). A pluggable adapter is out
  of scope; note the seam for later.
- **IR-2 — Scenario source + name field. [LOCKED: `data/suites.json` leaves,
  leaf `name`.]** Flatten `data/suites.json` to its leaves (`children is None`)
  — one entry per executed test — and use the leaf **`name`** (not `fullName`).
  Verified: root `suites` → leaves carrying `{name, status, ...}`.
- **IR-3 — Status → `RUN_RESULTS` map. [LOCKED.]** `passed→PASSED`,
  `failed→FAILED`, **`broken→FAILED`**, `skipped→SKIPPED`,
  **`unknown→SKIPPED`**. (`EXECUTING` has no Allure source.) Unrecognized
  status string → `unknown` handling (→ `SKIPPED`).
- **IR-4 — created_at. [LOCKED + verified.]** `widgets/summary.json.time.start`
  (epoch-ms) → `datetime.fromtimestamp(ms/1000, tz=UTC).isoformat(
  timespec="seconds")` — the **same shape** `create_run` already produces
  (`root/app/storage/_runs.py:264-266`).
  `validate_run` only requires `created_at` **non-empty + single-line**
  (`root/app/models/_run.py:109-118`) — no
  format parsing — so this is accepted with zero risk. Requires a write path
  that accepts `created_at` + per-case `result` (see §5 DO-2). _Fallback if
  `summary` missing:_ earliest leaf `time.start`, else reject.
- **IR-5 — Name resolution: ALL-OR-NOTHING. [LOCKED.]** Resolve over the
  **whole destination project** (case-insensitive on `feature.scenario.name`).
  The import is **all-or-nothing**: it commits only when **every** report
  scenario resolves to **exactly one** case. The following abort the entire
  import (no partial write) with a collected list of per-scenario error lines
  in the format `<no>.<scenario name> : <message> - <reason>`; the user fixes
  the report and re-imports:
  - **Unmatched** — scenario name matches no case in the project.
  - **Project-side ambiguity** — the name matches **2+** cases in the project
    (cannot pick a single path). _**Accepted risk:** project-wide scenario
    names are **not** unique by design (feature-04 enforces uniqueness only
    within a 1-level folder scope), so legitimate cross-folder name reuse can
    trigger this. Tracked as a new Must-have: investigate a lightweight
    project-level scenario-name uniqueness solution._
- **IR-5b — Retries / report-side duplicates. [LOCKED: keep final result.]**
  Two report leaves sharing a name (case-folded) are treated as **retries of
  the same test**, not an error: collapse to a **single** result using the
  **final** run (the leaf with the latest `time.stop`, falling back to
  `time.start` / report order). This both honours retry reporting and keeps
  `file_path`s unique for `validate_run`.
- **IR-6 — Destination group. [LOCKED: pick existing only.]** List existing
  groups (`GET /api/run-groups` / `list_run_groups`) for the chosen project;
  no in-modal group creation in v1 (matches `create_run` requiring the group
  to exist).
- **IR-7 — Size cap.** 30 MB, enforced on both preview + commit (UTF-8 bytes),
  mirroring feature-14's helper.
- **IR-8 — Run name / file name.** Both required (run `name` non-empty
  single-line per `validate_run`; `file_name` normalized like other run
  files). Description optional.

## 5. Approach (decisions locked)

1. **DO-1 — Allure parser (pure, new `app/allure_io.py`).**
   `parse_allure_report(html: str) -> ParsedReport` where
   `ParsedReport{report_name, created_at_iso, scenarios:[{name, result}]}`:
   collect `d('<path>','<b64>')` calls, base64-decode the needed keys,
   read `summary.time.start` → ISO, flatten `suites.json` leaves → `(name,
   status, time.stop)`, **collapse same-name leaves to the final run** (max
   `time.stop`; IR-5b), apply the IR-3 status map. Raises a
   parse/`bad_request`-shaped error when the loader or `summary` is absent.
   No FS, no HTTP.
2. **DO-2 — storage import write path (verified).** Add
   `import_test_run(project, group, name, file_name, created_at, results,
   description="")` to `RunsMixin`, a **near-clone of `create_run`**
   (`_runs.py:227-275`) with two deltas: it takes `created_at` verbatim
   (instead of stamping `datetime.now`) and builds `TestRun.results` from the
   passed `RunResult`s (instead of seeding all-`PENDING`). Everything else is
   identical and reused: `_run_segments` (→ `_normalize_run_filename` appends
   `.yaml`, `_validate_segment` rejects forbidden chars), the
   group-must-exist `FileNotFoundError`, `target.exists()` →
   `NameConflictError`, `_serialize_run` (so `validate_run` still gates the
   write — unique non-empty `file_path`s, valid `result`s), `_atomic_write_bytes`
   + `_mark_write`. Chosen over extending `create_run` to keep its
   "fresh PENDING run" contract intact.
3. **DO-3 — name→path resolver (storage).** `resolve_scenarios(project,
   names) -> {matched:{name→path}, unmatched:[name], ambiguous:[name]}` built
   on `iter_feature_paths(project)` + `read_feature`, keyed on casefolded
   `scenario.name`. `ambiguous` = names matching 2+ project cases. (Report-side
   retries are already collapsed by DO-1, so `names` carries no duplicates.)
   Used by both preview + commit so they agree.
4. **DO-4 — API (in `routes_runs.py`, mirror feature-14, all-or-nothing).**
   Add a runs-local 30 MB cap helper (mirror `_require_import_source` /
   `_MAX_IMPORT_BYTES` from `routes_files.py:22-37`, field `html`), and reuse
   the existing `ImportValidationError` (422 envelope `details.reasons`) +
   `_require_non_empty_string` / `_require_optional_str` helpers.
   - `POST /api/runs/import/preview` — body `{project, html}`; parse (DO-1) +
     resolve (DO-3); returns `{report_name, created_at, scenarios:[{no, name,
     result, match: "matched"|"unmatched"|"ambiguous", file_path?}], counts,
     errors:["<no>.<name> : <message> - <reason>"]}`. No writes; `errors` is
     populated for every non-`matched` scenario so the UI can preview the
     blocking reasons.
   - `POST /api/runs/import` — body `{project, group, name, file_name,
     description?, html}`; re-parses + re-resolves server-side (preview is
     advisory only). If **any** scenario is unmatched / ambiguous, raise
     `ImportValidationError{reasons[]}` → **422** with the per-line error list
     and write nothing. Otherwise build one `RunResult(file_path, result)` per
     scenario and call `import_test_run(...)`. 30 MB cap on both.
_**Raw-report retention: NONE (locked).**_ Neither the API nor storage writes
the uploaded HTML. `import_test_run` writes only the run `.yaml`; the `html`
string exists solely within the request lifecycle and is discarded after the
run is written (or on any abort). There is no code path that saves the report
under `<project>/`.

5. **DO-5 — UI** (new `tmsImportRun`, top-bar button; structurally mirrors
   `tmsImportFile` @ `03_folder_actions.js:292-624`, with these grounded
   deltas):
   - **Button:** add an **"Import test run"** `<button>` in
     `app/templates/base.html` immediately **after** the existing
     "Import test cases" button (`base.html:24-26`), reusing its classes,
     `onclick="tmsImportRun()"`.
   - **HTTP helper:** use **raw `fetch`** (like `tmsImportFile`), **not**
     `tmsApiPost`. `tmsApiPost` (`03_folder_actions.js:5-20`) throws
     `Error(j.error.message)` and **drops `error.details.reasons`** — but the
     all-or-nothing 422 carries the per-line errors precisely in
     `details.reasons`, which the commit handler must read to feed
     `showError(msg, reasons)`.
   - **Destination:** fetch **`GET /api/run-groups`** (NOT `/api/tree`) →
     `{projects, groups:[{project,group}]}`, exactly like `tmsCreateRun`
     (`04_run_create.js:296-384`). Render a single **"Where"** `<select>` of
     existing `project|group` pairs (one `<optgroup>` per project); the
     selected option yields both `project` (for resolution) and `group` (for
     the write). **IR-6: drop the "+ Create new group…" row.** If `groups` is
     empty → info-only modal "No run groups yet — create one first."
   - **Inputs (distinct, per backlog):** **Run file name** (required text;
     server normalizes + appends `.yaml`), **Run name** (required), **Run
     description** (optional). _Unlike `tmsCreateRun`, file name is NOT derived
     from the run name — no slug preview._
   - **File:** `<input accept=".html,.htm">`, client size guard 30 MB,
     `await file.text()` → `POST /api/runs/import/preview {project, html}` on
     file change (and re-preview on "Where" project change).
   - **Preview table:** `# | Scenario | Result | Matched case`; unmatched /
     ambiguous shown as blocking error lines via the existing
     `showError(msg, reasons)` list (`<no>.<name> : <message> - <reason>`).
   - **Confirm gate:** where-selected + name + file_name non-empty **and zero
     blocking errors** (every scenario `matched`). On confirm →
     `POST /api/runs/import`; on 422 render `err.details.reasons`. On success:
     **clear the file input + cached `html`** (the report is not retained),
     `close()` the modal, `tmsRefreshTreePane("test-run-pane")`, and **open the
     new run by default** in the main pane via
     `GET /ui/run/<project>/<group>/<file_name>.yaml` (mirrors `tmsCreateRun`
     step 9c).
6. **ACT.** Smokes (§7), `COVERAGE.md`, `DONE.md`, clear the `IN-PROGRESS.md`
   Must-have, mark this spec shipped.

## 6. Out of scope

- **Non-Allure** report generators and **Allure 3 "awesome"** single-file
  (different embedding) — note the adapter seam only.
- Importing **steps / attachments / history / trends / timing** — only
  scenario **name + status** and the report's created time are used.
- **Editing** the run during import beyond name/file-name/description (post-
  import edits use the existing run editor).
- **Examples-/outline-level** result granularity (consistent with feature-14's
  feature/scenario-only tag model).
- Auto-**creating cases** for unmatched scenarios.
- **Retaining / archiving the raw HTML report** (or attaching it to the run) —
  the report is parsed in-memory only and never stored under the project.

## 7. Test plan (smokes, `feature-15/`)

- **F15_01 parser:** decode the sample `index.html` → correct `report_name`,
  `created_at` (from `summary.time.start`), and 9 `(name, PASSED)` scenarios
  (verified leaf count of `data/suites.json`);
  malformed/non-Allure input → parse error. **Synthetic nested `suites.json`**
  (epic→feature→story) flattens to the right leaves (depth-agnostic walk).
- **F15_02 status map:** each Allure status → expected `RUN_RESULTS` (IR-3),
  incl. the `broken`/`unknown` decisions.
- **F15_03 resolver + retry collapse:** matched / unmatched / ambiguous
  (project-side) classification over a seeded project (case-insensitive);
  **same-name leaves collapse to the final (latest `time.stop`) result**
  (IR-5b) and never trigger a duplicate-`file_path` abort.
- **F15_04 storage import:** written run preserves the report `created_at`,
  sets per-case `result`s, rejects duplicate `file_path`, `NameConflictError`
  on existing file.
- **F15_05 API preview/commit:** preview shape + counts + `errors` lines;
  commit succeeds only when **all** scenarios match (writes one result each),
  and returns **422** with per-line reasons when any scenario is unmatched /
  ambiguous; enforces the 30 MB cap. **Retention:** after a successful commit,
  only the run `.yaml` exists — no `.html` is written anywhere under the
  project tree.

## 8. Sign-off (Jun 15, 2026 — all resolved)

- **IR-1 — Source format:** Allure 2 single-file only (confirmed from the
  sample: `allureVersion 2.42.0`, `single_file: true`, `d('...')` loader).
- **IR-2 — Scenario source:** flatten `data/suites.json` leaves; use leaf
  `name`.
- **IR-3 — Status map:** `broken → FAILED`, `unknown → SKIPPED`.
- **IR-5 — Resolution:** **all-or-nothing**; **unmatched** and
  **project-ambiguous** abort the import with per-line errors
  `<no>.<scenario name> : <message> - <reason>`. Lookup scope = **whole
  project**.
- **IR-5b — Retries:** same-name report leaves collapse to the **final**
  result (latest `time.stop`), not an abort.
- **Accepted risks (Jun 15, 2026):** (a) project-ambiguity can reject
  legitimate cross-folder name reuse → new Must-have item to investigate
  project-level scenario-name uniqueness; (b) nested suite trees → covered by
  an F15_01 synthetic-nested smoke; (c) 30 MB parsed twice (preview+commit) →
  perf tracked manually.
- **IR-6 — Destination group:** pick an **existing** group only (no in-modal
  creation in v1).
