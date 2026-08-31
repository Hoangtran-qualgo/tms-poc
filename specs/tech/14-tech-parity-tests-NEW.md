# 14 · Migration parity tests — implementation guide

## Goal

Prove that each TypeScript slice behaves identically to the documented Python
baseline, except for an explicitly approved migration exception. A passing
TypeScript-only test is insufficient: every important test has a Python
oracle, an equivalent fixture, or both.

This is a local development and comparison plan. It does not propose CI/CD.

## Test source and limits

The current suite under `.smoke-scratch/` consists of standalone Python
scripts. It covers many storage and HTTP behaviours, but it is not a browser
harness: some UI tests inspect rendered HTML or JavaScript source. Reuse its
fixtures and assertions as evidence, not as an instruction to mechanically
translate every script.

Known examples:

- Raw-save behaviour: `feature-05/F05_08_raw_roundtrip.py`.
- Watcher/SSE source semantics: `feature-03/F03_01_event_filtering.py` through
  `F03_06_acceptance.py`.
- Run timestamp creation and unchanged-value round-trip:
  `feature-10/F10_46_created_at_stamp.py`.
- Report immutable fields: `feature-12/F12_23_patch_runs_and_immutability.py`.
- Allure API preview/commit: `feature-15/F15_05_import_api.py`.
- Rename cascade/rollback: `feature-21/F21_01_storage_cascade.py`.
- `/ui` browser-navigation negotiation: `tech-10/T10_01_negotiation.py`.

Full runtime workflow coverage is not proven by the current suite. The
Chromium shell/deep-link smoke is verified. The TypeScript watcher was also
manually checked against a production Next server: an external nested file
created after the SSE connection emitted `event: change`. Python FSEvents
delivery is outside this TypeScript workability check.

## Selected test tooling and current verification status

| Layer | Selected tool | Current status |
| --- | --- | --- |
| Domain, storage, and HTTP-contract tests | Vitest `4.1.11` | Temporary Node 24.19.0 CLI verification passed. |
| React component tests | React Testing Library `16.3.2` | Temporary Node 24.19.0 module-import verification passed. |
| Browser workflow tests | Playwright Test `1.62.1` | `js/playwright.config.ts` has fifteen workspace smoke tests; all fifteen pass in the latest production-server Chromium run. |

Playwright is selected because it supplies the TypeScript test runner and
browser automation needed for the contract's deep-link, dialog, draft, and
external-change workflows. The browser script builds the app and starts a
local production Next server; Chromium is installed in the local Playwright
cache for repeatable workspace checks.

The current TypeScript workspace has a Vitest suite covering the implemented
domain/API slices (62 tests across 28 files at the latest check): tree/folder
listings and counts, feature structured/raw writes, legacy and batch import preflight,
enum mutations, run lifecycle and timestamp protection, Allure preview/commit,
report CRUD and live view aggregation, relocation guards/cascades, SSE framing,
and representative Python↔TypeScript feature-model, tree/folder route,
feature-write, run-write, report-write, enum-write, Allure-import, fresh-run,
relocation, legacy-import, batch-import, malformed-nested-payload error-contract,
and framework-default HTML error cases.
These are Node-side contract tests; they are not a substitute for the full
Python differential oracle used for API parity cases. The live watcher probe
is documented separately below and targets the TypeScript runtime directly.
Differential files run serially in Vitest because each Python fixture process
starts a filesystem watcher and concurrent FSEvents streams are not available
on this host.

Current blockers are explicit:

- The in-app browser inventory remains empty. The independent Playwright
  Chromium run verified `15 tests in 1 file`, including Allure preview/import,
  report computed-view editing, folder rename, raw-save/rename/move, and
  external-change UI handling, against the production Next server.
- No TypeScript watcher runtime blocker was observed in the production SSE
  probe. Python FSEvents verification is intentionally out of scope for this
  migration check.

## Differential test setup

