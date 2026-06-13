# 14 · Import test cases (upload a `.feature`, split into cases)

_Build phase. Status: **DO-1–DO-4 shipped Jun 13, 2026 — awaiting manual
walkthrough + ACT cleanup.** Splitter (`split_feature_source` +
`_collect_children`) in `app/gherkin_io.py`; storage (`create_feature_file` +
`import_feature_cases`, all-or-nothing with compensating rollback, collect-all
`ImportValidationError`) in `app/storage/_features.py`; API
(`POST /api/files/import/preview` + `POST /api/files/import`, 3 MB cap on both)
in `app/server/routes_files.py` + `app/server/errors.py`; UI (`tmsImportFile`
modal + Import button) in `app/static/03_folder_actions.js`,
`folder_module.html`, `folder_subfolder.html`. Covered by `F14_01`..`F14_04`
smokes; full suite 286/286. Decisions IM-1..H + the three DO-2 decisions signed
off Jun 13, 2026 (see §5, §8). Filed from the `IN-PROGRESS.md` Must-have
"Investigate new feature: import test cases". Grounded against live code
Jun 13, 2026._

> [!IMPORTANT]
> **VERY IMPORTANT NOTE (as of feature 14): the TMS tool supports only
> _feature-level_ and _scenario-level_ tags — `Examples:`-level tags are
> NOT supported yet.** The import preview table exposes a **Feature tag**
> and a **Scenario tag** column only; there is no Examples-tag surface, and
> tag-based features (e.g. search/filter by tag) operate on feature +
> scenario tags only. _(Mechanism caveat: `ExamplesTable.tags` are parsed
> and re-emitted verbatim on file round-trip, so an outline's Examples tags
> survive an import unchanged — they are simply **not a first-class,
> surfaced tag concept** anywhere in the product yet. Treat first-class
> Examples-tag support as a future enhancement.)_

## 1. Goal (from the backlog)

- The user uploads a `.feature` file; the system validates **file type**,
  **format** (Gherkin), and **content**.
- One feature file may contain **one or more scenarios**. On import, each
  scenario is split out and saved as a **single test case** (one
  `.feature` file = one scenario, the TMS model invariant), all sharing the
  uploaded file's **feature description** and **feature tags**.

## 2. Why this is non-trivial (the core tension)

TMS's entire model is **one scenario per `.feature` file**. The parser
*actively rejects* multi-scenario input:

- `parse_feature` raises `GherkinParseError` on >1 scenario, on `Rule:`
  blocks, and on a missing `Feature:` header
  (`@/Users/hoang.tv/Documents/Projects/tms/app/gherkin_io.py:68-122`).
- The rejection lives in `_split_children`, which raises on the **second**
  scenario and on any `rule` child
  (`@/Users/hoang.tv/Documents/Projects/tms/app/gherkin_io.py:222-259`).

So the whole point of import — accepting a multi-scenario file — is the one
thing the current parser refuses. Import therefore needs a **new splitter**
that parses a multi-scenario document and emits N single-scenario
`Feature` objects. This is the central piece of work; everything else
(upload plumbing, naming, UI) is secondary.

## 3. Current state (grounded)

- **Model** is single-scenario:
  `Feature{description, tags, background, scenario, enums}` with exactly one
  `Scenario`
  (`@/Users/hoang.tv/Documents/Projects/tms/app/models/_feature.py:159-199`,
  `:108-142`). `description` is the assembled `Feature:` name + body; tags
  are feature-level; `Background` is optional/shared.
- **Parser internals reusable for a splitter:** `_build_scenario`
  (`gherkin_io.py:313-331`), `_assemble_description`, `_extract_steps`,
  `_extract_enum_directives`, and the child walk (`_split_children`,
  `:222-259`). A splitter can collect *all* scenario children instead of
  rejecting the second.
