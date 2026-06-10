# 01 · Restructure & decentralize the codebase

_Tech spec — forward-looking. Investigate done Jun 10, 2026 (PDCA;_
_writeup in `IN-PROGRESS.md` § Must have, "Investigate: re-structure_
_and decentralize the codebase"). Self-reviewed + refined Jun 10, 2026_
_(risk register added; slices re-ordered safest-first). Plan/Do pending_
_sign-off. Tracks the tech movement of the project, not a product feature._

## Summary

A few source files have grown large enough that any one change forces a
reader to scan unrelated logic. This spec scopes a **behaviour-preserving**
decomposition of those files into smaller, single-purpose modules /
handlers, decentralizing the code by feature/domain to raise
maintainability, stability, scalability, and ease of navigation.

There is **no functional change**: same HTTP surface, same on-disk
behaviour, same DOM behaviour. Success is "the smoke suite stays green
(236/236) after every slice, and the public import + runtime surface is
unchanged."

## Scope

In scope:

- Splitting the four oversized files into per-domain modules behind a
  stable public surface (Python packages with re-exporting `__init__`;
  ordered global JS files).
- Repointing the static-inspection smokes that read moved files by path.

Out of scope:

- Any behaviour, API, schema, or UX change.
- Introducing a JS build step / bundler / `package.json`.
- Converting JS to ES modules (would force `window.*` re-exports across
  every inline `onclick=` / `hx-on` handler).
- Rewriting logic "while we're in there" — moves only; no refactors of
  function bodies beyond what a move strictly requires.

## Current state — hotspots (measured Jun 10, 2026)

| File | Lines | Shape |
|---|---|---|
| `app/static/app.js` | 3554 | one flat global script, ~8 sections; `tmsEditor` alone ≈ 1430 |
| `app/storage.py` | 2258 | one ~2000-line `Storage` god-class, ~13 banner sections |
| `app/server.py` | 968 | two blueprints (`api`, `ui`), ~9 route groups + 12 errorhandlers |
| `app/models.py` | 753 | feature + run + report dataclasses + validators |

Already right-sized (leave alone): `gherkin_io.py` (494),
`reporting.py` (329), `watcher.py` (207), `errors.py` (126),
`sse.py` (59), `__init__.py` (76).

## Constraints — what the split must NOT break

1. **Python public import surface.** Imports observed across `app/` and
   `.smoke-scratch/`:
   - `from app.storage import Storage` (77×), plus `TEMP_FILE_RE`,
     `RECENT_WRITE_TTL_SECONDS`, `MAX_FOLDER_DEPTH`,
     `cleanup_orphan_temp_files`, and **private** `_normalize_run_filename`,
     `_PathLock`.
   - `from app.server import api`, `_folder_crumbs`.
   - `from app.models import Feature, Scenario, Step, TestRun, RunResult,
     Report, RUN_RESULTS, validate_feature, validate_run,
     validate_report, _is_valid_tag`.
   - `app/__init__.py` imports `api` / `ui` blueprints + `Storage`;
     `watcher.py` imports `TEMP_FILE_RE` + `RECENT_WRITE_TTL_SECONDS`.
   - → Each god-file becomes a **package** whose `__init__.py` re-exports
     the current names verbatim. Import sites do not change.
2. **No JS build step.** `base.html` loads one classic
   `<script src="app.js">`; templates call `tms*` functions from inline
   `onclick=` / HTMX `hx-on` attributes, so every function is an implicit
   global.
   - → Split into **multiple ordered classic `<script>` files in global
     scope**. Load order = dependency order; `bootstrap.js` (init + event
     wiring) loads last.
3. **Smoke suite is the safety net** — but several smokes read source
   files **by path** (`grep`/`read`), so moving code requires repointing
   them in the same slice (see Risks & mitigations, R2/R6).

## Target layout (per file)

### `app/storage/` package

- `_core.py` — module constants (`TEMP_FILE_RE`, `RECENT_WRITE_TTL_SECONDS`,
  `MAX_FOLDER_DEPTH`, `RESERVED_DEPTH2_NAMES`, extensions, `_FORBIDDEN_CHARS`),
  free functions (`cleanup_orphan_temp_files`, `_normalize_filename`,
  `_normalize_run_filename`, `_normalize_report_filename`), `_PathLock`,
  and a small `_StorageBase` holding `__init__`, `self.root`, the lock
  dict, `_resolve`, `_lock_for`, `_key`, `_mark_write`,
  `was_recently_written`.
- Mixins, one module each (split along the existing banner sections):
  - `_paths.py` — `_split`, `_validate_segment`, `_reject_reserved_typed_area`.
  - `_listing.py` — `list_root`, `list_tree`, `_tree_children`,
    `list_test_run_tree`, `list_projects`, `list_folder`.
  - `_features.py` — `read_feature`, `read_raw`, `_atomic_write_bytes`,
    `create_file`, `write_feature`, `write_raw`, `delete_file`,
    `rename_file`.
  - `_enums.py` — `read_project_enums`, `init_project_enums`,
    `_invalidate_enums_cache`, `_parse_project_enums`, `_cross_check_enums`.
  - `_search.py` — `search`, `_scope_to_segments`, `_iter_feature_files`,
    `iter_feature_paths`.
  - `_folders.py` — `create_folder`, `rename_folder`, `delete_folder`,
    `move_file`, `duplicate_file`.
  - `_runs.py` — run typed-area CRUD (`_run_segments`, `_serialize_run`,
    `_parse_run`, the 11 `*_run*` methods).
  - `_reports.py` — report typed-area CRUD (`_report_segments`,
    `_report_to_persisted_dict`, `_serialize_report`, `_parse_report`,
    `_cross_check_report`, the 6 `*_report*` methods).
- `__init__.py` — `class Storage(PathsMixin, ListingMixin, FeaturesMixin,
  EnumsMixin, SearchMixin, FoldersMixin, RunsMixin, ReportsMixin,
  _StorageBase)`; re-export the constants + free functions.
- **Invariant:** at *module* level a mixin imports only `_core` + stdlib,
  never a sibling mixin (prevents import cycles). Cross-mixin **method
  calls at runtime are fine** — they resolve on the composed `Storage`
  instance (e.g. `_folders.create_folder` calling
  `self._reject_reserved_typed_area` from `_paths`). Public API
  `storage.<method>()` is unchanged.

### `app/server/` package

- `__init__.py` — define `api` + `ui` blueprints once; import every route
  module for its registration side effects; re-export `api`, `ui`,
  `_folder_crumbs`.
- `_shared.py` — every cross-route helper (verified set): app accessors
  `_storage()`, `_bus()`; response/validation helpers `_error`,
  `_require_json_object`, `_require_non_empty_string`,
  `_require_list_of_str`, `_require_optional_str`; path helpers
  `_parent_to_segments`, `_leaf_name`, `_is_feature_path`,
  `_folder_crumbs`. Imported by every route module.
- Route modules (import the shared blueprints, attach handlers):
  `routes_tree.py` (tree + events), `routes_folders.py`,
  `routes_files.py`, `routes_runs.py`, `routes_reports.py`,
  `routes_enums.py`, `routes_search.py`, `routes_ui.py` (all `@ui` views).
- `errors.py` — the 12 `@api`/`@ui` errorhandlers.
- **Invariant:** the URL map is byte-identical (assert in a smoke).

### `app/models/` package

- `_feature.py` — `Feature`, `Scenario`, `Step`, `_is_valid_tag`,
  `validate_feature`, related constants.
- `_run.py` — `TestRun`, `RunResult`, `RUN_RESULTS`, `validate_run`.
- `_report.py` — `Report`, `REPORT_TYPES`, `validate_report`.
- `__init__.py` — re-export all public + the `_is_valid_tag` private that
  a smoke imports.

### `app/static/` JS split (ordered global `<script>` tags in `base.html`)

**Verified complete inventory (Jun 10):** 37 top-level functions + 6
`const`/`let` declarations + a bottom block (3 listeners —
`htmx:afterSwap`, `sse:change`, `beforeunload` — and the
`DOMContentLoaded → tmsBootShell` guard). **No declaration calls another
`tms*` at load time** (the `const`s are object/string/`null` literals), so
the *only* ordering constraint is that the bottom block (`bootstrap.js`)
loads **last**; files 1–9 may load in any order. Symbol → file:

1. `tree.js` — `tmsExpandedFolders`, `toggleTreeFolder`, `tmsRestoreTreeState`.
2. `sidebar.js` — `TMS_SIDEBAR_*`, `tmsSwitchSidebarTab`,
   `tmsActivate{TestRun,Reports}Pane`, the resize set (`tmsSidebarResize`,
   `tmsClamp/Set/Start…SidebarWidth`, `tmsOnSidebarResize{Move,End}`,
   `tmsResetSidebarWidth`), the collapse set
   (`tmsSet/ToggleSidebarCollapse`), `tmsInitSidebar`.
3. `modal.js` — `tmsApiPost`, `tmsRefreshFolder`, `tmsOpenModal`.
4. `pickers.js` — `tmsSlugifyForFilename`, `tmsFillSelect`,
   `tmsFetchProject{Feature,Folder}Paths`, `tmsBuildCasePicker`,
   `tmsBuildRunPicker`.
5. `create_flows.js` — `tmsCreate{Project,Module,Subfolder,File,Run,Report}`,
   `tmsAddReportRuns`, `tmsEditReportScope`.
6. `run_editor.js` — `tmsRunEditor` + `tmsBootRunEditor`.
7. `file_editor.js` — `tmsEditor` (≈1430 lines; biggest) + `tmsBootEditor`.
8. `util.js` — small order-free helpers `tmsEscape`, `tmsIsValidTag`,
   `tmsWireSearch` (boundaries flexible — all are globals, may merge).
9. `bootstrap.js` — `tmsBootShell` + the 3 listeners + `DOMContentLoaded`
   guard; loads **last** (calls `tmsWireSearch` / `tmsInitSidebar` /
   `tmsBoot{Run,}Editor`, all defined earlier).

## Migration strategy

Ship **one file's split per slice**, suite-green between slices (no big
bang). Order by genuinely ascending risk (safest first to build
confidence):

