# 13 · Per-project `enums.yaml` CRUD UI

_Forward-looking spec. Status: **Spec'd — all decisions resolved, ready
for Plan / Do** — filed Jun 11, 2026 from the `IN-PROGRESS.md` § Could-have
item "Investigate: per-project `enums.yaml` CRUD UI", itself deferred from
`11-feature-testcase-component-NEW.md` v1 (which pre-named
`write_project_enums` as "deferred to the CRUD-UI follow-up").
Investigation grounded against the live code Jun 11, 2026 — each section
carries current-state findings (file:line refs), a proposed approach, and a
**confidence** level._

_**Sign-off log (Jun 11, 2026 — COMPLETE):** D3 **approved** — never
silently remove an in-use key/kind. D5 **approved** with a refinement — the
management surface is reached via a **new sidebar tab** (not a folder-view
modal). D11 **approved — block** (consistent with D3): Clear resets the
file only when nothing references the vocab; otherwise it returns a
detailed `409` naming the in-use enum + referencing case(s) and tells the
user to clear that enum in the test case first (the editor already supports
that via the picker "— not set —" option and the orphan Clear button —
verified, no new work). D2 **approved** — `PUT /api/enums/<project>`,
`POST …/rename`, `POST …/clear`. Already-shipped: auto-init-on-create
(D9), per-project uniqueness (D12). New work: backfill script (D10), the
sidebar tab (D5). **All decisions resolved — Plan / Do may proceed.**_

## Problem statement

Today a project's enum vocabulary (`<project>/enums.yaml`) is **read-only
through the app**: the only mutation is `init_project_enums` (the
`Initialize enums file` button), and every subsequent change — add a kind,
add/rename/remove an entry, fix a label — requires hand-editing the YAML on
disk (`11-feature-testcase-component-NEW.md:227`, `:276-279`). That is fine
at small scale but becomes a friction / correctness hazard once teams
actively curate vocabularies:

- **No guard rails** — a hand-edit can introduce a malformed file; the next
  test-case save then 422s with `enums_parse_error` for an unrelated reason.
- **Rename is dangerous** — renaming a key in the YAML silently orphans
  every `.feature` that still carries the old key (`# enum.<kind>: <old>`),
  and there is no tool to cascade the rename across files.
- **Stale pickers** — an external edit to `enums.yaml` is not reflected in
  an open editor session until a full reload (the client session-caches the
  vocab and deliberately skips SSE — `08_file_editor.js:906-907`,
  `11-…:608-623`).

This spec designs a project-scoped CRUD surface over `enums.yaml` plus the
SSE-driven cache refresh that lands with it.

## Out of scope (for this spec)

- Any change to the **`Feature.enums` data shape**, the on-disk
  `# enum.<kind>: <key>` directive, or the test-case editor picker behaviour
  — all owned by spec 11 and reused verbatim.
- Tag governance / tag CRUD — tags remain free-form (spec 11 § Out of scope).
- Multi-project / global enum vocabularies — `enums.yaml` is per-project by
  construction (`_core.py:75-85`) and stays that way.
- Reordering kinds / entries as a first-class feature (a nice-to-have;
  noted under § Surface for follow-up, not built here).

## Current state (grounded Jun 11, 2026)

- **Read / parse / validate** — `Storage.read_project_enums(project)` is
  mtime-cached and returns `{kind: {key: label}}` with insertion order
  preserved; `_parse_project_enums` enforces the schema rules (a)–(d)
  (single-key mappings, identifier regex, non-empty single-line labels,
  unique keys) (`app/storage/_enums.py:23-58`, `:100-226`). Malformed YAML
  → `EnumsParseError` → HTTP 422 (`app/errors.py:106-126`).
- **Init only, no write-back** — `init_project_enums` writes the default
  `components:\n` bytes, `_mark_write`s, invalidates the cache, and returns
  the parsed dict (`_enums.py:60-94`). There is **no** `write_project_enums`
  — spec 11 deferred it here on purpose (`11-…:262-266`, `:533-535`).
- **HTTP** — `GET /api/enums/<project>` and `POST /api/enums/<project>`
  (init) only (`app/server/routes_enums.py:15-35`).
