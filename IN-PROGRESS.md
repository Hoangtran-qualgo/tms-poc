# In-progress backlog

Items observed during v1 manual verification that still need work. Grouped
by MoSCoW priority. Each entry should grow a short repro and pointer to the
relevant file(s) when picked up.

Convention: all **Investigate**-phase items default to **Should have** or
**Could have**; only file an Investigate item under **Must have** when it
is explicitly designated as such.

## Must have

- **Investigate: re-structure and decentralize the codebase.**
  _Filed Jun 10, 2026. Explicitly designated Must have (overrides the
  default Investigate → Should/Could placement)._
  - **Problem**: a few files have grown large and carry many distinct
    logics in one place (e.g. `app/storage.py`, `app/server.py`,
    `app/static/app.js`). Splitting them into smaller, single-purpose
    handlers/modules would lower the cost of changing any one feature.
  - **Goal**: decentralize features/functions to raise the codebase's
    maintainability, stability, scalability, and user-friendliness.
  - **Investigate** (scope to nail down before any code moves):
    - Map the current oversized files and the logical seams within
      each (which groups of functions are cohesive and could move
      together).
    - Propose a target module/handler layout (e.g. per-feature or
      per-domain split for storage, route blueprints split by area in
      `server.py`, controller modules split out of `app.js`).
    - Define the migration as small, behaviour-preserving slices with
      the smoke suite green (236/236) after each — no behaviour change,
      pure restructuring.
  - **Investigation — Jun 10, 2026 (PDCA: Plan / Do / Check done; Act =
    this writeup; Do step = code survey, no code written).**
    - **Verdict: feasible, mechanical, zero behaviour change, no new
      deps.** Every oversized file decomposes along seams that already
      exist as comment-banner sections. The whole effort is "move code
      behind a stable public surface", verifiable by the existing smoke
      suite (236/236) plus `node --check` for JS.
    - **Hotspots (measured Jun 10, 2026):**
      | File | Lines | Shape |
      |---|---|---|
      | `app/static/app.js` | 3554 | one flat global script, ~8 sections |
      | `app/storage.py` | 2258 | one ~2000-line `Storage` god-class |
      | `app/server.py` | 968 | two blueprints (`api`, `ui`), ~9 route groups |
      | `app/models.py` | 753 | feature + run + report dataclasses + validators |
      The rest are already right-sized: `gherkin_io.py` (494),
      `reporting.py` (329), `watcher.py` (207), `errors.py` (126).
    - **THE constraint that shapes the whole plan — preserve the public
      import + runtime surface.** A `grep` of import sites shows the
      coupling that any split must not break:
      - **Python**: `from app.storage import Storage` (77×), plus
        `TEMP_FILE_RE`, `RECENT_WRITE_TTL_SECONDS`, `MAX_FOLDER_DEPTH`,
        `cleanup_orphan_temp_files`, and even **private** names
        (`_normalize_run_filename`, `_PathLock`) are imported by smokes;
        `from app.server import api` / `_folder_crumbs`;
        `from app.models import Feature, Report, TestRun, RunResult,
        RUN_RESULTS, validate_*`, `_is_valid_tag`. `app/__init__.py`
        imports `api`/`ui` blueprints + `Storage`; `watcher.py` imports
        `TEMP_FILE_RE` + `RECENT_WRITE_TTL_SECONDS`.
        → Convert each god-file into a **package** whose `__init__.py`
        re-exports the current names verbatim. Import sites don't change.
      - **JS**: there is **no build step / no `package.json`** —
        `base.html` loads a single classic `<script src="app.js">`, and
        templates call the `tms*` functions from inline `onclick=` /
        HTMX `hx-on` attributes, so every function is an implicit global.
        → Split into **multiple ordered `<script>` files that stay in
        global scope** (NOT ES modules — that would force `window.`
        re-exports across every inline handler). Load order = dependency
        order, `bootstrap.js` last.
    - **Proposed target layout (per file).**
      - `app/storage/` package. Keep module-level constants + free
        functions (`TEMP_FILE_RE`, `cleanup_orphan_temp_files`,
        `_normalize_*`, `_PathLock`) in `app/storage/_core.py`. Split the
        class along its existing banners into **mixins**, one module each:
        `_paths.py` (split/validate/resolve/reserved), `_listing.py`
        (`list_root/tree/folder/projects`, `list_test_run_tree`),
        `_features.py` (read/create/write/delete/rename + atomic write),
        `_enums.py`, `_search.py` (+ `iter_feature_paths`), `_folders.py`
        (create/rename/delete/move/duplicate), `_runs.py` (run CRUD),
        `_reports.py` (report CRUD). `class Storage(PathsMixin,
        ListingMixin, … )` assembled in `__init__.py`, which also
        re-exports the constants. Public API (`storage.<method>()`)
        unchanged — mixins share `self.root`, `self._resolve`, `_lock_for`,
        `_mark_write` from a small base.
      - `app/server/` package. Define the `api` + `ui` blueprints once in
        `__init__.py`; move route handlers into side-effect modules that
        import the shared blueprints: `routes_folders.py`, `routes_files.py`,
        `routes_runs.py`, `routes_reports.py`, `routes_enums.py`,
        `routes_search.py`, `routes_tree.py`, `routes_ui.py`, plus
        `errors.py` (the 12 errorhandlers) and `_validators.py`
        (`_require_*`, `_folder_crumbs`). `__init__.py` imports them for
        registration and re-exports `api`, `ui`, `_folder_crumbs`. URL map
        is byte-identical.
      - `app/models/` package. `_feature.py` (Feature/Scenario/Step +
        `validate_feature` + `_is_valid_tag`), `_run.py` (TestRun/RunResult
        + `RUN_RESULTS` + `validate_run`), `_report.py` (Report +
        `REPORT_TYPES` + `validate_report`). `__init__.py` re-exports all.
      - `app/static/` JS split (global scope, ordered `<script>` tags in
        `base.html`): `tree.js` (~40), `sidebar.js` (~220), `modal.js`
        (tmsOpenModal + tmsApiPost + tmsRefreshFolder, ~250), `pickers.js`
        (case/run pickers + slugify + fillSelect, ~600), `create_flows.js`
        (tmsCreateFile/Run/Report + add-runs + edit-scope), `run_editor.js`
        (`tmsRunEditor`, ~500), `file_editor.js` (`tmsEditor`, ~1430 — the
        single biggest unit, do it on its own), `bootstrap.js` (init +
        event wiring, loaded last).
    - **Migration slices (ordered by risk ↑, each ends smoke-green).**
      1. **`server.py` → package.** Lowest risk: Flask blueprints are
         built for this; the route table is unchanged. Verify: full suite
         + assert URL map identical.
      2. **`models.py` → package.** Pure dataclasses; re-export keeps every
         `from app.models import …` working.
      3. **`storage.py` → package (mixins).** Medium risk (shared
         `self` state); do helper-extraction (serializers/parsers) first,
         then mixins one section at a time.
      4. **`app.js` → ordered files.** Highest coupling — see risks.
    - **Risks / caveats.**
      - **Static-inspection smokes read files by path.** Several smokes
        `grep` `app/static/app.js`, `app/storage.py`, `app/server.py` for
        function/route presence (e.g. `F12_24` JS-wiring, the `F10_*`
        js-wiring smokes). Moving code **will** break those greps; each
        such smoke must be repointed to the new file (or a glob) in the
        same slice. This is the main hidden cost, concentrated in the JS
        slice.
      - **Private-name imports by smokes** (`_normalize_run_filename`,
        `_PathLock`, `_folder_crumbs`) must be re-exported or the smokes
        repointed — they break silently otherwise (ImportError at
        collection).
      - **JS load order is now load-bearing.** A wrong `<script>` order
        = `ReferenceError` only at runtime (no build to catch it). Mitigate
        with `node --check` per file + a smoke that asserts the script tag
        order in `base.html`.
      - Mixin split must not introduce import cycles (each mixin imports
        only `_core` + stdlib, never a sibling mixin).
    - **Open questions (resolve before Plan).**
      1. **Scope of slice 1 only, or all four?** Recommend shipping one
         file's split per slice, suite-green between, rather than a big
         bang.
      2. **JS: split files vs. keep one + extract only `tmsEditor`?** The
         1430-line `tmsEditor` alone is ~40% of `app.js`; pulling just it
         out may capture most of the value at a fraction of the smoke-churn.
      3. **Re-export private names, or repoint the smokes?** Re-export is
         zero-churn but cements the privates as semi-public; repointing is
         cleaner but touches more smokes.
      4. **Does this warrant a `specs/features/13-…` spec, or is it an
         internal refactor tracked only here + `DONE.md`?** (Refactors so
         far — the smoke restructure — lived in `DONE.md` without a feature
         spec.)