For one test case:

1. Create a fixture data root containing only the folders/files relevant to
   the case.
2. Copy it to separate Python and TypeScript roots.
3. Run the same request or filesystem action against each implementation.
4. Compare the specified HTTP result, emitted SSE data where applicable, and
   final filesystem state.
5. Delete both temporary roots after the test.

Never run both implementations as writers against the same root. Current
locks, event buses, and recent-write state are process-local.

## Comparison rules

| Concern | Required comparison |
| --- | --- |
| Successful JSON endpoint | Exact status, content type, JSON field names/types, and documented order where source preserves it. |
| Structured errors | Exact status, `error.code`, details keys, and semantic message rule. Do not require incidental absolute filesystem text. |
| Default 404/405 | Status, HTML response class/content type, and absence of the JSON error envelope. Establish exact body expectations from a Python baseline test before asserting bytes. |
| HTML fragments/shell | Correct response mode for request headers plus observable screen state; markup need not be identical. |
| Raw feature write | Exact persisted bytes after LF normalization. |
| Canonical feature/YAML write | Parsed value plus serialized bytes when the Python serializer makes formatting part of current behaviour. |
| Create timestamp | Validate format and source (server clock or imported report); avoid comparing a live current-time value byte-for-byte. |
| Atomic failure/rollback | No partial target or stale reference remains after the stated failure. |
| SSE | Initial comment, `change` event framing, heartbeat, and suppression/debounce semantics. |

## Required test layers

### 1. Pure domain and persistence tests

Cover Gherkin parsing/splitting, structured serialization, raw-save mode,
path validation, maximum folder depth, filename rules, atomic writes,
malformed external files, enum cross-checks, YAML parse failures, and
reference cascades.

Include both ordinary and legacy/malformed fixtures. Listing/count behavior
must keep malformed or zero-scenario `.feature` files visible as one non-auto
case, and tag matching for `auto` is case-insensitive.

### 2. HTTP contract tests

For every row in `specs/tech/12-tech-python-api-contract-NEW.md`, test:

- a successful request;
- malformed body/type/required-field failure where the route accepts input;
- missing and duplicate resource behaviour when applicable;
- status, response body/media type, and filesystem result;
- retry/idempotence and all-or-nothing behaviour where documented.

Specifically retain malformed nested JSON routes that currently surface as
`500`, UI parse/domain `500` snippets, and framework-default HTML `404/405`.
Do not improve them inside a parity test.

### 3. Workflow and browser checks

Use a real browser or a documented manual local procedure for:

- direct URLs, refresh, Back/Forward, and `/ui` shell/fragment negotiation;
- sidebar state, recursive counts, folder sorting/filtering, and selection;
- create, rename, move, delete, import preview/commit, and retryable dialogs;
- structured/raw editor draft behaviour and external-change handling;
- run, report, enum, and import workflows;
- native unload confirmation.

The current source protects unload, Back/Forward, and several explicit editor
actions, but it does not prove a universal navigation veto. A global React
dirty-route blocker is a product change unless explicitly approved.

### 4. Live filesystem checks

Test the TypeScript path with a production Next server: connect to
`GET /api/events`, wait for `: connected`, create a nested file outside the
app, and verify one `event: change` frame. Also verify self-write suppression,
heartbeat behavior, and stream cleanup. This check targets Node's recursive
watcher; Python FSEvents delivery is not required for the TypeScript migration.

## Domain acceptance matrix

