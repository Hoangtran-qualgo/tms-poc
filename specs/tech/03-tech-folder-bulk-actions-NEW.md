# 03 · Folder-detail test-case list — bulk selection + actions

_Tech spec. Filed Jun 11, 2026 (Investigate phase; promoted from_
_`IN-PROGRESS.md` § Must have). **Status: SHIPPED Jun 11, 2026** —_
_Plan + Do complete; full smoke suite **272/272**. As-built breakdown in_
_`DONE.md` § Must have; verification smokes in `.smoke-scratch/tech-03/`._
_Investigation was grounded against the live code Jun 11, 2026 — current-state_
_findings below carry file:line refs. The transient PDCA plan was removed on_
_Do-phase completion; this doc is now the as-built spec._

## Summary

Add a **multi-select bulk-action toolbar** to the folder-detail test-case
list (the `features` table rendered by `folder_module.html` and
`folder_subfolder.html`). The user selects one or more test cases via
per-row checkboxes, then applies one bulk action: **Move**, **Re-tag**,
**Run** (add to a test run), or **Delete**.

**Scope is strictly one level.** Actions apply only to the folder's
**direct** test cases — never to cases in sub-folders. Example: folder `A`
holds `test case 1` and sub-folder `B` holds `test case 2`; from `A`'s view
the toolbar acts on `test case 1` only. This falls out naturally because
the listing already separates direct sub-folders (`folders`) from direct
features (`features`) — see § Current state.

## Scope

In scope:

- A bulk-action toolbar above the `features` table in the depth-2 module
  view (`folder_module.html`) and the depth-3..MAX sub-folder view
  (`folder_subfolder.html`).
- A per-row selection checkbox + a select-all checkbox in the table header.
- Four bulk actions over the selected **direct** test cases: Move, Re-tag,
  Run, Delete.
- Per-action confirmation / progress / partial-failure feedback, and a
  deterministic list + tree refresh after each action.

Out of scope:

- Recursive (sub-folder-spanning) selection or actions.
- Selecting sub-folder rows (the sub-folder table stays click-to-navigate).
- New product semantics for runs, tags, or moves beyond what the existing
  single-item flows already do.
- The separate **folder-level test-case filter** backlog item (Could have);
  this toolbar is independent of it.

## Current state (grounded Jun 11, 2026)

**Listing already yields direct children only.** `Storage.list_folder`
returns `{folders, features}` where `features` is the list of direct
`.feature` files in the folder (feature-level + scenario-level tag union
after the Jun 11 fix). Sub-folders are a separate `folders` list. So the
"one level only" scope is the default data shape — no recursion to suppress.

**Two near-identical templates render the list:**

- `app/templates/folder_module.html:47-73` — depth-2 module view.
- `app/templates/folder_subfolder.html:48-73` — depth-3..MAX view.

Both render each feature row as a whole-row navigation target:

```@/Users/hoang.tv/Documents/Projects/tms/app/templates/folder_module.html:58-61
      <tr class="border-t border-slate-100 hover:bg-slate-50 cursor-pointer"
          hx-get="/ui/file/{{ module_path }}/{{ f.file_name }}"
          hx-target="#main-pane"
          hx-swap="innerHTML">
```

Implication: a selection checkbox lives **inside** a row whose entire body
is an HTMX navigation trigger. The checkbox cell must stop click
propagation so toggling selection does not navigate to the editor.

**Backend endpoints already exist for every action (single-item):**

- **Move** — `PATCH /api/files/<path>/move`, body `{ "parent": "<proj>/<mod>/..." }`
  (`app/server/routes_files.py:80-87` → `Storage.move_file`,
  `app/storage/_folders.py:127`). Rejects same-parent and out-of-depth
  destinations; preserves the leaf name.
- **Delete** — `DELETE /api/files/<path>` → `204`, **idempotent**
  (`app/server/routes_files.py:65-69` → `Storage.delete_file`,
  `app/storage/_features.py:129`).
- **Re-tag** — `PATCH /api/files/<path>`, body = a **full** `Feature` dict
  (`app/server/routes_files.py:57-62` → `Storage.write_feature`). There is
  **no partial tag patch**: re-tagging is a read-modify-write of the whole
  feature. `Feature.tags` is feature-level; `Feature.scenario.tags` is
  scenario-level (`app/models/_feature.py:176,178`).
- **Run (add case)** — `POST /api/runs/<project>/<group>/<file_name>/cases`,
  body `{ "file_path": "<data-root-relative .feature path>" }`
  (`app/server/routes_runs.py:126-131` → `Storage.add_run_case`).