## Should have

_(empty)_

## Could have

- **Investigate: persist expand-state for the Test run sidebar tab.**
  _Filed Jun 5, 2026 as a Phase-2 follow-up to
  `specs/features/10-feature-test-run-NEW.md`._

  The Directory-tree tab keeps expand state across SSE refreshes
  via `tmsExpandedFolders` + `tmsRestoreTreeState`. The Test-run
  tab is **stateless** in v1: every `sse:change` re-renders it
  with all groups collapsed. Investigate whether runs / groups
  grow enough per project (heuristic: >50) that this becomes
  annoying. If yes, add a sibling Set + restore helper scoped to
  `#test-run-pane`, hooked into `htmx:afterSwap`.

- **Investigate new feature: folder-level test case filter.**
  - From a folder view (from project/ level to single folder level), filter and list test cases by contain /
    not-contain rules over:
    - a specific tag.
    - a specific group of tags (all must match / none must match).
    - any tag within a specific group of tags (at least one matches).
  - Investigate the UX (chip-based filter bar vs. modal), the query
    surface (extension of `GET /api/search` vs. a new endpoint), and
    how it interacts with the existing tree / folder views.

- **Investigate: per-project `enums.yaml` CRUD UI.**
  _Deferred from `11-feature-testcase-component` v1 (Jun 8, 2026)._
  - Add / remove an enum kind, add / remove entries within a
    kind, rename a key with cascade across affected `.feature`
    files (rewrite every `# enum.<kind>: <old_key>` directive
    to `# enum.<kind>: <new_key>` atomically).
  - SSE-driven live refresh of in-session picker caches —
    lands together with the CRUD UI since the two share the
    invalidation path.
  - Out of scope until v1 of `11-feature-testcase-component`
    ships and teams start hitting the limits of the
    hand-edit-the-YAML flow.