- **Cross-check on save** — `_cross_check_enums` rejects a test-case save
  whose non-empty `enums` entries don't resolve in the project vocab
  (`_enums.py:228-270`); the editor surfaces unresolved pairs as orphan
  badges (`08_file_editor.js:1062-1101`).
- **Cascade primitives** — the directive is `# enum.<kind>: <key>`
  (`gherkin_io.py:54-56`, serialized at `:374-382`), features round-trip
  through `Feature.enums`, and `Storage.iter_feature_paths(scope)` yields
  every `.feature` under a project (`app/storage/_search.py:138-157`).
- **Watcher / SSE** — `EventBus.publish("change")` fans a coarse (path-less)
  `"change"` to every subscriber (`app/watcher.py:42-102`); **self-write
  suppression** (`_mark_write` + `was_recently_written`,
  `_core.py:235-265`) means in-app writes emit **no** SSE — the same
  constraint we hit for E5 tree-refresh (tech-02).
- **Editor vocab cache** — `tmsEditor._vocabCache[project]` is a
  session-scoped Promise cache; `_loadEnums` populates it and `renderEnums`
  draws one picker per kind (`08_file_editor.js:909-993`). After
  `init_project_enums` the client updates the cache from the response so the
  picker appears without reload (`11-…:616-619`).

## Decisions (proposed)

- **D1 — Storage gains `write_project_enums(project, data)`.** Serialize
  `{kind: {key: label}}` back to canonical YAML (kind order = insertion
  order of `data`, so the UI controls ordering; a kind with no entries
  emits `<kind>:` like the default seed). Round-trip through
  `_parse_project_enums` **before** writing so a bad payload 422s instead of
  persisting; then `_atomic_write_bytes` + `_mark_write` +
  `_invalidate_enums_cache` (mirrors `init_project_enums`).
  **Confidence: HIGH** — symmetric with the existing init path; spec 11
  already reserved the method name.
- **D2 — API shapes: whole-document replace + explicit rename + clear.**
  **RESOLVED (approved Jun 11).**
  - `PUT /api/enums/<project>` accepts the **full** edited vocab and
    replaces the file (covers add/remove kind, add/remove entry, edit
    label). Whole-document is simplest and matches how the client already
    loads the entire vocab.
  - `POST /api/enums/<project>/rename` `{kind, old_key, new_key}` is a
    **dedicated** op because a blind document replace cannot distinguish a
    *rename* (old→new, needs file cascade) from a *remove old + add new*
    (data loss). Rename must be explicit so the cascade is intentional.
  - `POST /api/enums/<project>/clear` resets the file to the seed (D11).
  **Confidence: HIGH** — paths confirmed.
- **D3 — Removal of an in-use key/kind is blocked, not silent.**
  **RESOLVED (approved Jun 11).** When a `PUT` would drop a key (or whole
  kind) that ≥1 `.feature` still references, reject with `409` carrying the
  **usage count + a sample of paths**, so no save silently orphans cases.
  The user must reassign/clear those cases (or rename) first. This governs
  **incidental** removals through the document edit / rename path. The
  **Clear (fresh start)** action (D11) follows the *same* block rule — it is
  not a destructive bypass. **Confidence: HIGH**.
- **D4 — Rename cascade is alias-first, then drop (crash-safe ordering).**
  Under a **project-scoped lock**: (1) **dry-run** — enumerate affected
  features via `iter_feature_paths(project)`, parse each (abort the whole op
  if any fails to parse, surfacing the offending path); (2) write
  `enums.yaml` with **both** `old_key` and `new_key` present (alias) so no
  read ever sees an undefined key; (3) rewrite each affected feature
  (`enums[kind]: old→new`, re-serialize, atomic write); (4) write
  `enums.yaml` again **without** `old_key`. Each file write is individually
  atomic (`os.replace`); true multi-file transactionality is impossible on a
  plain FS, so the alias ordering guarantees that a crash at any point
  leaves a *valid* (never-orphaned) state. See A4.
  **Confidence: MEDIUM** — ordering is sound; the multi-write window is the
  residual risk (A4).