**Listing endpoints for pre-flight (verified):**

- `GET /api/folders/<path>/contents` (and `/api/folders/contents` for root)
  → `Storage.list_folder` (`app/server/routes_folders.py:22-34`). At depth
  2..MAX returns `{kind, folders:[name], features:[{file_name, description,
  tags}]}`. Backs the Move **name-conflict** pre-flight (check each selected
  leaf against the dest's `features[].file_name`).
- `GET /api/tree` → full recursive tree (`routes_tree.py:11`); folder nodes
  carry `{type:"folder", path, depth, children}`, file nodes
  `{type:"feature"|"other", path}` (`_listing.py:45-84`). Backs the
  same-project Move folder picker (filter to the source-project subtree,
  folder nodes depth 2..MAX).
- `GET /api/runs/<project>/<group>/<file_name>` → the run incl.
  `results[].file_path` (`Storage.read_run`). Backs the Run **de-dup**
  pre-flight.

**Reusable client helpers already exist:**

- **Move picker — editor-internal, NOT a standalone helper.** The single-case
  move modal is a method on the editor singleton at
  `app/static/08_file_editor.js:778-920`: it sources folders from
  `GET /api/tree`, filters to valid `.feature` parents (depth 2..MAX),
  builds a `<select>` (current parent shown but disabled), and PATCHes
  `/api/files/<p>/move`. **Caveat:** it draws from the **whole tree (all
  projects)** today, so reuse for D4 (same-project-only) means **factoring
  the picker out + filtering to the source project** — not a free call.
- Run picker: `tmsBuildRunPicker` in `app/static/05_report_flows.js:22`
  (returns `{node, getSelected, countVisible}`); flat per-project run list
  via `GET /api/runs/<project>` (`app/server/routes_runs.py:166`).
  **Caveat:** it is **multi-select** (built for reports referencing up to 10
  runs); bulk-Run needs a **single** target run, so constrain to one
  selection or use a plain `<select>`.
- Tag chip input — `tmsEditor.renderChips(prefix, tags)`
  (`app/static/08_file_editor.js:170`) is **coupled to the editor's
  `state.feature` + fixed DOM ids** (`<prefix>-tags-chips/-input`); not a
  standalone widget. The Re-tag modal needs a small chip input (replicate
  the markup, validate with the tag grammar below).
- Tag grammar for the Re-tag pre-flight: `_is_valid_tag`
  (`app/models/_feature.py:207`) — non-empty, ASCII-printable 0x21–0x7E,
  **no whitespace, `@`, or `,`**. The client can replicate this exactly.
- Project feature-path fetch + case picker: `tmsFetchProjectFeaturePaths`,
  `tmsBuildCasePicker` in `app/static/04_run_create.js`.
- Shared modal primitive with Esc / Cmd+Return: `tmsOpenModal`
  (`app/static/03_folder_actions.js`).
- Refresh helpers (confirmed): `tmsRefreshFolder(folderPath)`
  (`app/static/03_folder_actions.js:22`, re-GETs `/ui/folder/<path>` into
  `#main-pane`) and `tmsRefreshTreePane(paneId)`
  (`app/static/02_sidebar.js:128`).
- **No existing JS controller binds to the folder partials.** The editor
  self-bootstraps via a tail `<script>` in its template on every swap; the
  folder templates have **no** tail script today. The bulk controller needs
  its own bind hook (mirror the editor's tail-script pattern, or a global
  `htmx:afterSwap` listener that looks for the toolbar).

## Proposed approach

**UI (both folder templates).** Add a checkbox `<td>`/`<th>` as the first
column of the `features` table. Wrap the table in a small toolbar:

- A header **select-all** checkbox toggling every row checkbox in the
  current (direct-children) list; reflects indeterminate state.
- Toolbar buttons **Move · Re-tag · Run · Delete**, disabled while the
  selection is empty, with a live "N selected" count.
- The checkbox cell calls `event.stopPropagation()` so it never triggers
  the row's `hx-get` navigation.

The toolbar renders **only when `features` is non-empty**. The select-all
checkbox reflects all / none / **indeterminate**. Selection state is
**per-render**: it is cleared on every `htmx:afterSwap` into `#main-pane`
(the swap replaces the DOM), and after a successful batch.

**Canonical selection key.** Each selected case is identified by its
**data-root-relative path** `<folder_path>/<file_name>` (e.g.
`Alpha/Mod/case.feature`). This single string is simultaneously: the
`hx-get="/ui/file/<key>"` suffix already on the row, the `/api/files/<key>`
path (Delete / Re-tag / Move), and the `file_path` value stored in a run
(Run). No path translation is needed between actions.

Factor the duplicated `features` table out of the two templates into a
shared `{% include %}` partial (e.g. `_folder_feature_table.html`) so the
toolbar + checkbox markup lives in **one** place and both depth-2 and
depth-3+ views stay in sync. The partial needs the folder path in scope;
`folder_module.html` exposes `module_path` and `folder_subfolder.html`
exposes `folder_path`, so pass a normalised `folder_path` into the include.
(Confidence: medium — verify no other template depends on the inline markup
before extracting.)

**Client (new JS module, e.g. `app/static/10_bulk_actions.js`).** A small
controller bound on `htmx:afterSwap` for the folder partials that:

- tracks the selected set of data-root-relative `.feature` paths;
- wires select-all / per-row toggles + button enable/disable;
- on each action opens a modal (reusing the helpers above), then runs an
  **all-or-nothing** flow (D3): a **pre-flight verification pass** over
  **all** selected cases, and only if every case passes does it perform the
  action as a **client-side fan-out of the existing single-item endpoints**
  (one request per selected case);
- if **any** case fails verification, it **aborts before any write** and
  shows the failed case(s) + reason(s);
- on completion refreshes the folder list + sidebar tree once.

Rationale for fan-out over new batch endpoints: every action already has a
robust, validated single-item endpoint; a batch endpoint would duplicate
that validation. The all-or-nothing gate (D3) is enforced client-side by
verifying every case up-front, so the fan-out only runs once the batch is
known-good. Revisit only if fan-out proves too chatty for realistic folder
sizes.

**Per action:**

- **Move** — factor out the editor's folder picker (`08_file_editor.js:778`,
  sourced from `GET /api/tree`) and **filter it to the source project only**
  (D4); fan-out `PATCH /api/files/<path>/move` per case. Pre-flight rejects
  same-parent + name conflicts (D3). Refresh source + dest folder + tree.