- **Write paths** all funnel through validation + the project enum
  cross-check:
  - `create_file(parts, description, *, scenario_name)` writes a
    placeholder-scenario file
    (`@/Users/hoang.tv/Documents/Projects/tms/app/storage/_features.py:40-81`).
  - `write_feature(parts, feature)` serialises a full `Feature`; **requires
    the file to already exist**
    (`@/Users/hoang.tv/Documents/Projects/tms/app/storage/_features.py:83-105`).
  - **Enum cross-check** rejects saves whose `enums` don't resolve in
    `<project>/enums.yaml` — unknown kind, unknown key, or *missing*
    `enums.yaml` → `ValidationError`
    (`@/Users/hoang.tv/Documents/Projects/tms/app/storage/_enums.py:509-551`).
  - **Tags are free-form** (char rules only, no vocab) — imported tags
    never fail a cross-check
    (`@/Users/hoang.tv/Documents/Projects/tms/app/models/_feature.py:207-221`).
- **Naming rules:** leaf must end `.feature` (auto-appended)
  (`_normalize_filename`, `_core.py:124-139`); segments reject
  `/ \ : * ? " < > |` + control chars and `.`/`..`
  (`_validate_segment` `:301-311`, `_FORBIDDEN_CHARS` `:32-34`).
- **Create API:** `POST /api/files {parent, file_name, scenario_name?,
  description?}`; `parent` must be 2..`MAX_FOLDER_DEPTH` segments
  (`@/Users/hoang.tv/Documents/Projects/tms/app/server/routes_files.py:20-50`).
- **Create UI:** `tmsCreateFile(parent)` opens a modal and `POST`s JSON; no
  file input anywhere (`03_folder_actions.js:184-278`). Buttons sit beside
  "+ Create test case" in `folder_module.html:26` and
  `folder_subfolder.html:27`.
- **No multipart / file-upload path exists anywhere in the app** — import
  introduces the first one. `tmsSlugifyForFilename` already exists for
  deriving filenames (`04_run_create.js:50`).

## 4. Proposed approach (phased)

### Phase 1 — the splitter (pure, no I/O) — _the risky core_

Add to `gherkin_io.py` a pure function:

```
split_feature_source(source: str) -> list[Feature]
```

- Parse once with the official `Parser` (same as `parse_feature`).
- Reject `Rule:` blocks with the **same** `GherkinParseError` as today.
- Collect **every** scenario child (refactor `_split_children` into a
  shared `_collect_children -> (background, [scenario_ast])`;
  `parse_feature` keeps its "exactly one" enforcement by calling the
  collector and rejecting `len > 1` — preserving its current error/loc).
- For each scenario, build a `Feature` that **shares** the file's
  `description` (blank if the source has none), feature-level `tags`, and
  `background`, paired with that one `Scenario` (reuse `_build_scenario`,
  so outlines + examples + data tables + step DataTables survive). Each
  case keeps **its own** scenario-level `tags` (see §5 IM-2 note).
- **`enums` is always emptied** on the produced `Feature`s (IM-2 → drop).
- **Missing `Feature:` header (IM-A):** synthesize one. A deterministic
  pre-scan (skip blank / `#` comment / `@tag` lines; is the first
  significant line a `Feature:`?) decides; if absent, prepend `Feature:\n`
  and parse → every case shares a **blank** description. _Verified
  Jun 13, 2026: a headerless `Scenario:` source **raises**
  `CompositeParserException` (does not return `feature=None`), and
  prepending `Feature:\n` parses cleanly to `name=''`, `description=''`
  with the scenario children intact._ The pre-scan (not a blanket
  exception-catch) avoids masking genuine syntax errors elsewhere.
- **Zero scenario blocks** (a header but no `Scenario:`) → return `[]`;
  the caller turns that into a "no scenarios to import" content error.

Unit-testable with zero storage — pin it hard first (this is where the
logic risk lives).

### Phase 2 — storage import (pre-flight, then write; all-or-nothing)

Add `Storage.import_feature_cases(parent_segments, items: list[(file_name,
Feature)]) -> None` where each `file_name` is **user-supplied** (IM-3/IM-5):