- **D5 — UI is a new "Enums" sidebar tab → per-project main-pane manager.**
  **RESOLVED (approved Jun 11, refined).** Add a **4th sidebar tab**
  ("Enums") alongside Directory / Test run / Reports
  (`base.html:79-133`, `02_sidebar.js:20-91`). The tab pane lists every
  **project** via `Storage.list_root()` (one `enums.yaml` per project, D12);
  clicking a project loads
  a management view into `#main-pane` via `GET /ui/enums/<project>` — the
  same sidebar-lists / main-pane-edits pattern Runs and Reports already use
  (consistency over a modal). The manager shows kinds → entries (key +
  editable label) with add/remove/rename affordances and the Clear (D11)
  action; legacy projects (no file) render the existing `Initialize enums
  file` state. The editor's `#feature-enums` header
  (`file_editor.html:115-128`) gains a secondary deep-link to the manager.
  _The earlier "modal launched from the folder view" is superseded by the
  tab; rationale unchanged (project-scoped, not file-scoped)._
  **Confidence: HIGH** — fits the existing tab shell exactly (S4 sizing).
  New: `tmsActivateEnumsPane` (lazy mount + `sse:change`), `enums_sidebar.html`
  partial, `GET /ui/enums-tree` (project list) + `GET /ui/enums/<project>`
  (manager view).
- **D6 — SSE refresh covers external edits only; in-app edits self-refresh.**
  The editing client updates `_vocabCache[project]` from the write response
  (optimistic, like init today). For **external** disk edits, the editor
  subscribes to `sse:change` → invalidate `_vocabCache` → re-`_loadEnums()`.
  In-app edits made in *another* tab will **not** auto-refresh that tab,
  because self-write suppression eats the SSE (same constraint as E5);
  documented, not worked around. See A5.
  **Confidence: HIGH** on the mechanism; the cross-tab gap is an accepted
  limitation.
- **D7 — Validation reuses the spec-11 rules verbatim.** Kind/key identifier
  regex `ENUM_IDENTIFIER_RE` (`models/_common.py:22-29`), non-empty
  single-line labels, unique keys per kind — all enforced server-side by
  routing the payload through `_parse_project_enums`. The client mirrors the
  regex for inline feedback but the server is authoritative.
  **Confidence: HIGH**.
- **D8 — `enums.yaml` is never deleted by this UI.** Removing the last kind
  leaves an empty (or `{}`-parsing) file; there is no "delete enums.yaml"
  action (legacy/no-file state is reached only by never initialising).
  **Confidence: HIGH**.
- **D9 — Auto-init on project create: ALREADY SHIPPED — no work.**
  `create_folder` depth-1 already writes the default `enums.yaml`
  (`components:\n`) beside every new project, inside the same lock region
  (`app/storage/_folders.py:58-66`; covered by spec-11 acceptance
  `11-…:672-676`). Request 3 is satisfied today; this spec only **reaffirms**
  it and adds a regression smoke. **Confidence: HIGH.**
- **D10 — One-time backfill for legacy projects via a CLI script.** A
  standalone, idempotent `scripts/backfill_enums.py` (run once by an
  operator) constructs a `Storage` over the data root, iterates depth-1
  project folders, and calls `init_project_enums(project)` for each that has
  no `enums.yaml` (skips those that already do; never overwrites). It is a
  thin wrapper over the existing init path — no new storage logic. Reuses
  `NameConflictError` as the "already present" skip signal. (The per-project
  `Initialize enums file` button stays as the in-app, one-at-a-time path;
  the script just does the whole repo at once.) **Confidence: HIGH.**
- **D11 — "Clear (fresh start)" resets the file; BLOCKS if in use.**
  **RESOLVED (approved Jun 11 — block, consistent with D3).** A dedicated
  `POST /api/enums/<project>/clear` resets `enums.yaml` to the **default
  seed** (`components:\n`, i.e. identical to a freshly-created project)
  rather than deleting the file (honours D8). To keep the rule **consistent
  with D3**, Clear does **not** cascade or silently orphan: if any kind/key
  in the file is still referenced by ≥1 `.feature`, the op is **blocked**
  with `409` and a detailed message naming the in-use enum(s) and the
  referencing case(s), e.g.
  _"enum `component: checkout` is in use by test case `proj/login.feature`
  (and 2 more) — please clear that enum in the test case first."_ Clear only
  succeeds when nothing references the vocabulary; the file is then reset to
  the seed in one atomic write under the project lock.
  - **User-side clear affordance — VERIFIED, no new work.** A case's enum is
    cleared in the editor either via the picker's **"— not set —"** option
    (`08_file_editor.js:1016-1020`, change handler `:1041-1049` sets
    `enums[kind]=""`) or the orphan-row **Clear** button (`:1087-1098`).
    Saving the case writes the now-empty directive, dropping the reference.
  **Confidence: HIGH** — same `count_enum_key_usage` guard as D3; no cascade
  primitive needed for Clear.
