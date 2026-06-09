# Business rules

Cross-cutting product / domain rules every feature spec under
`/specs/features` must satisfy. Summarised from `PLAN.md`; refer
there for rationale and edge cases. Where `DONE.md` records a change
that supersedes `PLAN.md` (e.g., folder depth, sub-folder file
placement), the rule below reflects the current state.

## Feature file invariants

- Each `.feature` file holds **exactly one** scenario (or scenario
  outline). Multi-scenario files are rejected on read.
- `Rule:` blocks are rejected on read (incompatible with the one-
  scenario invariant).
- A zero-scenario file is auto-fixed on read: a placeholder
  `Scenario(kind="scenario", name="", steps=[], examples=[], tags=[])`
  is injected. The next save persists it.
- `Feature.description` is required non-empty at write time.

## Scenario

- `Scenario.name` is optional, single-line, may be empty — never
  auto-derived from `Feature.description`.
- `Scenario.tags` stored without the leading `@` in the model; the
  serializer prepends it and the UI renders chips with `@`.
- Steps may use Given / When / Then / And / But in any order (no
  positional restriction on keywords).
- Step keywords outside those five (e.g. non-English) are silently
  dropped on read — documented data-loss risk.
- `Step.text` is required non-empty at write. Empty-text steps are
  silently removed by the Save-click cleanup. Cleanup does NOT
  rewrite keywords, so orphan `And` / `But` may remain.

## Scenario Outline

- `kind == "outline"` requires `len(examples) >= 1` at write time.
- Default examples on outline creation / kind switch:
  `[ExamplesTable(header=["col1"], rows=[])]`.
- Switching Outline → Scenario is refused if the current examples
  table differs from the default by exact case-sensitive comparison
  (header values + count + rows). User must clear first.
- `kind == "scenario"` requires `examples == []`.

## Background

- Always present in the model. Omitted from disk when
  `background.steps` is empty.

## Tags

- Non-empty, whitespace-free, ASCII-printable, must not contain `,`
  (used as a chip separator). Stricter than Gherkin's official rules;
  non-conforming external tags fail validation on first save.
- Duplicates within the same tag list are de-duplicated at write
  time (order preserved, first occurrence kept).

## File / folder operations

- `.feature` files live in a module (depth 2) or any sub-folder
  beneath a module (depth 3..10). Files directly at the data root
  or directly under a project (depth 1) are rejected by the API.
- File CRUD: create, rename (same-parent only), duplicate (same-
  parent only), delete (idempotent), move (file → another folder at
  depth 2..10, leaf name preserved).
- Cross-module move historically required delete + create; the
  `PATCH /api/files/<p>/move` endpoint (post-DONE.md) now supports
  moves within the data root.
- Folder creation depth (API): 1..10 (i.e., project + up to 9 nested
  levels).
- Folder rename / delete depth: any. Rename is same-parent only.
- Tree UI shows folders and files at any depth; sub-folders below
  modules now have a first-class folder view (post-DONE.md).
- Non-`.feature` files render an "unsupported" page when opened.

## Save semantics

- Explicit Save button only. No auto-save. `beforeunload` warns when
  a dirty buffer exists.
- Save button is disabled when `Feature.description` is empty or
  whitespace-only.
- **Save-click cleanup** runs before validation / API call:
  - Drop any step (Background or Scenario) with empty / whitespace
    text.
  - Drop any examples row consisting entirely of empty cells (header
    preserved).
  - If cleanup leaves the buffer invalid (e.g., outline with zero
    rows after cleanup), show inline error and abort the save.
- When file name and content both change, the save flow is rename
  PATCH first, then content PATCH at the new path. Any non-2xx
  aborts the chain; the editor stays on its current path.
- A transient `Saved` badge (1.5 s) confirms each successful save in
  the editor topbar (post-DONE.md).
- External rename / delete of the open file shows a banner with
  Save (to new path) / Save-as / Discard actions. Save button is
  disabled while the banner is up. Dirty buffer is preserved.
- Cross-writer conflict policy: last-write-wins.

## Search

- `match=text` matches `Feature.description` only.
- `match=tag` matches `Scenario.tags` only.
- Feature tags, examples tags, and step text are NOT searched in v1.
- Default case-insensitive. Scope: `all` / `project:<name>` /
  `module:<proj>/<mod>`.
- Result UX:
  - 0 hits → empty-state message.
  - 1 hit → open that file directly in the editor.
  - ≥ 2 hits → list view; each row shows `file_path` + the first
    line of `description` + a badge with `matched_field` and
    `match_value`.
- Search input fires on Enter or after a 300 ms typing pause; empty
  queries do not fire.

## Round-trip caveats (documented data-loss risks)

- DocStrings (`"""…"""`), comments, blank lines, and `# language:`
  headers are parsed and discarded on read; never written back.
- Non-canonical step keywords are silently dropped on read.
- Externally-authored files with a multi-line body description
  block are reformatted to a single-line `Feature:` with literal `\n`
  on first save (no content loss, just canonicalisation).
- A literal `\n` typed by a user inside a description textarea
  round-trips as a real newline on the next save.
- Save-click cleanup may leave orphan `And` / `But` steps on disk;
  downstream tools (e.g., `behave`) resolve them against the
  nearest logical predecessor.