1. `models.py` → package — **safest**: pure dataclasses, no Flask app
   context, no side-effect imports.
2. `server.py` → package — low risk, but watch the **side-effect-import
   footgun** (R3): route modules must be imported in `__init__.py` or
   their routes silently vanish. Mitigated by the byte-identical URL-map
   assert.
3. `storage.py` → package (mixins) — medium risk (shared `self` state);
   helper extraction first, then one mixin at a time, suite-green between.
4. `app.js` → ordered files — **highest** coupling + most smoke churn;
   no build to catch load-order / `ReferenceError` mistakes. Do last.

## Acceptance criteria

- The smoke suite is **green after every slice** — no test deleted or
  weakened; static-inspection smokes repointed, not removed. The baseline
  (236) **rises** as the new verification smokes below are added; record
  the new total in `DONE.md`.
- `python -c "import app"` + `create_app()` boot unchanged; the Flask URL
  map is **byte-identical** before/after the `server.py` slice (a new
  permanent smoke asserts this against the pre-flight baseline dump).
- `node --check` passes for every new JS file; a new smoke asserts the
  `<script>` tag order in `base.html`; a manual browser pass confirms
  every inline `onclick=` / `hx-on` handler resolves (no `ReferenceError`).
- **Python** modules target ≤ ~600 lines. **JS is exempt from a hard
  cap**: `file_editor.js` (`tmsEditor`, ≈1430) stays largest unless
  open-question Q2 opts to sub-split it; the goal is one cohesive unit
  per file, not a line number.
