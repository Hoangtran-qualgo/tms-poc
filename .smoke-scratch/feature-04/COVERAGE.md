# feature-04 · Folder CRUD — coverage matrix

Step 1 audit of the smoke tests against
`specs/features/04-feature-folder-crud-NEW.md`.

## Method

- Spec source: `specs/features/04-feature-folder-crud-NEW.md`.
- Rule heuristic (locked Jun 8, 2026): every imperative
  statement in the spec + every bullet under
  `## Acceptance criteria`.
- Spec sub-headings under `## Invariants & rules` are
  treated as **sections** for the one-smoke-per-section
  rule (Decision A) so each subdivision (Depth, Name
  uniqueness, Name validation, Idempotence, UI gaps) gets
  its own file.
- `Status` values: `covered`, `partial` (incidental coverage
  inside a primary-other-feature smoke), `missing`, `n/a`
  (rule is documentation-only / not testable).
- `Smoke file` column carries the target file for every row.
  Per Decision A, feature-04 uses **one smoke per spec
  section** — eight files total
  (`F04_01_http_routes.py` … `F04_08_acceptance.py`).
  All eight exist as of Step 4 (Jun 8, 2026).
- **Primary-frame distinction.** Feature-04 is the
  HTTP-route + UI-wiring layer; feature-02 already owns the
  storage-half of the path-discipline, depth, name-validation,
  and name-uniqueness rules. The smokes below assert the
  *route layer's* delegation and the *response envelope*
  (status code, JSON body, error-code string), not the
  underlying storage behaviour.

## Matrix

