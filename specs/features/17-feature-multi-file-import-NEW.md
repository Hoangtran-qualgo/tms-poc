# 17 · Import test cases from multiple `.feature` files

_**SHIPPED Aug 17, 2026.** Extends feature 14's one-file import without
changing the splitter, case model, or storage transaction. Feature-17 smokes
pass 2/2; feature-14 compatibility smokes pass 4/4. Full-suite check: 315/321
pass; the six failures are pre-existing watcher acceptance paths that cannot
start watchdog's fsevents stream in this environment._

## Goal

Allow the user to select multiple `.feature` files in one import operation.
Every source is split into the existing one-scenario-per-case model, and all
created cases go into one selected module or branch folder.

## Current evidence

- Feature 14 intentionally accepts one `source` string at
  `POST /api/files/import/preview` and `POST /api/files/import`; its modal
  reads only `fileInput.files[0]`.
- `split_feature_source(source)` is pure and already produces a separate
  single-scenario `Feature` value for every scenario in one source.
- `Storage.import_feature_cases(parent, items)` already accepts a flat list of
  `(file_name, Feature)` pairs. Its one pre-flight detects file-name and
  scenario-name conflicts across the full list, case-insensitively, and its
  write phase compensates any partial write.
- The investigation spike proves that pairs formed from two different sources
  use this existing transaction unchanged; a duplicate scenario across the
  sources aborts before any file is created.

## Confirmed minimum approach

Keep the current text-in-JSON transport, splitter, case model, and storage
transaction. Extend the two existing import endpoints so the UI submits an
ordered `sources` array, where each entry carries the browser file name for
display/error context and its text for server-side parsing. The server:

1. validates the batch limit;
2. parses every source with `split_feature_source`;
3. flattens scenarios in source order then scenario order;
4. passes one combined list with the user-entered output names to
   `Storage.import_feature_cases`; and
5. returns paths only after the whole batch succeeds.

A batch permits at most **20 files** and **3 MB total** when source strings
are encoded as UTF-8. Reaching either limit rejects the request. The shipped
one-file `{source}` request remains a supported one-element batch so existing
clients keep their current preview/error shape. The multi-file UI uses the new
`sources` body.

For a multi-file request, the batch preview response is
`{scenarios, errors, enums_present, enum_sources}`. Each scenario carries its
`source_index`, `source_name`, feature/scenario tags, name, and step count;
each error carries its source context plus type/parse/content details. Source
names ending outside `.feature`, Gherkin parse errors, and sources containing
no scenarios are collected together. Commit repeats this work and turns any
such error into an all-or-nothing `import_validation_error` before storage is
called.

The import modal changes its existing picker to `multiple`, retains the one
project and destination-folder selection, and renders a **Source file** column
beside the existing scenario/tag/file-name columns. A source's browser name is
display-only: the source-array index defines deterministic association even
when two selected files share the same leaf name.

This deliberately does **not** add multipart upload, an archive format, a new
parser, a new storage transaction, or a separate destination per source.
Feature 20 later adds client-only folder-sequence filename prefill; it does not
alter the batch request or storage transaction.

## Confirmed rules / remaining blindspot

1. **Atomicity:** A malformed/invalid source blocks the whole selected batch;
   no cases are created. This extends feature 14's all-or-nothing rule.
2. **Limit:** At most 20 selected files and 3 MB total UTF-8 source text. Both
   limits apply; client and server enforce them.
3. **Preview errors:** Preview collects source-specific type/parse/content
   errors and disables Import until none remain. The commit independently
   re-parses and revalidates the complete batch before storage writes.
4. **API compatibility:** Existing one-file `{source}` preview/commit bodies
   retain their shipped behaviour. The new multi-file UI sends `{sources}`.
5. **Enum acknowledgement:** One acknowledgement covers all source files with
   enum directives, and the modal names those files.
6. **Blindspot accepted:** Source names are untrusted display labels and may
   duplicate; their array index, not their name, associates preview rows with
   source text. Output-case names remain validated by storage.

## PDCA result

1. **Plan — done:** locked the batch rules, source-array schema, and
   acceptance cases.
2. **Do — API — done:** `routes_files.py` accepts `{sources: [{name,
   source}, ...]}`, validates 20 files / 3 MB total, labels/collects source
   errors, flattens valid features, then calls the existing storage importer
   once. Legacy `{source}` branches preserve their shipped responses.
3. **Check — API — done:** `F17_01_import_api.py` covers ordering, source
   context, collected errors, both limits, atomic batch commit, cross-source
   conflict, commit revalidation, and legacy compatibility.
4. **Do — UI — done:** `tmsImportFile()` uses a multi-file picker, client
   limits, all-settled file reads, source-file preview rows, collected-error
   confirmation gating, a multi-source enum acknowledgement, and one commit.
5. **Check — UI — done:** `F17_02_import_ui.py` covers the picker, limits,
   request wiring, source/error UI, and acknowledgement gate. Feature-14
   smokes remain green.
6. **Act — done:** backlog moved to `DONE.md`, temporary plan deleted,
   summary updated, and coverage recorded.

## Acceptance criteria after decisions are locked

- A selection of two or more valid `.feature` sources previews every scenario
  in deterministic source/scenario order and lets the user name each output
  case.
- A successful commit creates all named cases in the one selected destination
  and refreshes that folder plus the directory tree once.
- Filename and scenario-name validation considers every selected source and
  existing direct-child case in the destination, case-insensitively.
- Failure semantics, type/size limits, preview error presentation, legacy API
  support, and multi-source enum acknowledgement follow the rules above.

## Affects

- `app/server/routes_files.py` — the preview/commit request normalizer must
  accept the confirmed batch schema and flatten parsed scenarios.
- `app/static/03_folder_actions.js` — the existing import modal must select,
  read, preview, label, and commit multiple browser files.
- `.smoke-scratch/feature-17/` — new standalone API and UI checks must lock
  the confirmed batch semantics while feature-14 smokes preserve one-file
  compatibility.
- `specs/features/14-feature-import-test-cases-NEW.md` — remains the source
  of one-file invariants reused here; this spec records the additive batch
  behaviour.

## Depends on

- Feature 14's one-scenario-per-case splitter and editable output-name rule
  (feature 20 supplies the default values),
  case-insensitive direct-folder uniqueness, enum-drop policy, and
  all-or-nothing storage transaction.
- `Storage.import_feature_cases()` accepting one flat batch regardless of its
  sources, as proven by the investigation spike.
- The existing JSON text transport and browser `File.text()` support; no
  multipart parser or archive extractor is introduced.

## Surface for follow-up

- A normalized ordered-source request can later support a zip/archive import
  without changing the splitter or storage transaction, if that is requested.
- Explicit batch bounds and per-source errors form the security/usability
  baseline for any later non-`.feature` import format.
- Project-wide scenario-name uniqueness remains a separate backlog decision;
  this feature preserves the current destination-folder scope.