- Public import surface (`from app.storage import Storage`, etc.)
  unchanged — verified by every existing import continuing to resolve.

## Risks & mitigations

Ordered by exposure (likelihood × impact). Each slice is a **single
git-revertable unit** — if it cannot go green, **revert it** and re-plan;
never leave the suite red between slices.

| # | Risk | Lik. | Impact | Mitigation |
|---|---|---|---|---|
| R1 | JS load-order / TDZ mistake → runtime `ReferenceError` (no build to catch it) | **Low** | High | **Verified: no load-time cross-refs among declarations** → only `bootstrap.js`-last matters; `node --check` per file; `base.html` script-order smoke; manual handler pass |
| R2 | Static-inspection smokes grep moved files by path → silent false failures | High | **Low** | Point reads at a **glob-concat of `static/*.js`** (verified concat-safe across every assertion pattern) → one uniform repoint. **Measured: ~30 JS smokes, 1 server, 0 storage/models** — churn is JS-only |
| R3 | A `server/` route module not imported in `__init__` → route silently disappears | Med | High | Byte-identical URL-map assert vs. pre-flight baseline |
| R4 | Private-name imports (`_normalize_run_filename`, `_PathLock`, `_folder_crumbs`, `_is_valid_tag`) break at collection | Med | Med | Re-export from package `__init__` (or repoint smokes — open Q3) |
| R5 | Mixin module-level import cycle | Low | Med | Mixins import only `_core` + stdlib (invariant above) |
| R6 | Tech-slice verification smokes not discovered (`run.py` globs `feature-*` only) | High | Med | Decide pre-flight: extend the glob to `{feature,tech}-*`, or house them under an existing feature dir |
| R7 | JS behaviour regression invisible to the suite (no Playwright) | Med | High | Manual browser pass mandatory in slice 4; residual risk accepted + documented |
| R8 | Scope creep — "improve while moving" | Med | Med | Moves only; body edits forbidden (Scope § out); review every diff line |
| R9 | Refactor on an uncommitted tree → per-slice `git revert` unreliable | **Low** | High | **feature-12 committed Jun 10** (tree clean bar prep docs); still branch the restructure off `feature/test-report` before slice 1 |