- **D12 — One `enums.yaml` per project: ALREADY GUARANTEED — no work.**
  The file is a single fixed-name artifact at the project root
  (`_ENUMS_FILE_NAME`, `app/storage/_core.py:75-85`); there is no mechanism
  to create a second. Request 5 needs no change. **Confidence: HIGH.**

## Assumptions & risk register

| # | Assumption / risk | Status / mitigation |
|---|---|---|
| A1 | Canonical re-serialization round-trips byte-stably for unchanged files (idempotent `read → write`). | **To verify in S1** with a round-trip smoke; the serializer must match the seed format (`components:\n`) for the empty-kind case. |
| A2 | A project's `.feature` count is small enough that a synchronous cascade + dry-run parse is acceptable (no async/job needed). | Holds for the current single-user / small-repo target; if profiling later shows large projects, batch/stream — out of scope now. |
| A3 | The `# enum.<kind>: <key>` directive is the **only** place a key is persisted in a feature (no other copy). | Confirmed (`gherkin_io.py` parse `:133-198` / serialize `:374-382`); cascade only needs to rewrite `Feature.enums`. |
| A4 | Multi-file cascade is **not** atomic across files. | Mitigated by D4's dry-run + alias ordering so any crash leaves a valid (never-orphaned) state; a partial cascade is *resumable* (re-running rename old→new is a no-op for already-migrated files). **Residual risk accepted.** |
| A5 | In-app enum writes won't SSE-refresh other tabs (self-write suppression). | Accepted limitation, mirrors E5; the editing tab self-refreshes, external edits propagate. Documented in D6. |
| A6 | Blocking removal of in-use keys (D3) won't overly frustrate users. | **Resolved** — block confirmed; the sanctioned destructive path is the explicit, confirmed Clear (D11). |
| A7 | `read_project_enums` cache invalidation on every write keeps the cross-check correct. | `write_project_enums` calls `_invalidate_enums_cache` (D1); the next cross-check re-reads. Same guarantee `init_project_enums` already relies on. |
| A8 | The Enums tab can list projects without a new storage method. | **Resolved** — `Storage.list_root()` already returns depth-0 folder names = projects (`_listing.py:22-30`); the tab reuses it verbatim. (Projects are depth-0 in `list_tree`, not depth-1.) No new traversal logic. |
| A9 | The backfill script (D10) runs **offline** (operator-invoked), not inside a request, so it needs its own `Storage` construction over the data root. | **Resolved** — `create_app` resolves the root as `data_root` or `./project` then does `Storage(root)` (`app/__init__.py:41-51`); the script does the same trivial `Storage(Path(...))`, iterates `list_root()`, and calls `init_project_enums`. No app/server needed. |
| A10 | Clear (D11) blocks on any in-use enum rather than cascading. | **Resolved** — Clear reuses the same `count_enum_key_usage` guard as D3; it needs **no** cascade primitive. The user unsets enums per-case in the editor (verified affordance), then Clear succeeds. |

## Storage surface (extends `02-storage-core`, mirrors `_enums.py`)

- `write_project_enums(project, data)` — D1 (round-trips through
  `_parse_project_enums` before writing; `_atomic_write_bytes` +
  `_mark_write` + `_invalidate_enums_cache`).
- `rename_enum_key(project, kind, old_key, new_key)` — D4 cascade; returns
  the count of features rewritten (for the API response / UI toast).
- `clear_project_enums(project)` — D11; under the project lock, **blocks**
  (raises, mapped to `409`) if any kind/key is still referenced; otherwise
  resets the file to `_ENUMS_DEFAULT_BYTES`. Reuses the D3 usage guard — no
  cascade.
- `count_enum_key_usage(project, kind, key) -> (int, list[str])` — usage
  count + a small sample of paths; backs D3's block-on-in-use check, the
  rename preview, and D11's Clear guard / detailed error message.