- **Re-tag** — collect a tag set from the user (chip input). Tags are
  normalised the way the editor stores them: strip a leading `@`,
  de-dup order-preserving, reject any tag failing the grammar. An **empty**
  set is allowed and means *clear all feature-level tags* (consistent with
  "clear current tags"). For each selected case read the feature
  (`GET /api/files/<path>`), overwrite **`feature.tags`** with the new set
  (leaving `scenario.tags` untouched — D1), then `PATCH` the whole feature
  back. The round-trip preserves everything else (`background`, `scenario`,
  `enums`, data tables) since `to_dict`/`from_dict` are symmetric
  (`app/models/_feature.py:181-199`).
- **Run** — pick a **single** target run from the **source project's**
  existing runs (`GET /api/runs/<project>`); `tmsBuildRunPicker` is
  multi-select so either constrain it to one selection or use a plain
  `<select>`. Fan-out `POST /api/runs/<project>/<group>/<file_name>/cases`
  per case; pre-flight de-dups against the run's current cases (D3;
  `add_run_case` raises 409 on duplicate). If the project has no runs, show
  an empty-state prompt (D2 — no inline creation).
- **Delete** — confirmation modal listing the N names; fan-out
  `DELETE /api/files/<path>` per case (idempotent). Refresh list + tree.

## Decisions (D1–D4 all resolved Jun 11, 2026)

- **D1 — Re-tag tag level + clear semantics. RESOLVED Jun 11, 2026:
  feature-level only, keep scenario.** Bulk Re-tag overwrites
  `feature.tags` with the user-supplied tag set and leaves
  `feature.scenario.tags` **untouched**. Scenario-level tags still surface
  in the listing/search union (D10). Re-tag is therefore a read-modify-write
  that only replaces the feature-level tag list per selected case.
- **D2 — Run picker target. RESOLVED Jun 11, 2026: existing runs only.**
  Bulk Run adds the selected cases to an **existing** run; creating a run
  inline is **out of scope**. If the (source) project has no runs, the Run
  modal shows an empty-state prompt directing the user to create a run first
  (it does not offer inline creation).
