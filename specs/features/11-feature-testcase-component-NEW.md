# 11 · Test case project-level enums (component, ...)

_Forward-looking Investigate-phase spec. Status: **Spec'd**
(Investigate signed off Jun 8, 2026; Plan/Do still pending).
Kicked off Jun 8, 2026 from the `IN-PROGRESS.md` "Investigate new
test-case data: component" item; scope broadened same day from
"single `component` field" to **"generic enum map driven by
`enums.yaml`"** — `component` is the first enum kind to ship, but
the data shape, validator, parser, serializer, and editor surface
all generalise over any enum kind the project defines._

## Problem statement

The downstream "quality report" feature (sibling Investigate item
in `IN-PROGRESS.md`) wants to answer "which AREA of the product
fails most often in a given test run". Today the only test-case
metadata that could carry that signal is the **tag** list on the
feature or the scenario, which:

- is free-form and unbounded — every tag the team writes is
  equally weighted; there is no notion of a "primary owning area";
- mixes orthogonal concerns (priority, status, automation flag,
  team owner, product area) into one flat namespace.

A first-class `component` concept lets reports group failures by a
known dimension without re-purposing tags. Rather than hard-coding
a `component` field, the test case carries a **generic enum map**
whose shape mirrors the project's `enums.yaml`. Adding a new enum
kind to the YAML (e.g. `priorities`, `automation_status`) makes
it available everywhere — dataclass, validator, editor picker —
with **zero code change**. v1 ships with `components` as the first
and only seeded enum kind.

## Out of scope (for this spec)

- The quality-report rendering itself — separate Investigate item.
- Folder-level filtering by tag — separate Investigate item
  (`folder-level test case filter`).
- Project-wide tag governance (linting, normalisation, suggested
  tag lists). Component vocabulary is in scope; general tag
  hygiene is not.
- Downstream features that *consume* a specific enum kind (e.g.
  a `priorities`-driven report) — only the data plumbing for
  arbitrary enum kinds is in scope; product behaviour layered on
  individual kinds is its own work.

## Decisions (Q1–Q5 resolved Jun 8, 2026)