## Assumptions & confidence

_Self-investigation Jun 10, 2026 (re-eval after enumerating the repoint_
_set). Confidence by slice: **very high for slices 1 & 3** (models /_
_storage — zero path-repoints; re-export covers every private import),_
_**high for slice 2** (server — 1 path-repoint + URL-map assert), **high_
_for slice 4** (JS — full symbol map verified, no load-time coupling, and_
_the ~30-smoke repoint is uniform + concat-safe; the lone residual is_
_manual runtime verification, R7). No slice is below "high"; nothing_
_remaining is a structural-feasibility unknown._

**Confirmed against the code this session:**

- `models.py` imports only `.errors` (pure, no Flask / no side effects) →
  genuinely safest first. It defines `__all__` (19 names) → the package
  `__init__` must re-export **and** rebuild `__all__`.
- `storage.py` imports only stdlib / `yaml` / `.errors` / `.gherkin_io` /
  `.models` → `_core.py` can be a true leaf; no cycle with `models`.
- **Storage mixin coupling is light and direction-acyclic:** Listing →
  Features (`read_feature`), Search → Features, Reports → Enums
  (`read_project_enums` in `_cross_check_report`). Mixins are viable but
  **layered, not flat peers** (Features/Enums are foundational) — the
  "decentralized peers" framing is slightly optimistic.
- `server.py` has **no** `before/after_request` hooks or module-level app
  config; `_storage()` / `_bus()` read `current_app.extensions` → blueprint
  split is clean.
- `app.js` is IIFE-free and **all** top-level execution is the listeners at
  the bottom (`htmx:afterSwap`, `sse:change`, `beforeunload`,
  `DOMContentLoaded → tmsBootShell`) → load order is the only correctness
  constraint; everything else is call-time global resolution.
- No `mypy`/`pyright`/lint config exists → mixin `self.`-cross-refs fail no
  static gate (smokes + `node --check` are the only nets).
- No `from app.* import *` anywhere → re-export correctness is the sole
  package requirement.
- Stale line-anchored citations in `specs/` are small (8 across 2 files).
- **No smoke `conftest` / shared helper exists** — only `run.py`; each smoke
  imports `app.*` directly, so there is no shared fixture to break.
- **Exact repoint set enumerated (Jun 10, read-only grep):** files read *by
  path* — `app/static/app.js` ≈ 30 smokes (features 04–11), `app/server.py`
  1 (`F05_12`), `app/storage.py` **0**, `app/models.py` **0**. Private-name
  importers (4, all neutralised by `__init__` re-export): `_is_valid_tag`
  (F01_06), `_folder_crumbs` (F07_03), `_normalize_run_filename` (F10_59),
  `_PathLock`. → repoint cost ≈ **0 for models/storage, 1 for server, ~30 for
  JS** — slice 4 is the sole churn center.
- **`app.js` fully inventoried (Jun 10):** 37 top-level functions + 6
  `const`/`let` + a bottom listener block; **no declaration references
  another `tms*` at load time** → file order is free except `bootstrap.js`
  must be last (R1 → Low). Definitive symbol→file map is in Target layout.
- **The ~30 JS-repoint smokes are concat-safe:** all use the same
  read-then-search pattern (~5 path idioms); every negative/count assertion
  targets rendered HTML, a scoped function body, or a whole-file negative —
  all preserved when the read points at a **glob-concat of `static/*.js`**.
  So the repoint is one uniform pattern, not 30 bespoke edits (R2 impact ↓).