- **D3 — Fan-out vs batch endpoints + failure model. RESOLVED Jun 11, 2026:
  client fan-out over the existing single-item endpoints (no new HTTP
  surface) under an all-or-nothing rule.** Concretely:
  - **All-or-nothing.** The controller first runs a **pre-flight
    verification pass** over **every** selected case. If **at least one**
    case fails verification, it **shows the failed case(s) + reason(s) and
    does not proceed** — **no writes happen**. Only when **all** cases pass
    does it perform the action.
  - **Pre-flight verification (read-only, no writes).** The check uses state
    fetched once before the batch, then evaluated for every selected case:
    - **Move** — destination parent exists and is depth 2..MAX; no name
      conflict at the destination (`GET /api/folders/<dest>/contents` once →
      check each selected leaf against `features[].file_name`); not the same
      parent as the source.
    - **Run** — the chosen run exists and is read once
      (`GET /api/runs/<project>/<group>/<file_name>`); no selected case's
      key is already in `results[].file_path` (de-dup).
    - **Re-tag** — the user-supplied tag set is well-formed (each tag
      single-line, non-empty, matches the tag grammar).
    - **Delete** — always verifiable (idempotent); the gate is the
      confirmation modal, not a precondition.
  - **Then fan-out: one request per selected case** against the existing
    endpoints (Move `PATCH .../move`, Delete `DELETE`, Re-tag `GET`+`PATCH`,
    Run `POST .../cases`), dispatched **sequentially** in selection order to
    keep write locks uncontended.
  - **Residual risk (TOCTOU).** Because verification is client-side and the
    writes are N separate requests, a case could still fail mid-fan-out
    after passing pre-flight (e.g. a concurrent edit between check and
    write). For a single-user dev tool this is acceptable; if such a
    mid-batch write fails, stop and surface which case failed (the
    already-applied writes are not rolled back). Pre-flight makes this the
    rare exception, not the common path.
  - **One refresh at the end.** The folder list + sidebar tree refresh
    **once** after the batch completes, then the selection is cleared.
  - **Progress + disabled state.** The toolbar buttons disable and show an
    in-flight indicator while a batch runs; re-enable on completion.
  - **Feedback surface.** Pre-flight failures and any TOCTOU fan-out failure
    render **inside the open action modal** (a `[data-role=error]` region,
    listing each failed case + reason); the modal stays open so the user can
    adjust and retry. Success closes the modal, then triggers the single
    end-of-batch refresh.
- **D4 — Cross-project Move/Run. RESOLVED Jun 11, 2026: same project
  only.** Bulk **Move** may only target folders **within the source
  project**; the Move picker is scoped to the current project (no project
  select). Bulk **Run** likewise targets only the **source project's** runs
  (runs are per-project: `<project>/test-run/<group>/...`). This is narrower
  than the single-case Move modal, which allows cross-project moves.

## Assumptions & risks

- **A1** — The checkbox-in-clickable-row interaction is the main UX risk;
  `stopPropagation` on the checkbox cell is required and must be smoke-tested.
- **A2** — Extracting the shared feature-table partial must not change the
  rendered markup that feature-07 smokes (FT1/FT2/FT3, `F07_04a/b/c`) assert
  on; keep classes/structure identical aside from the new first column.
- **A3** — Re-tag read-modify-write races with concurrent edits; per-file
  storage locks mitigate, but a stale-read overwrite is possible. Acceptable
  for v1 (single-user dev tool); note for future.
- **A4** — Failures are caught up-front by the pre-flight verification pass
  (all-or-nothing, D3): name conflict on Move, already-in-run on Run, and
  malformed tags on Re-tag all block the batch before any write. The only
  residual partial-failure path is a TOCTOU race during fan-out (see D3),
  which is acceptable for v1.

## Self-investigation — confidence & unresolved assumptions (Jun 11, 2026)

Grounded against the live code. **Overall confidence: HIGH** (re-evaluated
Jun 11, 2026 after the detail refinement — up from medium-high). Every
contract the plan depends on is now verified against code: the four action
endpoints, the three pre-flight listing endpoints
(`/api/folders/<p>/contents`, `/api/tree`, `/api/runs/...`), the unified
selection key, and the lossless Re-tag round-trip. The remaining unknowns
are narrow UI-plumbing items, each retired early in the DO sequence — none
are contract gaps.

**Verified (high confidence):**

- Listing already returns **direct children only** (`features` vs `folders`)
  — the "one level" scope is free.
- All four single-item endpoints exist and behave as the plan assumes
  (Move/Delete/Re-tag/Run; refs above).
- `add_run_case` raises **409 on duplicate** (`_runs.py:359`) → pre-flight
  de-dup is real, not guessed.
- Tag grammar `_is_valid_tag` is **client-replicable** (ASCII printable, no
  ws/`@`/`,`) → Re-tag pre-flight is sound.