| # | Rule | Spec § | Smoke file | Status |
|---|---|---|---|---|
| HR1 | `POST /api/folders` accepts body `{name, parent?}`, defaults `parent` to `""` (root), creates `parent + [name]`, returns `{ok: true}` with HTTP 201. | Public surface → HTTP routes | `F04_01_http_routes.py` | covered |
| HR2 | `PATCH /api/folders/<path:p>` accepts body `{name}`, renames `p` to `<parent of p>/<name>` within the same parent, returns `{ok: true}` with HTTP 200. | Public surface → HTTP routes | `F04_01_http_routes.py` | covered |
| HR3 | `DELETE /api/folders/<path:p>` recursively deletes `p`, returns body `""` with HTTP 204 (idempotent: missing target = 204). | Public surface → HTTP routes | `F04_01_http_routes.py` | covered |
| UI1 | `tmsCreateProject()` in `app/static/app.js` uses `window.prompt`, posts to `/api/folders` with `parent: ""`, then calls `tmsRefreshFolder("")`. | Public surface → UI triggers | `F04_02_ui_triggers.py` | covered |
| UI2 | `tmsCreateModule(project)` in `app/static/app.js` uses `window.prompt`, posts with `parent: project`, then calls `tmsRefreshFolder(project)`. | Public surface → UI triggers | `F04_02_ui_triggers.py` | covered |
| UI3 | `tmsCreateSubfolder(parent)` in `app/static/app.js` uses `window.prompt` (spec says `tmsOpenModal` — known spec gap surfaced under Notes & flags), posts with the given `parent`, then calls `tmsRefreshFolder(parent)`. | Public surface → UI triggers | `F04_02_ui_triggers.py` | covered |
| DR1 | `POST /api/folders` accepts `1 <= len(segments) <= MAX_FOLDER_DEPTH` (10). Depth 1 = project; depth 2 = module; depth 3..10 = sub-folder. (Route-layer assertion; storage-half tested in feature-02 DR1.) | Invariants → Depth | `F02_02_depth_rules.py` (storage half) + `F04_03_depth.py` (route half) | covered |
| DR2 | `PATCH /api/folders/<p>` and `DELETE /api/folders/<p>` accept any depth `>= 1` (no upper bound enforced; the storage methods are depth-permissive). | Invariants → Depth | `F04_03_depth.py` | covered |
| NU1 | Name conflicts (duplicate folder name in the same parent) raise `NameConflictError` → HTTP 409 with `code: name_conflict`. (Route-layer assertion; storage-half in feature-02 NU4.) | Invariants → Name uniqueness | `F02_04_name_uniqueness.py` (storage half) + `F04_04_name_uniqueness.py` (route half) | covered |
| NU2 | A folder and a `.feature` file may coexist at the same logical name because the file leaf always includes the `.feature` extension; their resolved paths differ on any host filesystem. | Invariants → Name uniqueness | `F04_04_name_uniqueness.py` | covered |
| NV1 | Every segment passes `_validate_segment` at the route layer: no `/ \ : * ? " < > \|` or control characters; empty / `.` / `..` rejected. Failure → HTTP 400 with `code: bad_request`. (Route-layer assertion; storage-half in feature-02 PD2.) | Invariants → Name validation | `F02_01_path_discipline.py` (storage half) + `F04_05_name_validation.py` (route half) | covered |
| ID1 | `DELETE /api/folders/<p>` returns 204 even if `p` was already missing (storage's `delete_folder` no-ops on missing target). | Invariants → Idempotence | `F04_06_idempotence.py` | covered |
| UG1 | v1 has no UI button for folder rename or delete; the surfaces are API-only. Testable as the absence of rename/delete-folder buttons in the rendered folder views and as the absence of `tmsRenameFolder` / `tmsDeleteFolder` symbols in `app/static/app.js`. | Invariants → UI gaps | `F04_07_ui_gaps.py` | covered |
| AC1 | Creating a folder with a forbidden character returns HTTP 400 with `code: bad_request`. (Strengthens NV1.) | Acceptance criteria | `F04_08_acceptance.py` | covered |
| AC2 | Creating a folder at depth 11 (or higher) returns HTTP 400 with `code: bad_request`. (Strengthens DR1 boundary.) | Acceptance criteria | `F04_08_acceptance.py` | covered |
| AC3 | Creating a duplicate folder in the same parent returns HTTP 409 with `code: name_conflict`. (Strengthens NU1.) | Acceptance criteria | `F04_08_acceptance.py` | covered |
| AC4 | Deleting a folder removes every descendant file and folder (`shutil.rmtree`). (Strengthens HR3 with the recursion claim.) | Acceptance criteria | `F04_08_acceptance.py` | covered |
| AC5 | Deleting a non-existent folder returns HTTP 204 (idempotent). (Strengthens ID1.) | Acceptance criteria | `F04_08_acceptance.py` | covered |
| AC6a | Each successful folder mutation through the API (`POST` / `PATCH` / `DELETE /api/folders`) generates **zero** SSE `"change"` events on the bus, because storage's `_mark_write` plus the watcher's `was_recently_written` suppresses the writing tab's self-event. (Split from spec AC6 — see Step-1 sign-off note 1.) | Acceptance criteria | `F02_08_acceptance.py` AC5 (storage half) + `F03_06_acceptance.py` AC1 (watcher half via storage methods) + `F04_08_acceptance.py` (API-route half) | covered |
| AC6b | An **external** folder mutation (one that bypasses `Storage`, e.g. `os.makedirs` directly inside the data root) generates **exactly one** SSE `"change"` event per open tab, no sooner than `DEBOUNCE_SECONDS` after the last write in the burst. (Split from spec AC6 — see Step-1 sign-off note 1; preserves the spec's detection-intent half.) | Acceptance criteria | `F03_06_acceptance.py` AC2 (watcher half) + `F04_08_acceptance.py` (folder-mutation specialisation) | covered |

## Summary

- Total rules: **20** (3 HTTP routes, 3 UI triggers, 2 depth, 2 name uniqueness, 1 name validation, 1 idempotence, 1 UI gaps, 7 acceptance).
- `covered`: **20**.
- `partial`: **0**.
- `missing`: **0**.
- `n/a`: **0**.

**Feature-04 is done** per the locked Definition-of-Done
(`COVERAGE.md` has zero `missing` rows; `run.py --filter 04`
exits zero with all eight smokes green). The five
previously `partial` rows (DR1, NU1, NV1, AC6a, AC6b) are
now covered by feature-04's own route-layer smokes; the
feature-02 / feature-03 files stay in their primary
frames and continue to provide the storage / watcher
half of those rules.

## Notes & flags

- **Zero direct API-route coverage.** A `grep` for
  `"/api/folders"` across `.smoke-scratch/` returns no
  matches; every existing folder-related smoke calls
  `Storage.create_folder` / `rename_folder` / `delete_folder`
  directly. Step 2 will be a no-op `git mv` (zero files
  to move). Same shape as feature-02 / feature-03.
- **Storage / watcher partial-coverage rows.** DR1 / NU1 /
  NV1 / AC6 are marked `partial` because feature-02 and
  feature-03 own the *storage / watcher half* of the
  contract. The feature-04 smokes will test the *route
  half*: `app.test_client().post("/api/folders", json=…)`
  with assertions on `response.status_code`,
  `response.get_json()["error"]["code"]`, and
  `response.headers`. Both halves stay in their primary
  frames; partial → covered once the route half exists.
- **AC6 split (per Step-1 sign-off).** Spec text bundles
  two distinct claims into one bullet: "exactly one SSE
  change event reaching open tabs" AND "no self-event
  from the writing tab". These contradict for API
  mutations (suppression makes it zero events, not one).
  The audit splits AC6 into **AC6a** (API mutation →
  zero events, matching actual code) and **AC6b**
  (external mutation → exactly one event after
  `DEBOUNCE_SECONDS`, matching the spec's detection
  intent). Both halves are testable today.
- **UI trigger testing approach (approved).** UI1 / UI2 /
  UI3 are Javascript functions in `app/static/app.js`.
  Smokes assert presence + correct `parent` argument +
  `/api/folders` POST URL + `tmsRefreshFolder(<arg>)`
  follow-up call via **regex matching of the static JS
  source text**. Not a Javascript runtime test.
- **UG1 testable shape (approved — "test all testable
  scenarios").** Two-pronged negative-invariant test:
  (a) render `/ui/folder/...` for each depth (root /
  project / module / sub-folder) via Flask test client
  and assert the response HTML does NOT contain
  "Rename folder" / "Delete folder" button labels or
  `onclick` handlers, AND
  (b) assert `app/static/app.js` does NOT define
  `tmsRenameFolder` / `tmsDeleteFolder` symbols.
- **NU2 testable shape.** Create a folder named "X" at
  depth 2, then create a file named "X.feature" in the
  same parent module; assert both coexist (no conflict).
  This is the spec's "always differ via `.feature` ext"
  claim made concrete.
- **MAX_FOLDER_DEPTH = 10** is the same constant referenced
  by feature-02 DR1. The feature-04 DR1 / AC2 smokes
  exercise it via the HTTP boundary (depth 11 → 400),
  not via direct call.
- **Spec gaps discovered during Step-1 read-through.**
  - HR2's spec entry says rename returns `{ok: true}` but
    omits the HTTP status. The code returns 200 (default
    Flask). Will assert 200 in the smoke; flag for spec
    patch.
  - The spec doesn't specify error body shape on 400 /
    409 (it just says "returns 400" / "returns 409").
    The code returns `{error: {code, message, details}}`
    per the server-level error handler convention. Will
    assert `error.code` matches the documented code
    string (`bad_request`, `name_conflict`).
  - `POST /api/folders` with a malformed JSON body raises
    `ValueError` → 400, not in spec. Will not test (out
    of scope per "audit tests the spec as written").
  - AC6 conflates two distinct behaviours (suppression of
    self-writes + detection of external writes). The
    split rationale is recorded under Notes & flags.
  - **UI3 spec/code drift (discovered Step 4).** Spec
    says `tmsCreateSubfolder(parent)` is
    "`tmsOpenModal`-based" but the as-shipped code in
    `app/static/app.js:404-417` uses `window.prompt`
    just like `tmsCreateProject` and `tmsCreateModule`.
    Test follows code (same shape as the AC6 split).
    Either patch the spec to read "prompt-based" or
    add a `tmsOpenModal` flow to the function; the
    `F04_02_ui_triggers.py` assertion message names
    this as a known spec gap.

## Step 4 execution log

**Jun 8, 2026** — Step 4 (Gap-fill) executed for feature-04:

- Eight smoke files written, one per spec section,
  ~50–220 lines each:
  - `F04_01_http_routes.py` covers HR1–HR3 (3 rules).
  - `F04_02_ui_triggers.py` covers UI1–UI3 (3 rules).
  - `F04_03_depth.py` covers DR1–DR2 (2 rules).
  - `F04_04_name_uniqueness.py` covers NU1–NU2 (2 rules).
  - `F04_05_name_validation.py` covers NV1 (1 rule).
  - `F04_06_idempotence.py` covers ID1 (1 rule).
  - `F04_07_ui_gaps.py` covers UG1 (1 rule, two-pronged).
  - `F04_08_acceptance.py` covers AC1–AC6 (7 rules,
    AC6 split into AC6a + AC6b).
- Each file carries the `# Pattern: see .smoke-scratch/README.md`
  pointer comment per the locked boilerplate-reminder rule.
- Verification: `./.venv/bin/python .smoke-scratch/run.py
  --filter 04 --verbose` reports `8/8 passed; 0 failed`
  and all 20 rule-level `PASS  <id>: …` lines fire.
- Full-suite re-run (`run.py` without filter) reports
  `27/27 passed; 0 failed`, confirming no regression in
  features 01 / 02 / 03.
- **Per-rule notes:**
  - **HR1–HR3** drive the routes via `app.test_client()`
    against an isolated `tempfile.TemporaryDirectory`
    data root. HR1 covers both `parent` omitted and
    `parent=''` explicit (defaults to root); HR2 covers
    depth-1 (project) and depth-2 (module) renames
    with subtree-follows verification; HR3 covers
    descendant teardown plus the idempotence wire shape.
  - **UI1–UI3** are pure static-text checks against
    `app/static/app.js`. A helper `_extract_function_body`
    uses brace-depth counting to isolate each `async
    function` body, then `re.search` confirms the
    documented call shape (prompt source, POST URL +
    body, follow-up `tmsRefreshFolder` argument).
    UI3's assertion message names the spec gap.
  - **DR1** walks depth 1 … 10 successfully (each
    POST building on the previous parent), then
    asserts depth-11 → 400 `bad_request`. **DR2**
    avoids case-only renames on macOS HFS+/APFS
    (which collapse `d1` ↔ `D1` to one path → 409)
    by using distinct tokens (`d1` → `proj`,
    `d5` → `leaf`, etc.).
  - **NU1** asserts the 409 envelope (`error.code`,
    `error.details.path`), tests duplicates at depth
    1 and depth 2, tests PATCH-rename into a taken
    slot, and confirms parent-scoped uniqueness
    (same-name folders under different parents
    coexist).
  - **NU2** creates `Alpha/Mod/X.feature` then
    `Alpha/Mod/X` (folder) and vice-versa to prove
    the coexistence claim is order-independent.
  - **NV1** loops the full forbidden-char set
    (`/ \ : * ? " < > |`), control chars (NUL, BEL,
    `\n`, `\t`, ord 31), `.` / `..`, plus a forbidden
    char in a PARENT segment. Closes with a sanity
    "clean name accepted" assertion to prove the
    validator isn't a global reject.
  - **ID1** covers four idempotence shapes:
    never-existed depth-1 path, never-existed deep
    path (parent chain also missing), existed-then-
    deleted (double-DELETE), and existing-vs-missing
    siblings under the same parent (same wire shape).
  - **UG1** is two-pronged: (a) renders
    `/ui/folder/...` at root / project / module /
    sub-folder via the test client and asserts no
    "rename folder" / "delete folder" label and no
    `hx-patch` / `hx-delete` wired to `/api/folders/`;
    (b) static-greps `app/static/app.js` for the
    declaration forms of `tmsRenameFolder` /
    `tmsDeleteFolder` and asserts both are absent.
    The (b) prong includes a positive sanity check
    (`tmsCreateProject` etc. ARE present) to guard
    against a false-negative when the JS file is
    truncated or the path drifts.
  - **AC1–AC5** are tight HTTP envelope assertions
    that strengthen NV1 / DR1 / NU1 / HR3 / ID1.
  - **AC6a** subscribes to the bus AFTER seeding
    (so seeding events don't pollute the count),
    drains any in-flight events with a generous
    settle wait, then drives `POST` + `PATCH` +
    `DELETE /api/folders` and asserts the
    subscriber queue stays empty for `max(
    DEBOUNCE_SECONDS * 3, 0.5)` seconds.
  - **AC6b** uses **two** subscribers (simulating
    two open browser tabs) and an external
    `os.makedirs` burst that bypasses `Storage`
    entirely. Asserts each subscriber receives
    exactly one `"change"` message, no extras
    arrive in the next debounce window (burst
    collapse), and `t_msg - t_last_write >=
    DEBOUNCE_SECONDS * 0.9` (10 % slack approved
    in feature-03 Step-1 sign-off, reused here).

**Feature-04 cycle complete.** Per the locked plan,
**feature-05 is next** — audit
`specs/features/05-*-NEW.md` (will need to discover the
exact filename in Step 1).

## Step 1 sign-off log

**Jun 8, 2026** — Step 1 (Audit) sign-off for feature-04:

1. **AC6 split.** Decision **(c)** — split AC6 into
   AC6a (API mutation → zero events, follows code) and
   AC6b (external mutation → exactly one event after
   `DEBOUNCE_SECONDS`, follows spec intent). Both rows
   are now in the matrix; total rule count 19 → 20.
2. **UI trigger smoke approach.** Approved — static
   regex matching of `app/static/app.js`, no JS runtime.
3. **UG1 worth a smoke.** "Test all testable scenarios"
   — keep UG1 as testable (not `n/a`) and use the
   two-pronged negative-invariant approach above.
   F04_07_ui_gaps.py exists; file count stays at 8.
4. **Restate-from-feature-02 pattern.** Approved. Each
   restated row's "Smoke file" column carries both
   files (route + storage) post-Step-4. Feature-02
   smokes stay in their primary frame untouched.

Step 2 (Restructure) and Step 3 (Refine) will be no-ops
— zero existing primary-frame smokes for feature-04.
Proceed directly to Step 4 (Gap-fill) with the eight
files `F04_01_http_routes.py` … `F04_08_acceptance.py`.