**Assumptions still unverified (status under Dispositions below):**

1. **Suite is actually 236/236 green** — **RESOLVED Jun 10**: confirmed
   236/236 via `.venv/bin/python .smoke-scratch/run.py` (the bare `python`
   shim fails — no PyYAML). Re-confirm before each slice.
2. **Exact repoint set** — **RESOLVED Jun 10** (enumerated above in
   Confirmed); no longer gating. JS holds ~30 of the ~31 path-reads.
3. **JS runtime behaviour after the split** — no Playwright; the inline
   `<script>` bootstraps in `run_editor.html`, `file_editor.html`,
   `search_results.html` are only exercisable by a manual browser pass.
4. **Byte-identical URL map after the server split** — plausible (Werkzeug
   sorts by specificity) but unproven until done.
5. **No hidden external consumer** — the grep covered `app/` + `.smoke-scratch/`
   only; out-of-repo or dynamic `importlib` users are unknown.

**Blind spots (not previously in scope):**

- **Dirty working tree** (R9): the just-seen `git status` shows 12 modified +
  several untracked feature-12 files. Starting here makes "revert a slice"
  unreliable — **commit feature-12 first.**
- Inline `<script>` in three partials reference `tms*` globals on HTMX swap —
  transparent to the split, but manual-test-only.
- `git` blame continuity fragments (a god-class split is not a clean `mv`).
- **Doc-reference blast radius is broad (measured):** the four files are
  named in many docs — `server.py` 14, `app.js` 12, `storage.py` 11,
  `models.py` 8. Most survive (still importable as `app.storage`), but the
  `.py` suffix turns cosmetically wrong once a file becomes a package, on
  top of the 8 line-anchored citations that actually break. Broad but
  low-severity cleanup.

**Dispositions (Jun 10, 2026 — user review):**

- *Suite 236/236 green* (#1) — **resolved Jun 10** (236/236 via
  `.venv/bin/python`). *Exact repoint set* (#2) — **resolved** (enumerated;
  ~30 JS, 1 server, 0 storage/models, + 4 private re-exports).
- *JS runtime behaviour* (#3, R7) — **manually self-verified by the user**;
  automated JS behaviour testing stays out of scope. Residual risk owned,
  not eliminated.
- *Byte-identical URL map* (#4) — **accepted.** The URL-map assert smoke is
  kept regardless, since its real job is catching a silently-dropped route
  (R3), not proving #4.
- *No hidden external consumer* (#5) — **accepted.**
- *Dirty working tree* (R9) — **resolved Jun 10**: feature-12 committed; tree
  clean except restructure-prep docs (README, this spec). Remaining: branch
  the restructure off `feature/test-report` before slice 1.
- Remaining blind spots — **accepted as documented.**

## Affects

- `app/storage.py`, `app/server.py`, `app/models.py`,
  `app/static/app.js` — each becomes a package / set of files.
- `app/templates/base.html` — single `<script>` tag becomes an ordered
  list of `<script>` tags.
- `.smoke-scratch/` — static-inspection smokes that read moved files by
  path must be repointed (notably `F12_24` JS-wiring and the `F10_*`
  js-wiring smokes); none deleted.
- `specs/features/02-feature-storage-core-NEW.md` and `00-summary.md` —
  "Source file" pointers and function-chain references may need updating
  to the new module paths once the moves land.

## Depends on

- The smoke suite remaining the sole regression gate (236/236; no other
  harness). Decision/condition coverage stays manual (coverage.py not
  installed, per prior decision).
- Python import semantics for packages (`__init__.py` re-export keeps
  `from app.<pkg> import <name>` stable).
- The no-build, global-scope JS runtime model (HTMX + inline handlers).
- `gherkin_io.py`, `reporting.py`, `watcher.py`, `errors.py` staying as
  single modules (not split here).

## Surface for follow-up

- Once `Storage` is mixin-split, a future "typed-area registry" (already
  mooted for a 2nd typed area beyond `test-run` / `report`) becomes a
  drop-in `_<area>.py` mixin rather than another section in a 2000-line
  file.
- A repointed, file-aware static-inspection convention (smokes that glob
  `app/static/*.js` instead of hard-coding `app.js`) makes future JS
  splits cheaper.
- If JS keeps growing, this split is the prerequisite for later adopting
  a real bundler / ES modules without a from-scratch rewrite.
