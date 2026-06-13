# feature-14 · Import test cases — coverage matrix

Smoke coverage against
`specs/features/14-feature-import-test-cases-NEW.md` (shipped Jun 13, 2026).

## Method

- Spec source: `specs/features/14-feature-import-test-cases-NEW.md`
  (decisions IM-1..H + the three DO-2 decisions; phased PDCA DO-1..DO-4).
- Smokes follow the standalone pattern in `.smoke-scratch/README.md`:
  pure-function checks (splitter), `Storage` checks against a temp data
  root, Flask `test_client` HTTP checks (API), and HTML render-marker +
  concatenated-JS source-inspection checks (UI).
- `Status`: `covered`, `render` (HTML marker), `source` (JS wiring).

## Matrix

| Spec area | Smoke | Status |
| --- | --- | --- |
| DO-1: `split_feature_source` yields one `Feature` per scenario, document order | `F14_01_splitter` | covered |
| DO-1: shared feature description + tags + `Background` (independent copies) onto each case; scenario tags kept per-case | `F14_01_splitter` | covered |
| DO-1: Scenario Outline kind + Examples survive the split | `F14_01_splitter` | covered |
| DO-1 / IM-A: missing `Feature:` header synthesized (blank description); leading comments/tags skipped in pre-scan | `F14_01_splitter` | covered |
| DO-1: `Rule:` block raises `GherkinParseError`; genuine syntax errors not masked; header-only → `[]`; empty/comment-only → `[]`; CRLF normalised | `F14_01_splitter` | covered |
| DO-1 / IM-2: enum directives always dropped from split cases | `F14_01_splitter` | covered |
| DO-2: `import_feature_cases` happy multi-write persists shared desc/Background/tags + per-case scenario tags, names, order | `F14_02_import_storage` | covered |
| DO-2 / IM-2: dropped enums persist (no directive written) and bypass the project-vocab cross-check | `F14_02_import_storage` | covered |
| DO-2: blank description allowed; `.feature` auto-appended | `F14_02_import_storage` | covered |
| §6: scenario name + steps required (collected together), zero files written | `F14_02_import_storage` | covered |
| §6: duplicate **file name** rejected (case-insensitive) — vs existing + within-batch | `F14_02_import_storage` | covered |
| §6: duplicate **scenario name** rejected (case-insensitive) — vs existing, within-batch, and two same-named scenarios in one source file (C4b) | `F14_02_import_storage` | covered |
| §6: forbidden-char file name; depth-1 + reserved typed-area destination rejected | `F14_02_import_storage` | covered |
| DO-2 decision: all-or-nothing — mid-write failure rolls back already-written files | `F14_02_import_storage` | covered |
| DO-3: `POST /api/files/import/preview` → shared header + per-scenario metadata in order; `enums_present` flag | `F14_03_import_api` | covered |
| DO-3: preview parse error → 422 `parse_error` with line/column; zero-scenarios → empty list; > 3 MB → 400 | `F14_03_import_api` | covered |
| DO-3: commit happy → 201 created paths + files on disk | `F14_03_import_api` | covered |
| DO-3: commit rejects names/scenarios length mismatch (400) + project≠parent[0] (400) + > 3 MB (400) | `F14_03_import_api` | covered |
| DO-3 / IM-4: commit in-scope conflict → 422 `import_validation_error {reasons}`; no scenarios → 422 | `F14_03_import_api` | covered |
| DO-4: global `Import test cases` button in the top bar; removed from folder views | `F14_04_import_ui` | render |
| DO-4: `tmsImportFile()` no-arg launcher; project + destination picker from `/api/tree`, folders shown relative to project | `F14_04_import_ui` | source |
| DO-4: preview + commit endpoints wired; client gates file type + 3 MB; styled file picker | `F14_04_import_ui` | source |
| DO-4: bordered preview table (Scenario name 30-char truncate · Feature tag · Scenario tag top-2 `@`+N-more · File name) with placeholder-only filename inputs; `xl` modal | `F14_04_import_ui` | source |
| DO-4: enum-drop ack + filename completeness gate Confirm; success refreshes folder + tree; server reasons surfaced | `F14_04_import_ui` | source |

## Notes

- **Decisions (Jun 13, 2026):** IM-1 (one file/import), IM-2 (drop enums,
  keep tags), IM-3 (user names each file), IM-4 (all-or-nothing), IM-5
  (mandatory preview), plus DO-2 decisions: compensating-delete rollback,
  case-insensitive scenario-name uniqueness, collect-all
  `ImportValidationError`.
- **No multipart:** the browser reads the file with `FileReader` and POSTs
  its **text** (mirrors `PUT /files/<p>/raw`); the 3 MB cap is enforced
  **client + server**.
- **"Invalid file type"** is a client-side gate (`.feature` only); non-Gherkin
  text content surfaces server-side as `parse_error`.
- **Examples-level tags** are out of scope (see the VERY IMPORTANT NOTE at the
  top of the spec): only feature + scenario tags are surfaced; Examples tags
  round-trip verbatim but are not a first-class tag concept.
- **UI smokes** inspect the concatenated `app/static/*.js` (sorted) plus
  `test_client` HTML renders; there is no headless-browser step.
- Full suite at sign-off: **286/286 PASS / 0 FAIL** (was 282; +4 feature-14).