1. **Pre-flight, no writes** — validate, collecting **every blocking
   reason** (case-insensitive name checks) so the user fixes them in one
   pass (IM-4; collect-all signed off Jun 13, 2026), raised as
   `ImportValidationError(reasons=[...])`:
   - parent folder exists + depth `2..MAX_FOLDER_DEPTH`; not a reserved
     typed area (`_reject_reserved_typed_area`, IM-H).
   - each `file_name` normalises (`_normalize_filename`) + passes
     `_validate_segment`.
   - **per-scenario content rules:** scenario `name` non-empty (required),
     scenario `steps` non-empty (required); description/Background optional.
   - **1-level-folder-scope uniqueness** (IM-C/D): within the destination
     folder's **direct children only** (non-recursive) — no two imported
     `file_name`s collide; no two imported **scenario names** collide; and
     neither collides with an **existing** direct-child case's file name /
     scenario name. (Reads the folder's direct `.feature` children +
     their scenario names; the post-tech-04 listing already surfaces
     scenario names.)
   - `validate_feature` (serializer invariants) on each `Feature`.
2. Any blocking error → **abort with zero writes** + a clear message.
3. Otherwise write each case. Needs a create-from-`Feature` primitive:
   today `create_file` writes only a placeholder and `write_feature`
   demands an existing file — add `create_feature_file(parts, feature)`
   (create + serialise a full `Feature` in one shot, name-conflict guarded).

Write phase is **all-or-nothing**: cases are written one by one and, if any
write raises mid-batch, the already-written files are deleted (compensating
rollback, signed off Jun 13, 2026). Residual (IM-E): a hard crash *between*
the rollback's deletes can still leave a partial batch — no WAL — matching
the single-file write guarantee. Scenario-name uniqueness is enforced at
pre-flight only (best-effort vs. a concurrent writer) and is **case-
insensitive**, mirroring the file-name rule (G7).

### Phase 3 — API (text body, no multipart)

- **Preview:** `POST /api/files/import/preview` `{source}` → splits and
  returns per-scenario metadata `[{scenario_name, step_count,
  scenario_tags}]` + feature-level `{description, tags}` +
  `enums_present: bool` (so the UI can warn that enums will be dropped) +
  any parse error (line/col). **No writes.**
- **Commit:** `POST /api/files/import` `{project, parent, source, names:
  [...]}` — re-splits server-side (deterministic) and calls
  `import_feature_cases`. The browser reads the file with `FileReader` and
  sends its **text** (mirrors the existing `PUT /files/<p>/raw` text
  pattern — **no multipart introduced**). Enforce the **3 MB** cap
  (IM-F) server-side; reject larger with a clear error.
- Returns the created paths on success; a single blocking reason on abort.

### Phase 4 — UI (import modal with project + folder pickers + per-scenario names)

- A global **"Import test cases"** button in the **top bar** (`base.html`
  header, beside the app title) — `tmsImportFile()` with no argument
  (USER request Jun 13, 2026; moved out of the per-folder views).
- Modal flow (IM-5, USER request):
  1. **Project** selector + **destination folder** selector + a `.feature`
     **file picker** (client rejects non-`.feature` / > 3 MB; the picker
     button is given an outstanding border so it stands out). Because the
     project is chosen separately, the destination selector lists folders
     **relative to the chosen project** (module level and below); the full
     path stays the option value for the commit call.
  2. On file chosen → call the **preview** endpoint; render a bordered
     **per-scenario table** (USER request) with columns **Scenario name**
     (truncated to 30 chars + `…`, full name on hover), **Feature tag**
     (shared; top 2 `@`-prefixed + `+N more`), **Scenario tag** (same
     format), and **File name** — an input the user fills per scenario,
     **placeholder `file name`, no pre-filled value** (USER request). The
     modal uses the wider **`xl`** size. If `enums_present`, show a
     **"enums will be dropped" confirmation** the user must acknowledge
     before Confirm (IM-2).
  3. **Confirm** is gated on a chosen folder + every scenario having a
     non-empty filename (+ enum ack when relevant); posts to the commit
     endpoint. On success, refresh the destination folder + tree panes; on
     abort, render the server's blocking reasons as a list.
- The project + destination-folder pickers are built from `/api/tree`.

## 5. Decisions (resolved Jun 13, 2026)

- **IM-1 — One file per import.** Single `.feature` upload for v1;
  multi-file / zip / folder batch is a **future enhancement** (§8).
- **IM-2 — Drop all enums; keep tags.** Imported `# enum.<kind>: <key>`
  directives are **dropped** (sidesteps the project-vocab cross-check and
  the undefined per-scenario enum association). The UI **asks the user to
  confirm** enums will be dropped before importing when any are present.
  **Feature-level tags are shared** onto every split case; **each scenario
  keeps its own scenario-level tags.** _(Engineering note: the USER's
  "share … scenario tag" is read as "each case carries its scenario's own
  tags" — gherkin has no notion of one scenario's tags belonging to
  another. Flagged for confirmation.)_