- **Q1 — Storage shape: generic enum map on `Feature`.**
  Add `Feature.enums: dict[str, str]` to the dataclass. Outer
  keys are enum kind names (matching top-level keys in the
  project's `enums.yaml`); values are the selected enum **key**
  (the `snake_case` identifier defined under that kind in the
  YAML), or empty string = unset. Display labels are not
  stored on `Feature` — they are resolved at render time.
  The model is typed and generic — no per-enum-kind fields.
- **Q2 — Cardinality: exactly one per enum kind (optional).**
  Empty string = unset for that kind. A test case attributes
  failures to at most one bucket *per kind* — matches the
  "most-failed AREA" framing 1:1 for components and keeps
  per-kind report aggregation a simple `Counter`.
- **Q3 — Vocabulary: project-level enums YAML.** Each project
  owns a single `enums.yaml` file at the project root that lists
  the canonical set of values for **every** project-level enum,
  as `- <key>: <label>` mappings under each kind. The **key**
  (snake-case-ish identifier) is what gets stored in the test
  case; the **label** (free text) is what the editor displays.
  `components` is the seeded kind in v1; arbitrary additional
  top-level kinds are first-class and immediately surfaced by
  the editor / validator on next read.
- **Q4 — Relationship to tags: collapsed.** Enum values are a
  distinct domain concept on the model side, regardless of the
  on-disk encoding (see Q5). The pending `test-report`
  Investigate item does **not** collapse into this one.
- **Q5 — On-disk encoding: namespaced header comments.** Each
  enum kind with a non-empty value serialises as a single
  `# enum.<kind>: <key>` line at the top of the `.feature`
  file, one line per kind. The `enum.` prefix is reserved to
  avoid collision with hand-written comments like `# todo: x`
  or `# note: y`. The header carries the **key**, never the
  display label — labels are a UI concern resolved at render
  time from `enums.yaml`. Parser extracts them via a pre-parse
  scan; serializer re-emits them in canonical (alphabetical)
  order. Spec'd in the *On-disk format* subsection below.

## Design

### Data model — `Feature.enums`

In `app/models.py`:

- `Feature.enums: dict[str, str] = field(default_factory=dict)`
  (new field on the dataclass). Outer keys are enum kind names
  (matching top-level keys in `enums.yaml`); values are the
  selected enum **key** (matching one of the keys defined under
  that kind in `enums.yaml`), or empty string for *unset*.
  Display labels are **not** stored on `Feature` — they are
  resolved at render time from `enums.yaml`.
- `Feature.to_dict()` / `from_dict()` extend to carry `enums`.
- `validate_feature` rules (pure-model, project-agnostic):
  - Every kind name (outer key) must match the identifier
    regex `^[A-Za-z_][A-Za-z0-9_]*$`. The on-disk encoding
    uses `:` as a delimiter, so `:` is implicitly disallowed.
  - Every selected key (value) must be either the empty string
    OR a single-line string matching the same identifier regex.
  - **Empty value is always legal** — it represents *unset*
    for that kind. The pure model never rejects an unknown
    enum kind or an unknown key; project-aware cross-checking
    happens in storage (the model has no project context).

Why single-string per kind, not `list[str]`: see Q2.

### Project-level enums file — `<project>/enums.yaml`

One YAML file at the project root, alongside module folders and
the `test-run/` reserved folder. Schema:

```yaml
# <project>/enums.yaml
components:
  - login: Login by credential
  - login_by_SSO: Login by SSO
  - user_base: User manager module
# future: priorities, automation_status, ...
#   each kind: a list of single-key mappings `<key>: <label>`.
```

A multi-kind project (shape used by the demo project ships with):

```yaml
# <project>/enums.yaml — multi-kind example
components:
  - login: Login by credential
  - login_SSO: Login by SSO
  - user_manager: User data manager
  - workspace_manager: Workspace data manager
priorities:
  - p0: Blocker
  - p1: High
  - p2: Medium
  - p3: Low
sprint:
  - init: Sprint 0
  - sprint_run: Development sprint
  - maintenance: Maintenance mode, no development sprint
automation_status:
  - manual: Manual only
  - in_progress: Automation in progress
  - automated: Automated
```

For a feature file that has `components: login` and
`priorities: p1` selected via the editor, the on-disk
encoding is:

```gherkin
# enum.components: login
# enum.priorities: p1
@smoke
Feature: Sign in
  Scenario: ...
```

Per-kind directives are emitted in **alphabetical kind order**
immediately above the leading tag / `Feature:` keyword.
Hand-written comments like `# todo: ...` are preserved as
ordinary comments (the parser only lifts the `enum.` -prefixed
ones into structured state).

Rules:

- Top-level keys are **enum kind names**; each value is a
  **list of single-key mappings** of the form `- <key>: <label>`.
  - `<key>` is the stable identifier stored in test cases (must
    match `^[A-Za-z_][A-Za-z0-9_]*$` — letters, digits,
    underscores; must start with a letter or underscore).
  - `<label>` is the display text shown in the editor picker
    (non-empty, single-line, free text — any printable
    Unicode allowed).
  - Keys must be **unique within a kind**. Insertion order is
    preserved and used as the picker display order.
- **All top-level kinds are first-class**: v1 surfaces every
  kind in the editor (one picker per kind) and validates
  against every kind at write time. There is no allow-list of
  "known" kinds.
- An empty value (e.g. `components:` with no items, or
  explicit `components: []`) is legal — it means "this
  project hasn't defined entries for this kind yet". Both
  parse-paths normalise to `{}` for that kind. The editor
  renders the picker as disabled with a hint pointing at the
  YAML file.
- A kind with no entry at all in `enums.yaml` is **unknown**
  to the project; saving a non-empty value (key) for an unknown
  kind is a write-time error (see Storage section).
- Kind naming: same identifier regex as the inner keys. Lower
  snake_case recommended (e.g. `components`, `automation_status`).
- File name `enums.yaml` is **reserved at the project root**:
  no module folder may be named `enums.yaml` (folder names
  ending in `.yaml` are already unusual but should be rejected
  explicitly — see Storage section).

In-memory shape after parsing: `dict[str, dict[str, str]]`
(outer kind → inner ordered `{key: label}` map). The list-of-
mappings form is normalised to a plain ordered dict; duplicate
inner keys raise `EnumsParseError`.

### Lifecycle — init on create, manual for existing

- **Auto-init on project create.** Today projects are created
  via `Storage.create_folder(["<project>"])` (depth-1 path);
  see `app/storage.py::create_folder`. The method is a single
  uniform `mkdir(parents=False)` that already handles all
  depths; we add a `len(segments) == 1` branch immediately
  after the `mkdir` to also write the default `enums.yaml`
  next to the newly-created folder. The default file contains
  `components:` (a single key with no value, which `pyyaml`
  parses to `None` and we normalise to `{}` per the empty-
  file rule). The default file is empty-by-content but
  present-by-existence; teams fill it in.
- **Manual init for existing projects.** A new explicit action
  `POST /api/enums/<project>` writes the same default
  `components:` file. Returns 201 on create, **409
  `NameConflictError`** if the file already exists (no
  overwrite). Surfaced in the UI as an `Initialize enums file`
  button on the project view; the button is shown only when the
  file is missing.
- **Edit flow for v1**: hand-edit `enums.yaml` in any editor.
  A CRUD UI on top of the file is explicit follow-up work
  (captured under *Surface for follow-up*).

### Storage surface (extends `02-storage-core`)

New methods on `Storage`:

- `read_project_enums(project: str) -> dict[str, dict[str, str]]`
  — reads + parses + validates `<project>/enums.yaml`. Uses
  `yaml.safe_load` (never the unsafe loader). Returns the
  outer-kind → inner `{key: label}` map (insertion order
  preserved). Missing file → `FileNotFoundError`. An empty
  file, a comment-only file, or a YAML document whose top-
  level is `None` is treated as `{}` (no kinds defined — same
  effective behaviour as a missing file for cross-checking,
  but the file itself counts as present for the
  `Initialize enums file` 409 check). Malformed YAML or schema
  → `EnumsParseError` (new error class, 422 in the API).
  Schema validation enforces:
  (a) every inner list element is a `dict` with **exactly
      one** key (the `- <key>: <label>` shape);
  (b) every key matches the identifier regex
      `^[A-Za-z_][A-Za-z0-9_]*$`;
  (c) every label is a non-empty string with no embedded
      newline (`"\n" not in label`);
  (d) keys are unique within a kind.
- `init_project_enums(project: str) -> None` — writes the
  default file. Exact bytes: `"components:\n"` (the kind name
  with no value, UTF-8, single trailing LF — written as a
  byte literal, **not** via `yaml.dump`, which would emit
  `components: null\n`). `pyyaml`'s `safe_load` parses these
  bytes to `{"components": None}` which `read_project_enums`
  normalises to `{"components": {}}` per the empty-value rule.
  Raises `NameConflictError` if the file already exists.
- _`write_project_enums(project: str, data: dict) -> None` is
  **deferred to the CRUD-UI follow-up** — v1 has no caller
  (hand-edit on disk + `init_project_enums` cover every
  write path). Listed here for completeness; do **not**
  implement in S2._
- `_reject_reserved_typed_area` / `_validate_segment` extended
  to also forbid a depth-2 folder named `enums.yaml` (cheap
  belt-and-braces; folder names are already constrained but
  explicit rejection makes the reservation legible).
- `list_tree` filters out `enums.yaml` at depth 2 (project
  root) so the file does not surface in the Directory tree.
  `list_folder` at depth 1 (project view) already returns
  only modules (folder names — see `app/storage.py::list_folder`
  depth-1 branch); no file-level filter needs adding there.
  v1 has **no UI** for editing the file beyond the
  `Initialize enums file` action; teams hand-edit it on disk.
  A CRUD UI is deferred to a follow-up Investigate item (see
  *Surface for follow-up*).

Enum cross-check on test-case save:

- `Storage.write_feature(parts, feature)` (and `write_raw`,
  `create_file`): for every `(kind, key)` pair in
  `feature.enums` where `key != ""`, look up the owning
  project (the first segment of `parts`), read its `enums.yaml`,
  and reject the save with a `ValidationError` if either
  (a) `kind` is not a top-level kind in the YAML, or
  (b) `key` is not one of the keys defined under that kind.
- Pairs with empty values are ignored by the cross-check
  (storage never forces a value to be set; *unset* is always
  legal regardless of what the YAML contains). When
  `feature.enums` has **zero non-empty entries**, the
  cross-check is skipped entirely — `enums.yaml` is not even
  opened.
- **Missing-file rule.** When `feature.enums` has non-empty
  entries but `<project>/enums.yaml` does not exist (legacy
  project), the cross-check treats the project as having
  **no enum kinds defined** → every non-empty entry is
  orphan → save is **rejected with 422** and a
  `validation_error` whose message points the user at the
  `Initialize enums file` action. This preserves the
  write-strict invariant and avoids quietly accumulating
  unvalidated values.
- Labels are **never** validated against — they are display-
  only and may be edited freely in `enums.yaml` without
  invalidating any `.feature` file.
- **Caching (in-scope v1).** `read_project_enums` keeps an
  in-memory cache keyed by project, with an **mtime check on
  every access**: if the file's mtime is unchanged since the
  last read, return the cached parsed value; otherwise re-read,
  re-parse, refresh the cache, return the new value. Cost per
  access is one `os.stat` plus a dict lookup on the hot path.
  This makes hand-editing `enums.yaml` (the v1 CRUD workflow)
  take effect on the next server-side access without any
  process restart, while keeping the cross-check on test-case
  save effectively free. `init_project_enums` also refreshes
  the cache from its own write so the in-process consistency
  is immediate (the deferred `write_project_enums` will do
  the same once it lands).
  Watcher-based invalidation (`03-watcher-and-sse`) is a
  follow-up optimisation if `os.stat` ever shows up in
  profiling.

### HTTP surface (extends `04-folder-crud` / `05-testcase-crud`)

Route naming follows the existing project-scoped convention
established by `10-feature-test-run` (`/api/runs/<project>/groups`,
not `/api/projects/<project>/runs/groups`). The enums endpoints
live under `/api/enums/<project>` for the same reason.

- `POST /api/enums/<project>` — init action. 201 on create,
  **409 `NameConflictError`** if the file already exists
  (no overwrite, matching `RESERVED_DEPTH2_NAMES` semantics).
  The 201 response body includes the freshly-written enums
  dict so the client can update its in-session cache without
  an extra round-trip.
- `GET /api/enums/<project>` — returns the parsed enums dict
  (`{<kind>: {<key>: <label>, ...}, ...}`, insertion order
  preserved). The editor uses this to render one picker per
  kind, with `<option value="<key>">{label}` pairs. 404 if
  the file is missing. **Fetch semantics:** the client
  fetches once per (project, session) on first access and
  caches client-side (see Operational notes — no SSE-driven
  live refresh in v1).
- `PATCH /api/files/<path:p>` / `PUT /api/files/<path:p>/raw` —
  already exist (`server.py::patch_file`, `put_file_raw`);
  gain the cross-check side-effect via the `write_feature` /
  `write_raw` updates in storage. Bad enum kinds / keys
  surface as 422 `validation_error` with a field reference
  pointing at the offending `enums[<kind>]`.

### Editor surface (extends `08-file-editor`)

- Structured tab: a new `Enums` section near the tags row
  renders **one `<select>` per top-level kind** in the project's
  `enums.yaml`. Pickers are generated dynamically from
  `GET /api/enums/<project>` — no per-kind code in the
  editor.
  - Each `<select>` includes a leading `— not set —` option
    whose `value` is the empty string; this is the default
    for any kind that the test case has not yet been assigned
    a value for.
  - Per-entry options render as `<option value="<key>">{label}
    </option>` — the editor submits the **key** on save while
    the user sees the **label**.
  - Empty-list kinds (e.g. `priorities: []` defined but no
    entries yet) render a disabled control with hint text
    *"No `<kind>` entries defined yet — edit `enums.yaml` to
    add some."*
- Missing-file state (legacy projects): the whole Enums section
  collapses to a single inline `Initialize enums file` button
  that calls the init endpoint and refreshes the section on
  success.
- Raw tab: the `# enum.<kind>: <key>` lines are visible verbatim
  in the raw text (keys only, never labels). Editing them there
  round-trips through the same parse → validate → serialise
  pipeline as any other raw edit.

### Error handling — new / removed / unknown enum kinds

The v1 contract is **read-tolerant, write-strict**:

- **New enum kind added to `enums.yaml`** (e.g. team adds
  `priorities` after some test cases already exist). All
  existing test cases automatically expose the new picker in
  the editor with the `— not set —` option selected and the
  underlying `feature.enums["priorities"]` defaulting to `""`
  (or being absent from the dict, which is treated identically).
  Users assign values per test case, on their own schedule.
  **Saving a test case never forces a value to be set** for any
  kind — the empty default is always a legal write.
- **Enum kind removed from `enums.yaml`** while some test cases
  still carry a value for it: the value is **preserved on read**
  (so transient YAML edits don't silently drop data) and shown
  in the structured tab as an *orphan* row with a warning
  badge. Saving the test case with the orphan value still set
  is rejected (422); the user must either clear the value
  (set it to *not set*) or re-add the kind to `enums.yaml`.
  - **Editor detection logic.** The editor joins the test
    case's `feature.enums` (from `GET /api/files/<p>`) with
    the project vocabulary (from `GET /api/enums/<project>`):
    a `(kind, key)` pair is *orphan* iff `kind ∉ vocab` **or**
    `kind ∈ vocab ∧ key ∉ vocab[kind]`. Orphan rows render
    as a labelled chip (`<kind>: <key>`) with a warning badge
    and a `Clear` action; they sit at the end of the Enums
    section so non-orphan pickers stay aligned with the
    project vocabulary order.
- **Unknown enum kind on disk** (a `# enum.foo: bar` header in
  a `.feature` file but no `foo` key in `enums.yaml`): same as
  the *removed* case above — preserved on read, surfaced as an
  orphan, blocks save until reconciled.
- **Unknown key for a known kind** (`# enum.component: bogus`
  when `bogus` is not a key in `enums.yaml#components`): same
  handling — preserved on read, flagged in the editor, save
  blocked. Note: label changes in `enums.yaml` (renaming the
  display text while preserving the key) do **not** invalidate
  any `.feature` file, because only keys are stored on disk.

The rationale: never lose user data on a transient YAML edit
(read-tolerant), but never let drift persist beyond an explicit
save (write-strict).

### On-disk format — `# enum.<kind>:` header comments

Selected encoding (Q5.b, generalised to N kinds, namespaced
under `enum.` to avoid collision with regular comments):

- **Shape.** Zero or more lines, one per non-empty enum value,
  matching `# enum.<kind>: <key>` (one space after `#`, one
  space after `:`). Emitted **immediately above any feature-
  level tags or the `Feature:` keyword**, whichever comes
  first. Only the **key** is written — labels live in
  `enums.yaml` and are resolved by the editor at render time.
  Comparable to the existing `# language: <code>` convention
  `gherkin-official` already knows about; the `enum.` prefix
  reserves a private namespace so generic comments like
  `# todo: refactor` are **not** misinterpreted as directives.
  Example:

  ```gherkin
  # enum.component: login_by_SSO
  # enum.priority: p0
  @smoke
  Feature: ...
  ```

- **Parse path.** `gherkin_io.parse_feature` calls
  `Parser().parse(source)` unchanged — `gherkin-official`
  already exposes every leading `#` comment in the AST's
  `comments[]` array (verified Jun 8, 2026 against the
  installed version). After parsing, compute the cutoff line
  as `cutoff = min(feature.location.line, first_tag_line)`
  where `first_tag_line = feature.tags[0].location.line` if
  `feature.tags` is non-empty, else `feature.location.line`.
  Walk `comments[]`: for each entry whose `location.line
  < cutoff`, trim the text and match it against
  `^# *enum\.([A-Za-z_][A-Za-z0-9_]*): *([A-Za-z_][A-Za-z0-9_]*) *$`.
  Capture each `(kind, key)` pair into `Feature.enums`.
  Duplicate `kind` in the header → `GherkinParseError`.
  Comments not matching the regex (e.g. `# todo: refactor`,
  `# note: see PR_47`) are ignored — they remain regular
  comments to `gherkin-official` and are discarded by the
  existing `01-gherkin-io` invariant. No source-string
  manipulation; line numbers in subsequent parse errors are
  preserved by construction.
- **Serialize path.** `gherkin_io.serialize_feature` emits one
  `# enum.<kind>: <key>` line per entry in `feature.enums`
  whose value is non-empty, in **alphabetical order by kind**
  for canonical formatting, before any feature-level tags.
  Entries with empty values are skipped — so files that
  don't use a given kind round-trip byte-identically even if
  `enums.yaml` later adds that kind.
- **Validation.**
  - Each key (right of `:`) must match the identifier regex
    above; whitespace-only or non-identifier text on the
    right of `:` is rejected at parse time
    (`GherkinParseError`).
  - Each kind name (between `enum.` and `:`) must match the
    identifier regex above.
  - At write time, the cross-check against the project's
    `enums.yaml` runs in storage (see Storage section).
    Unknown kinds or unknown keys for a known kind → 422
    `validation_error`.
- **Edge cases.**
  - Comments **after** the first feature-level tag or the
    `Feature:` keyword are not extracted — directives must
    precede them. Mirrors the `# language:` placement
    convention. Indentation inside the leading block is
    tolerated (gherkin-official preserves leading whitespace
    in `comment.text`; we trim before regex match).
  - DocString-internal `# enum.<kind>: <key>` lines are not
    extracted (they live inside a scenario, well past the
    cutoff line).
  - Round-trip invariant: `serialize(parse(serialize(parse(x))))
    == serialize(parse(x))` continues to hold; directives are
    canonicalised to single-space formatting, alphabetical
    order on every save.
  - Bare `# <kind>: <key>` (no `enum.` prefix) is **not** a
    directive — it remains an ordinary comment, which
    `gherkin-official` then drops at parse time per the
    existing comments-are-discarded invariant in
    `01-gherkin-io`.

## Discoveries from the existing codebase

- `gherkin-official` already tolerates `# language: <code>` as
  a leading header comment (see `01-gherkin-io` invariants).
  The `# enum.<kind>:` directives piggyback on the same shape,
  so no parser surgery beyond a small pre-parse scan is
  required (the same scan handles any number of kinds).
- Projects today are plain depth-1 folders created via
  `Storage.create_folder(["<project>"])` (no dedicated
  `create_project` method). The auto-init hook lands inside that
  function's depth-1 branch.
- Test runs deliberately link to test cases by external
  `file_path` rather than extending `Feature` (see
  `10-feature-test-run`'s *Surface for follow-up*). This spec
  consciously diverges from that precedent because enum values
  (component, priority, ...) are **definitional** attributes of
  a test case — they travel with the case across renames and
  moves — whereas run results are a **historical** attribute of
  a run (they belong to the run, not the case).

## Affects

- `01-gherkin-io` / `app/models.py`: new
  `Feature.enums: dict[str, str]` field on the dataclass;
  `to_dict` / `from_dict` / `validate_feature` extended. Parser
  gains a pre-parse scan for `# <kind>: <value>` directives;
  serializer emits one line per non-empty entry, alphabetically
  ordered, above tags / `Feature:`.
- `02-storage-core`: new methods `read_project_enums` and
  `init_project_enums` (`write_project_enums` is **deferred**
  to the CRUD-UI follow-up — no v1 caller); the `create_folder`
  depth-1 branch auto-writes the default `enums.yaml`;
  `write_feature` gains the per-kind enum cross-check.
- `04-folder-crud`: project create gains the auto-init side
  effect; depth-2 reservation set conceptually extended to
  include the `enums.yaml` file name at the project root.
- `05-testcase-crud`: `PATCH /api/files/<p>` and
  `PUT /api/files/<p>/raw` reject unknown enum keys / values
  with 422; `GET /api/files/<p>` returns the new `enums` map.
- `08-file-editor`: structured tab gains an `Enums` section
  with one `<select>` per kind, dynamically generated from
  `GET /api/enums/<project>` (fetched once per project per
  session, cached client-side); missing-file legacy state
  surfaces an `Initialize enums file` button; orphan-value
  warning badges per the *Error handling* subsection.
- `06-tree-pane` / `07-folder-views`: `list_tree` and
  `list_folder` filter `enums.yaml` out of their listings at
  the project root — v1 has no UI surface for the file
  beyond the editor's init action.
- `09-search`: future-facing — filter-by-`<kind>` would reuse
  the existing search plumbing (substring or, with follow-up,
  a typed filter).

## Depends on

- `pyyaml` (already pinned in `requirements.txt` for
  `10-feature-test-run`).
- The feature-spec lifecycle in `specs/README.md`.
- `02-storage-core` atomic-write + per-path lock primitives
  for the enums file writes.
- `gherkin-official` continuing to tolerate / skip leading
  `# enum.<kind>:` comment lines in the source (it already
  tolerates `# language:` the same way — any line starting
  with `#` is a comment to the parser).

## Surface for follow-up

- The Investigate item `Investigate new feature: quality report`
  in `IN-PROGRESS.md` is unblocked by this — bucketing dimension
  is `Feature.enums["components"]` (and any other kind the team
  adds to `enums.yaml`).
- The Investigate item `Investigate new feature: test report` in
  `IN-PROGRESS.md` stays distinct (tag-based filtering, not
  enum-based).
- **Deferred Investigate item: per-project `enums.yaml` CRUD
  UI.** Add / remove a kind, add / remove entries within a
  kind, rename a key with cascade across affected `.feature`
  files. Also includes SSE-driven live refresh of in-session
  picker caches once the CRUD UI exists (the two land
  together). v1 ships with hand-edit-the-YAML + the
  `Initialize enums file` action only.
- A second enum kind (e.g. `priorities`) needs **zero code
  change** to ship — the editor renders the picker, the
  validator cross-checks values, the parser/serializer handles
  the on-disk directive. Only the product behaviour built on
  top of it (reports, filters) is new work.
- Bulk-edit (set the same enum value across N test cases) is
  not in v1 but is the obvious next ergonomic step once teams
  start adopting a new kind retroactively.
- If folder rename / project rename is ever added, the enums
  file travels with the project folder by construction (it's a
  sibling file). No coordination needed.

## Operational notes

- **Project create is not atomic across folder + enums file.**
  Step 1 (`mkdir <project>/`) and step 2 (`write
  <project>/enums.yaml`) are sequential; a crash between them
  leaves a project in the same state as a pre-existing legacy
  project (no enums file). The user reconciles via the
  `Initialize enums file` action — same code path. No recovery
  is needed; no special tombstone is written.
- **Picker data is fetched once per (project, session).** The
  editor calls `GET /api/enums/<project>` the first time the
  user opens a test case in a given project, then caches the
  result client-side for the rest of the session.
  v1 deliberately does **not** subscribe to `sse:change` for
  this resource — enum vocabulary changes are infrequent and
  the simpler model avoids cache-coherence complexity. External
  YAML edits (shell, other tabs, other users) take effect on
  the next page reload.
  - **One exception:** the `Initialize enums file` action
    refreshes the cache from the action's 201 response body,
    so the picker appears immediately after init without a
    reload.
  - **Out of scope for v1:** cross-tab cache invalidation,
    SSE-driven live refresh, or any in-session reload prompt
    when `enums.yaml` changes on disk. Tracked as a deferred
    refinement.
- **`EnumsParseError`** lives in `app/errors.py` alongside
  `RunParseError` (added by `10-feature-test-run`). The
  matching `@api.errorhandler(EnumsParseError)` is registered
  in `app/server.py` next to the other `*ParseError` handlers
  (see `app/server.py:472-509`), returning `422
  enums_parse_error` with `{line, column}` details when the
  parser can pin a location, otherwise just `{message}`.
- **Labels with `:` or other YAML-special characters** must be
  YAML-quoted (`login: "Login: by credential"`). The error
  message on a malformed YAML cell points at the offending
  line.
- **Plan/Do slicing (suggested).** Three slices in **strict
  linear order** (each depends on the prior), every slice
  independently smoke-testable under `.smoke-scratch/`:
  - **S1 — Model + parser/serializer.** `Feature.enums` field
    on the dataclass (`app/models.py`), comments-walking
    extraction in `parse_feature` (`app/gherkin_io.py`),
    serializer emit, pure-model validation. No HTTP, no
    storage change. Smokes cover round-trip + identifier
    regex + co-existence with `# language:` and stray
    non-directive comments. **Blocks S2.**
  - **S2 — Storage + auto-init.** `read_project_enums` +
    `init_project_enums` (no `write_project_enums` in v1 —
    deferred to the CRUD-UI follow-up), `create_folder`
    depth-1 side effect (`if len(segments) == 1` branch
    after `mkdir`, inside the existing `_lock_for` region),
    `write_feature` cross-check (including the missing-file
    rule), mtime cache, `list_tree` filtering of `enums.yaml`
    at depth 2 (project root — implementation-wise, `depth ==
    1` in `_tree_children`'s parameter, mirroring the existing
    `RESERVED_DEPTH2_NAMES` filter at
    `app/storage.py:346`), and the new
    `EnumsParseError` errorhandler registration in
    `app/server.py`. Smokes cover the cross-check matrix
    (unknown kind, unknown key, missing-file, empty-file,
    label-rename-no-op). **Depends on S1; blocks S3.**
  - **S3 — HTTP + editor UI.** `GET /api/enums/<project>` and
    `POST /api/enums/<project>` routes in `app/server.py`;
    `tmsEditor` controller in `app/static/app.js` gains an
    `Enums` section in the structured tab (HTML scaffold in
    `app/templates/file_editor.html`); fetch-once-per-(project,
    session) cache keyed by project name parsed from
    `state.path.split('/')[0]`; `Initialize enums file` button
    visible when `GET /api/enums/<project>` returns 404.
    Manual smokes for the picker UX. **Depends on S2.**

## Acceptance criteria

- Creating a new project produces both the project folder AND a
  default `<project>/enums.yaml` containing the exact bytes
  `"components:\n"`, in that order. (Crash recovery: per the
  Operational notes, a missing enums file after a partial
  create is reconciled via the `Initialize enums file` action.)
- `POST /api/enums/<project>` on a project whose file is
  missing returns 201 and writes the default file; on a project
  where the file exists, returns 409 and leaves the file
  untouched.
- `GET /api/enums/<project>` returns the parsed dict; malformed
  YAML returns 422.
- A test case saved with one or more enum keys that all
  resolve in `enums.yaml` round-trips correctly
  (PATCH → GET → byte-identical raw → PATCH again), with
  header directives emitted as `# enum.<kind>: <key>` in
  alphabetical kind order, carrying the **key** (not the
  label).
- A `.feature` file with hand-written non-directive comments
  in its header block (e.g. `# todo: refactor`,
  `# note: see PR_47`) **is not affected** — the parser only
  captures `# enum.<kind>: <key>` lines; other comments stay
  as comments and are discarded by `gherkin-official` per the
  existing invariant.
- A test case saved with an enum key **not** listed under that
  kind in the YAML returns 422 `validation_error` and leaves
  the file unchanged. Same for an enum **kind** not present in
  the YAML at all.
- Renaming a label in `enums.yaml` (e.g. changing
  `login: Login by credential` to `login: Sign in by
  credential`) does **not** invalidate any existing
  `.feature` file — only the key is stored on disk, and the
  key is unchanged.
- Existing `.feature` files (no header directives) round-trip
  byte-identically — the serializer emits nothing when
  `Feature.enums` has no non-empty entries.
- **Adaptability**: adding a new top-level kind to `enums.yaml`
  (e.g. inserting
  ```
  priorities:
    - p0: Blocker
    - p1: High
  ```
  ) immediately surfaces a new `<select>` in every test case's
  editor on next reload, defaulted to *— not set —*, with
  **no code change** and no migration of existing `.feature`
  files.
- **Default behaviour for new kinds**: a test case that has
  never been assigned a value for a given enum kind serialises
  with no directive for that kind, and the editor renders the
  picker with *— not set —* selected. Saving without
  picking a value is legal.
- **Orphan-value handling**: removing a kind from `enums.yaml`
  while a test case still carries a value for it preserves the
  value on read (data is never silently dropped) but blocks
  re-save until either the kind is re-added to the YAML or the
  orphan value is cleared in the editor.
- The structured editor's `Enums` section reflects the current
  `enums.yaml` contents; emptying any kind's list disables
  that kind's control with a hint pointing at the YAML file.
