# feature-15 · Import test run — coverage matrix

Smoke coverage against
`specs/features/15-feature-import-test-run-NEW.md` (shipped Jun 15, 2026).

## Method

- Spec source: `specs/features/15-feature-import-test-run-NEW.md`
  (decisions IR-1..IR-6; phased PDCA DO-1..DO-5 + ACT).
- Smokes follow the standalone pattern in `.smoke-scratch/README.md`:
  pure-function checks (Allure parser), `Storage` checks against a temp data
  root (write path + resolver), Flask `test_client` HTTP checks (API), and
  HTML render-marker + concatenated-JS source-inspection checks (UI).
- `Status`: `covered`, `render` (HTML marker), `source` (JS wiring).

## Matrix

| Spec area | Smoke | Status |
| --- | --- | --- |
| DO-1: decode the real single-file sample → `report_name`, `created_at` from `summary.time.start` (report-derived, deterministic, not server-now), 9 distinct PASSED scenarios | `F15_01_parser` | covered |
| DO-1 / IR-2: nested `data/suites.json` (epic→feature→story) flattens depth-agnostically to its leaves | `F15_01_parser` | covered |
| DO-1: non-Allure / malformed / `suites`-less input raises `ValueError` (→ 400 `bad_request`) | `F15_01_parser` | covered |
| DO-1 / IR-3: Allure status → `RUN_RESULTS` (`broken`→FAILED, `unknown`→SKIPPED, unrecognised→SKIPPED) | `F15_02_status_map_and_retries` | covered |
| DO-1 / IR-5b: same-name retries collapse to the final run (latest `time.stop`), case-insensitive, order-independent | `F15_02_status_map_and_retries` | covered |
| DO-3: `resolve_scenarios` matched (case-insensitive single hit) | `F15_03_resolver` | covered |
| DO-3 / IR-5: unmatched (0 hits) + ambiguous (2+ hits) classification, input order preserved; project with no folder → all unmatched | `F15_03_resolver` | covered |
| DO-1+DO-3: parser-collapsed retries resolve to one path (no duplicate-`file_path` abort) | `F15_03_resolver` | covered |
| DO-2: `import_test_run` preserves the report `created_at` (not server-now) + per-case results in order | `F15_04_import_storage` | covered |
| DO-2: duplicate `file_path` rejected by `validate_run`; nothing written | `F15_04_import_storage` | covered |
| DO-2: `NameConflictError` on existing file; `FileNotFoundError` on missing group | `F15_04_import_storage` | covered |
| DO-4: `POST /api/runs/import/preview` all-matched → report name + `created_at` + rows + counts + empty errors | `F15_05_import_api` | covered |
| DO-4: preview flags unmatched/ambiguous with counts + per-line `errors` (`<no>.<name> : … - <reason>`) | `F15_05_import_api` | covered |
| DO-4: preview of non-Allure report → 400 `bad_request`; report > 30 MB → 400 | `F15_05_import_api` | covered |
| DO-4: commit all-matched → 201, run written with report `created_at` + one result per scenario | `F15_05_import_api` | covered |
| DO-4: **retention** — after a successful commit no `.html` is written anywhere under the data root (only the run `.yaml`) | `F15_05_import_api` | covered |
| DO-4 / IR-5: commit with unmatched/ambiguous → 422 `import_validation_error {reasons}`, nothing written; zero scenarios → 422; > 30 MB → 400 | `F15_05_import_api` | covered |
| DO-5: top-bar `Import test run` button beside `Import test cases`, wired to `tmsImportRun()` | `F15_06_import_ui` | render |
| DO-5: `tmsImportRun()` no-arg launcher; destination from `/api/run-groups`, `project\|group` options, **no "+ create group" row** (IR-6) | `F15_06_import_ui` | source |
| DO-5: preview + commit wired via **raw `fetch`** (not `tmsApiPost`) to preserve `details.reasons` | `F15_06_import_ui` | source |
| DO-5: preview table `#`/`Scenario`/`Result`/`Matched case`; client gates `.html` type + 30 MB | `F15_06_import_ui` | source |
| DO-5: Confirm gated on zero blocking errors; server reasons surfaced; success clears the report + opens the new run by default | `F15_06_import_ui` | source |

## Notes

- **Decisions (Jun 15, 2026):** IR-1 (Allure 2 single-file only), IR-2 (flatten
  `data/suites.json` leaves), IR-3 (status map: `broken`→FAILED,
  `unknown`→SKIPPED), IR-4 (`created_at` from `summary.time.start`, earliest-leaf
  fallback), IR-5 (all-or-nothing; unmatched + project-ambiguous abort with
  per-line errors), IR-5b (retries collapse to final by `time.stop`), IR-6 (no
  "+ create group" row — pick an existing group only).
- **The report is transient:** the uploaded HTML is parsed **in-memory** and
  **never persisted** — only the run `.yaml` is written. `F15_05` asserts zero
  `.html` under the data root after a successful commit; the UI also clears the
  file input + cached html on success.
- **Scenario match is case-insensitive and whole-project** (explicitly
  *temporary* per IR-5) — see the open `IN-PROGRESS.md` Must-have on a
  project-level scenario-name uniqueness rule.
- **No multipart:** the browser reads the report with `file.text()` and POSTs
  its **text** (mirrors feature-14); the 30 MB cap is enforced **client +
  server**.
- **UI smokes** inspect the concatenated `app/static/*.js` (sorted, body scoped
  to the `tmsImportRun` function) plus `test_client` HTML renders; there is no
  headless-browser step. `tmsImportRun` lives in `04_run_create.js` (appended,
  no new script tag).
- Full suite at sign-off: **295/295 PASS / 0 FAIL** (was 289; +6 feature-15).