- **IM-3 — User names each file.** After a successful read + split, the
  modal lists the scenarios and the user **types a filename for each**
  (pre-filled with an editable slug suggestion). No silent auto-naming.
- **IM-4 — All-or-nothing.** Any pre-flight failure aborts the whole
  import with **no writes**; the UI shows the user the blocking reason.
- **IM-5 — Mandatory preview.** The modal **must** preview the N scenarios
  with per-scenario filename inputs before committing.
- **IM-6 — Feature spec.** This is a product **feature** spec
  (`specs/features/14-…`), not a `tech-*` enhancement. Confirmed.

## 6. Validation rules (resolved)

- **Scope:** all uniqueness/name validation is scoped to the **destination
  folder's direct children (1 level, non-recursive)** — file names and
  scenario names (USER request).
- **Source `.feature` file:** feature description **optional** (blank if
  absent); scenario name **required**; scenario steps **required**;
  `Background` **optional**; feature + scenario tags **allowed**; enums
  **dropped**. `Rule:` blocks rejected (model invariant).
- **Split cases share:** the source feature `description` (or blank),
  the `Background` steps (IM-G, approved), and feature-level tags; each
  keeps its own scenario tags.
- **Duplicate scenario name → rejected** (case-insensitive), in **either**
  direction: two or more scenarios in the **source file** sharing a name,
  **or** a split scenario name colliding with an **existing** direct-child
  case's scenario name in the destination folder.
- **Duplicate file name → rejected** (case-insensitive): two imported file
  names colliding within the batch, or with an existing direct child.
- **Blocking errors surfaced to the user (examples):** missing scenario
  name; scenario with no steps; duplicate scenario name (in-source or
  in-scope); duplicate / conflicting file name; bad file type; > 3 MB;
  parse error (with line/col); no scenarios found. All reasons are
  **collected** and shown together (collect-all).

## 7. Assumptions / blindspots (self-critique)

- **IM-A (resolved: synthesize a blank Feature when the header is
  missing).** Per the USER: a source lacking a `Feature:` header still
  imports — the split cases get a **blank** shared description. Mechanism
  (verified Jun 13, 2026): the bare parser **raises** on a headerless
  `Scenario:` file, and prepending `Feature:\n` parses cleanly to an
  empty name/description with the scenarios intact — so the splitter
  pre-scans for a header and, if absent, parses a `Feature:\n`-prefixed
  copy. A header-present file with no `Scenario:` is still a
  "no scenarios" content error.
- **IM-A2 (parser regression risk).** The highest-risk *code* change is
  refactoring `_split_children` — feature-01 smokes assert the exact
  `Rule:` / multi-scenario error messages **and line/column**; the refactor
  must keep `parse_feature` byte-identical (rebuild it on top of
  `_collect_children`; re-run feature-01 first).
- **IM-B (enum-comment association).** Enum directives are file-level
  comments with no per-scenario binding in the AST — another reason IM-2
  drops them rather than guessing ownership.
- **IM-C/D (empty / duplicate scenario names).** Resolved by §6: empty
  scenario name and duplicate-in-scope are **blocking** pre-flight errors
  (all-or-nothing), not silently slugged.
- **IM-E (no transaction primitive).** Approved: pre-flight validation
  shrinks the failure window to crash-only; no WAL.
- **IM-F (size).** 1 file per upload, **3 MB** hard cap, enforced
  client + server with a clear message.
- **IM-G (`Background` duplication).** Approved: every split case copies
  the shared Background steps.
- **IM-H (reserved typed area).** Import reuses
  `_reject_reserved_typed_area` so cases cannot land under `test-run`.

## 8. PDCA plan (after go-ahead)