| Domain | Minimum parity cases |
| --- | --- |
| Tree and folders | Recursive tree, counts, reserved typed areas, malformed files, create/rename/delete, conflicts, idempotence. |
| Feature files | Create, structured save, raw save, unsupported suffix, duplicate/rename/move, enum directives, parse/validation errors. |
| Feature import | Legacy and batch forms, 20-file/3-MiB limits, preview errors, generated names supplied by client, no partial commit. |
| Enums | Initialization, vocabulary/kind-label writes, in-use refusal, key rename cascade, clear, malformed YAML. |
| Runs | Global project/group listing, group lifecycle, fresh-run creation, preview-gated Allure import, existing-group creation requirement, result/remark changes, draft add/remove case rows, reload/save, missing case tombstones, malformed YAML, timestamp rules. |
| Allure import | 30-MiB cap, malformed report, unmatched/ambiguous preview, no write on failed commit, report-derived timestamp. |
| Reports | Global project/report listing, ranking/inventory/trend rendering, each report type, live recomputation, data-source add/remove or scope edits, immutable `type`/`created_at`, malformed YAML, missing referenced inputs. |
| Relocation | Same-parent rename cascade, cross-folder move no-cascade behaviour, delete semantics, rollback after metadata-write failure. |
| UI/SSE | Header-dependent shell/fragments, global run/report/enum project selection, search scope/match/case/debounce behavior, empty/no-match states, single-hit navigation, error snippets, root-shell deep links (`tab`/`project`/`path` query state), legacy `/ui/*` adapter responses, drafts, external changes, SSE framing. |

## Approved-exception tests

The test suite must distinguish parity from the approved target exceptions:

- A TypeScript whole-run PATCH with changed `created_at` must be rejected and
  leave the existing run unchanged, even though current Python accepts it.
- TypeScript generic move, rename, and delete requests targeting typed areas
  must be rejected and leave storage unchanged, even though current Python is
  not consistently guarded.

Each exception test must identify the approval in
`specs/tech/13-tech-ts-api-parity-NEW.md`; it must not be reported as a Python
parity failure.

## Per-slice Plan → Do → Check → Act

1. **Plan:** name the contract rows, Python smoke evidence, fixture, expected
   HTTP/SSE/disk result, and exception status.
2. **Do:** implement the smallest complete TypeScript route/domain/UI slice.
3. **Check:** run Python and TypeScript against separate copied fixtures,
   compare results under the rules above, then perform any required browser or
   compatible-host check.
4. **Act:** record the result. Fix the implementation, add an approved
   exception, or stop for a human decision; do not silently relax the oracle.

## Exit criteria for a migrated slice

- Every included contract row has a success and relevant failure test.
- Persistent output and rollback behaviour compare correctly.
- Existing Python smokes relevant to the baseline remain understood and pass
  when used as the oracle; a historical `COVERAGE.md` claim alone is not proof.
- Browser-visible behavior is checked when the slice affects a workflow.
- Any difference is documented as an approved exception.

The current Playwright browser suite discovers fifteen checks, including direct
`/?tab=reports&project=Alpha` rehydration, legacy `/ui/file/...`, `/ui/run/...`,
and `/ui/report/...` deep links, bookmarked search hydration, dirty-editor tab
protection, create/import/filter/recursive-delete, run-edit/report-create, and
inline enum kind/entry/label flows, Allure preview/import, report computed-view
editing, folder rename, raw-save/rename/move, and external-change UI handlers.
Chromium execution passes for all fifteen checks. Broader cross-surface
workflows remain before cutover.

## Affects

- The existing `.smoke-scratch/` suite — supplies source evidence and fixtures
  for the Python baseline.
- `specs/tech/12-tech-python-api-contract-NEW.md` — defines route-level cases.
- `specs/tech/13-tech-ts-api-parity-NEW.md` — defines parity and approved
  exception handling.

## Depends on

- Separate, disposable data roots for Python and TypeScript execution.
- A future chosen TypeScript test runner and a real-browser/manual check
  method; neither is selected by current repository evidence.
- A host that supports Node's recursive filesystem watcher for live-refresh
  verification.

## Surface for follow-up

- Once parity is established, the same fixture corpus can protect approved API
  or UX changes without confusing them with migration regressions.
- The test plan makes an eventual cutover review evidence-based without adding
  CI/CD scope.