- Refresh helpers `tmsRefreshFolder` / `tmsRefreshTreePane` exist.
- feature-07 smokes pin `hx-get` **on the `<tr>`**, so the additive checkbox
  column + `stopPropagation` approach (A1/A2) is the only viable shape.

**Corrected during investigation (were wrong/optimistic in the first draft):**

- The Move picker is **not** a standalone `tmsEditor.move()` helper; it is
  editor-internal (`08_file_editor.js:778`), `<select>`-based, sourced from
  `GET /api/tree` across **all projects**. Reuse = factor out + project
  filter.
- `tmsBuildRunPicker` is **multi-select**, not single — bulk-Run must
  constrain or use a `<select>`.
- The tag chip input is **editor-coupled**, not reusable as-is.
- Smokes belong in **`tech-03/`**, not `feature-14/`.

**Assumptions that cannot be fully resolved until the Do phase (residual):**

- **U1 (low-medium, down from medium).** Extracting the shared
  `_folder_feature_table.html` partial preserves byte-compatible markup for
  the feature-07 selectors. Now de-risked by ordering: DO step **3a**
  extracts the table **verbatim** and re-runs F07 **before** any new markup
  is added (step 3b). The only way it breaks is a copy error caught
  immediately by F07.
- **U2 (medium-high, up from medium).** The checkbox-in-row
  `stopPropagation` reliably suppresses the `<tr>`'s HTMX `hx-get`. Raised
  on **in-repo precedent**: `tree.html:27-30`,
  `reports_sidebar.html:26`, and `test_run_sidebar.html:32` already use
  `onclick="event.stopPropagation(); ..."` on a descendant control to keep a
  clickable row's nav intact — the identical event-bubbling technique. The
  one residual: those rows use a manual click listener while our row uses
  htmx's own listener (both bubbling-based, so the technique transfers).
  *Confirm with the step-4 no-navigate smoke;* fallback = dedicated
  cell/link, but that would change the F07 `<tr>` contract — avoid.
- **U3 (medium-low).** The bind mechanism for the new controller — tail
  `<script>` per folder partial vs a single global `htmx:afterSwap` listener
  — interacts cleanly with existing main-pane swaps without double-binding.
  *Resolvable only while wiring step 4.*
- **U4 (low).** Realistic folder sizes keep sequential fan-out (N requests)
  acceptably fast. *Unknowable without usage data;* revisit only if slow.
- **U5 (low, accepted).** TOCTOU between pre-flight and fan-out (D3) — cannot
  be eliminated client-side without a batch/transaction endpoint, which is
  out of scope. Accepted for a single-user v1.

## Verification (as-built)

- Smokes live in **`.smoke-scratch/tech-03/`**: `T03_02` (toolbar at depth
  2 + 3), `T03_03` (per-row checkbox + double `stopPropagation` + canonical
  key, `<tr>` hx-get intact), `T03_04` (scope = direct-children only),
  `T03_05` (toolbar only when features exist), `T03_06` (controller static
  inspection: four actions + pre-flight endpoints + idempotent `htmx:load`
  bind + D1 feature-level tags).
- feature-07 smokes (`F07_04a/b/c`, `F07_05`, `F07_08a/b/c`) stayed green
  after both the verbatim extraction (3a) and the checkbox/toolbar add (3b)
  — they pin `hx-get` on the `<tr>` plus the filename/`title=`/`truncate`/
  chip-span selectors, all left intact (confirmed A1+A2).
- Full smoke suite: **272/272 PASS / 0 FAIL**. The client fan-out
  interaction is browser-level and verified by static inspection (`T03_06`)
  per the standing Phase-2 lock-in.

## As-built notes (deviations from the plan)

- **Controller filename** is `app/static/08_bulk_actions.js` (not the
  planned `10_*`): the `T01_01` script-order smoke requires
  `09_bootstrap.js` to remain the last app script and the sorted glob to
  equal the load order, so a `10_` file is impossible. `08_` sorts before
  `08_enums_manager.js` and keeps bootstrap last.
- **Bind event** is `htmx:load` (not `htmx:afterSwap`): the feature-06/08/10
  wiring smokes extract "the" single body-level `htmx:afterSwap` listener
  from the concatenated static JS, so a second one breaks them. `htmx:load`
  fires on swapped-in content (covers folder nav + `tmsRefreshFolder`) and
  the `data-bulk-bound` guard keeps it idempotent (this resolves U3).
- All decisions D1–D4 were confirmed with the user during the Plan phase;
  U1/U2 were retired by the 3a→3b ordering + the `T03_03` no-navigate smoke.