1. **DO-1 (Plan-critical, pure) — DONE Jun 13, 2026.**
   `split_feature_source` + the `_collect_children` refactor (enums emptied;
   tags per §5). `parse_feature` rebuilt on top of `_collect_children`,
   preserving its exactly-one enforcement (raises at the **second** scenario
   location). Header synthesis via a deterministic pre-scan
   (`_ensure_feature_header`) that skips blank/`#`/`@tag` lines, with parse
   line-offset correction. **CHECK (done):** feature-01 re-run green;
   `F14_01_splitter.py` covers 1 scenario, N scenarios, outline, shared
   Background (deep-copy independence), shared description / blank-on-synthesis,
   feature-tags-shared + scenario-tags-kept, `Rule:` rejected, header
   synthesis, header-but-no-`Scenario:`→`[]`, enums-dropped, genuine-syntax-
   error-not-masked, empty/comment-only→`[]`, CRLF. Full suite 283/283.
2. **DO-2 (storage) — DONE Jun 13, 2026.** `create_feature_file` +
   `import_feature_cases` (`app/storage/_features.py`) with the §4 Phase 2
   pre-flight. **Decisions (USER-approved):** (a) compensating-delete on
   mid-loop failure → true all-or-nothing; (b) **case-insensitive**
   scenario-name uniqueness (matches file-name G7); (c) **collect-all**
   blocking reasons via `ImportValidationError(reasons=[...])`. **CHECK
   (done):** `F14_02_import_storage.py` covers happy multi-write (shared
   desc/Background/feature-tags + per-case scenario tags, order), enums-
   dropped persisted + bypasses cross-check, blank description + `.feature`
   auto-append, name+steps required (collected), case-insensitive file +
   scenario conflicts (on-disk & within-batch) leaving **zero** files,
   forbidden-char rejection, depth-1 + reserved-area rejection, and
   compensating rollback on mid-write failure. Full suite 284/284.
3. **DO-3 (API) — DONE Jun 13, 2026.** `POST /api/files/import/preview`
   (`{source}` → shared `description`/`tags`, `enums_present`, per-scenario
   `{scenario_name, step_count, scenario_tags}`) + `POST /api/files/import`
   (`{parent, source, names, project?}`). 3 MB cap (UTF-8 bytes) on **both**;
   commit validates `len(names) == len(scenarios)` and optional `project`
   consistency with `parent[0]`; `ImportValidationError` → 422
   `import_validation_error {reasons}`. (Note: "invalid file type" is a
   client-side gate — DO-4; non-Gherkin content surfaces as `parse_error`.)
   **CHECK (done):** `F14_03_import_api.py` covers preview metadata +
   `enums_present`, preview parse error (line/col), preview zero-scenarios,
   > 3 MB on both, commit happy (created paths + on-disk), names mismatch,
   project/parent mismatch, in-scope conflict abort (reasons), no-scenario
   content error. Full suite 285/285.
4. **DO-4 (UI) — DONE Jun 13, 2026.** Global `Import test cases` button in
   the **top bar** (`base.html`) → `tmsImportFile()` modal (moved out of the
   folder views per USER). Modal: project selector + destination-folder
   selector (built from `/api/tree`, folders shown **relative to the chosen
   project**), `.feature` file picker (outstanding border style) with
   client-side type + 3 MB gating, dry-run preview, per-scenario read-only
   name + editable filename input (slug-prefilled), enum-drop
   acknowledgement gate, Confirm gated on a chosen folder + every filename
   filled + enum ack; server `import_validation_error` reasons rendered as a
   list; success refreshes the destination folder + tree. **CHECK (done):**
   `F14_04_import_ui.py` (top-bar button, removed-from-folder-views,
   relative folder display, styled picker, preview/commit wiring, gating,
   reasons). Manual walkthrough pending USER. Full suite 286/286.
5. **ACT:** `DONE.md`, `feature-14/COVERAGE.md`, clear the backlog item,
   mark this spec shipped.

## 9. Out of scope (v1)

- Non-`.feature` formats (CSV/Excel/etc.).
- Multi-file / folder / zip upload (IM-1 → future enhancement; the
  splitter + result shape leave room).
- First-class **`Examples:`-level tag** support (see the VERY IMPORTANT
  NOTE at the top): only feature + scenario tags are surfaced; Examples
  tags survive file round-trip but are not a supported tag concept yet.
- Mapping imported enum directives onto the project vocab (IM-2 drops them).
- Editing scenarios during import (verbatim split; edit afterward in the
  file editor).