- All new mutations take the **project-scoped lock** (`_lock_for`) and
  `_mark_write` every file they touch.
- _No new lister needed: the Enums tab reuses `Storage.list_root()`
  (depth-0 project folders, `_listing.py:22-30`) (A8)._

## HTTP surface (extends `routes_enums.py`)

- `PUT /api/enums/<project>` — replace document (D2); `422` on schema
  violation, `409` on in-use removal (D3), `404` if project/file missing.
- `POST /api/enums/<project>/rename` — `{kind, old_key, new_key}`; `200`
  with `{renamed: <count>}`; `404`/`422` as above; `409` if `new_key`
  already exists in the kind.
- `POST /api/enums/<project>/clear` — D11; `200` with `{cleared: true}` on
  success, or `409` with the in-use enum(s) + referencing case path(s) and a
  message instructing the user to clear that enum in the test case first.
- `GET /api/enums/<project>/usage?kind=&key=` — usage count + sample, for
  the manager's remove/rename preview. _(Optional if the count is folded
  into the `GET /api/enums/<project>` payload — decide in Plan.)_
- (`POST /api/enums/<project>` init — **already exists**, reused for legacy
  projects / the Initialize action.)

## UI surface — new "Enums" sidebar tab (D5)

Mirrors the Test-run / Reports tab pattern exactly:

- **`base.html`** — a 4th `data-sidebar-tab="enums"` button in `#sidebar-tabs`
  and a 4th `#enums-pane` `<aside>` placeholder.
- **`02_sidebar.js`** — `tmsSwitchSidebarTab` toggles the new pane;
  `tmsActivateEnumsPane` lazy-mounts `GET /ui/enums-tree` with
  `hx-trigger="sse:change"`.
- **`enums_sidebar.html`** — lists projects (`Storage.list_root()`), each
  linking `hx-get="/ui/enums/<project>"` into `#main-pane`; a small badge
  marks projects whose `enums.yaml` is missing (legacy).
- **`routes_ui.py`** — `GET /ui/enums-tree` (project list partial) and
  `GET /ui/enums/<project>` (the manager view).
- **Manager view** (`enums_manager.html` in `#main-pane`): kinds as sections,
  each listing `key — [label input]` rows with **remove** (guarded by
  usage), inline **add entry**, **rename key** (confirm shows cascade count),
  **add/remove kind**, plus a **Clear (fresh start)** action (D11, blocked
  with a detailed in-use message if any enum is still referenced) and the
  legacy **Initialize** state. A new
  `09_enums_manager.js` (or extension of an existing controller) drives the
  `PUT` / `rename` / `clear` calls.
- **Editor deep-link** — the editor's `#feature-enums` header
  (`file_editor.html:115-128`) gains a link that opens the Enums tab focused
  on the current project.
- **Cache refresh** — on a successful write the manager updates
  `tmsEditor._vocabCache[project]`; the editor also subscribes to
  `sse:change` to pick up external edits (D6).

## Confidence summary

| Area | Confidence | Gated by |
|---|---|---|
| `write_project_enums` + whole-doc PUT | **HIGH** | symmetric with init (D1/D2) |
| Validation reuse | **HIGH** | `_parse_project_enums` (D7) |
| Rename cascade correctness | **MEDIUM** | alias ordering + dry-run (D4/A4) |
| In-use removal policy | **HIGH** | block confirmed (D3) |
| UI: new sidebar tab | **HIGH** | fits existing tab shell (D5) |
| Clear (fresh start) | **HIGH** | block, reuses D3 guard (D11) |
| Backfill script | **HIGH** | thin wrapper over init (D10) |
| SSE / cache refresh | **HIGH** | external-only, self-refresh (D6/A5) |

## Scope slices (Plan / Do — all decisions resolved; ready to start)

- **S1 — Storage write + serialize.** `write_project_enums` + canonical
  serializer + cache invalidation; round-trip + schema-reject smokes.
  **Blocks S2–S5.**
- **S2 — Whole-document API + usage.** `PUT /api/enums/<project>`, in-use
  removal guard (D3), `count_enum_key_usage`; HTTP smokes.
- **S3 — Rename + cascade.** `_rewrite_features_enum`, `rename_enum_key`
  (alias-first, dry-run) + `POST …/rename`; cascade correctness +
  crash-ordering smokes.
- **S4 — Sidebar tab + manager view + SSE refresh.** New Enums tab, project
  list, `/ui/enums/<project>` manager, the `clear` action (D11), and
  `sse:change` cache invalidation; behavioural smokes (add/remove/edit,
  rename + clear reflected in an open picker).
- **S5 — Backfill script (D10).** `scripts/backfill_enums.py` (idempotent,
  skips initialised projects); smoke runs it over a mixed fixture (one
  legacy, one already-initialised) and asserts only the legacy one gains a
  default file.

## Smoke plan (`.smoke-scratch/feature-13/`)

- Round-trip stability: `read → write_project_enums → read` is identity;
  empty-kind emits the seed format (A1).
- Schema reject: bad identifier / duplicate key / empty label → 422, file
  unchanged.
- In-use removal blocked: removing a referenced key → 409 with count; file
  unchanged (D3).
- Rename cascade: every referencing `.feature` rewritten `old→new`; vocab
  ends with only `new_key`; a feature that didn't reference it is untouched;
  dry-run aborts (no writes) if any feature fails to parse (D4).
- Rename alias window: at no observable step does a feature reference an
  undefined key (A4).
- Clear (fresh start): blocked with `409` + in-use detail while any case
  references the vocab; succeeds (file reset to seed) once all references are
  cleared (D11).
- Auto-init regression: creating a project yields a default `enums.yaml`
  (`components:\n`) — pins the already-shipped D9 behaviour.
- Backfill script: over a mixed fixture, only legacy projects gain a file;
  re-running is a no-op (D10).
- Sidebar tab: `/ui/enums-tree` lists projects; `/ui/enums/<project>`
  renders the manager (missing-file projects show the Initialize state).
- SSE refresh: an external `enums.yaml` edit invalidates the client cache
  on `sse:change` (D6).

## Acceptance criteria

- Add a kind / add, rename, remove an entry, and edit a label entirely
  through the UI, with the file staying schema-valid (or the action being
  rejected with a clear message) at every step.
- Renaming a key updates every referencing `.feature` atomically-enough that
  no case is ever left orphaned by the operation itself.
- Removing an in-use key/kind is prevented (D3) — never a silent orphan;
  Clear (D11) follows the same block rule and only resets the file once no
  case references the vocabulary.
- A new **Enums** sidebar tab lists every project and opens a per-project
  manager in the main pane; legacy projects offer Initialize.
- The backfill script brings every legacy project up to a default file in
  one idempotent run.
- An open test-case editor reflects vocabulary changes (own-tab edits
  immediately; external disk edits via `sse:change`) without a manual reload.
- Each slice ships with its own smoke(s); suite green after each.

## Affects / cross-references

- `app/storage/_enums.py` — `write_project_enums`, `rename_enum_key`,
  `clear_project_enums`, `_rewrite_features_enum`, `count_enum_key_usage`
  (S1/S3/S4).
- `app/server/routes_enums.py` — `PUT` + `/rename` + `/clear` (+ optional
  usage) (S2/S3/S4).
- `app/server/routes_ui.py` + `app/templates/enums_sidebar.html` +
  `enums_manager.html` — the new tab's partials (S4).
- `app/templates/base.html` + `app/static/02_sidebar.js` — the 4th tab
  button, pane, and `tmsActivateEnumsPane` (S4).
- `app/static/08_file_editor.js` + `app/templates/file_editor.html` — editor
  deep-link, picker re-render, `sse:change` subscription (S4).
- `scripts/backfill_enums.py` — one-time legacy backfill (S5, D10).
- `app/storage/_folders.py:58-66` — project-create auto-init (D9, already
  shipped; pinned by a regression smoke).
- `specs/features/11-feature-testcase-component-NEW.md` — supersedes its
  "deferred `write_project_enums`" / "hand-edit only" notes once shipped.
- `specs/features/03-feature-watcher-and-sse-NEW.md` — the `sse:change`
  consumer added here; self-write suppression constraint (A5).

## Evolution / versioning

**Shipped (Jun 11, 2026)** — all twelve decisions resolved and all five
slices (S1→S5) delivered with 17 feature-13 smokes; full suite 262/262 green.
As-built recorded in `DONE.md` § Could have; spec-11's deferral notes
reconciled. This spec is now a historical record of the design + decisions.
