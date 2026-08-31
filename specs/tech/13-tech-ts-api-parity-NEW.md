# 13 · TypeScript API parity — implementation definition

## Purpose

The TypeScript/Next.js implementation must expose the same HTTP contract as
the current Python application. `specs/tech/12-tech-python-api-contract-NEW.md`
is the canonical endpoint, payload, status, error, and UI-negotiation table.
This document defines how to implement against that table without duplicating
or silently changing it.

## Contract rule

For every migrated route:

1. Keep the same method and path.
2. Keep the same request format, required fields, and path/query semantics.
3. Keep the same successful status, response media type, JSON shape, and
   persistent result.
4. Keep the same documented error status and envelope, including current
   `500` paths that result from malformed nested payloads or UI parse errors.
5. Preserve default HTML `404` and `405` responses for unmatched HTTP routes.
6. Preserve the `/ui` shell-versus-fragment distinction for headerless,
   HTMX, and browser-navigation requests.

The implementation may use Next route handlers, React, shadcn/ui, and Node
filesystem APIs. Those are implementation choices, not permission to change
the contract.

## Locked toolchain

| Element | Selected version / rule | Verification status |
| --- | --- | --- |
| Node.js | `24.19.0` LTS, installed through Homebrew as `node@24` and linked as the active `node`. | Runtime and npm CLI verified locally. |
| Next.js | `16.3.3`. | `js/` workspace exists; production build (`next build --webpack`) verified. The default Turbopack build is not verified in this managed environment because Tailwind PostCSS attempts a restricted child-process bind. |
| React and React DOM | `19.2.8`, satisfying Next 16.3.3's `^19.0.0` peer range. | Installed and build-verified. |
| TypeScript | `7.0.2`. | Installed and build-verified as the selected compatible stable release. |
| shadcn/ui | `shadcn@latest` was selected for the UI migration. | `components.json`, Tailwind/PostCSS setup, shared `cn` helper, and Button/Card/Input/Table primitives are present and used by the shell; full visual replacement remains a UI follow-up. |
| Browser workflow tooling | Playwright Test `1.62.1`. | `js/playwright.config.ts` has fifteen workspace smoke tests; all fifteen pass in the latest production-server Chromium run. |

The JavaScript workspace and `js/package-lock.json` now exist. The lockfile is
the npm-generated dependency record for the current implementation. The
shadcn configuration and shared Button are the first adopted primitives; the
rest of the shell remains on its existing classes until each surface is
migrated and browser-verified. The local browser harness builds once and
starts the production Next server, avoiding development-server hot-reload
races.

## Required server boundaries

| Boundary | TypeScript responsibility | Contract constraint |
| --- | --- | --- |
| HTTP adapter | Decode request, call a domain/storage operation, encode response. | Do not normalize all failures into one new error format. |
| Feature domain | Parse, validate, split imports, and serialize Gherkin. | Structured saves and raw saves remain separate modes. |
| Filesystem adapter | Resolve logical paths, atomically persist, list folders, and maintain typed storage. | Do not let browser code access the project root directly. |
| YAML/enums adapter | Read/write enums, runs, reports, and reference cascades. | Preserve field names and current legacy/malformed-data behaviour. |
| Allure adapter | Parse a single submitted HTML text value. | Preserve the 30 MiB limit, preview/commit split, and report-derived timestamp. |
| Live-refresh adapter | Publish the current SSE wire format. | Preserve `change` event naming, empty data, heartbeat, and self-write suppression semantics. |
| React/shadcn UI | Render and mutate through the HTTP contract. | Preserve observable navigation, error, retry, draft, and destructive-action outcomes. |

## Persistence and mutation rules

- TypeScript must run server-side for any filesystem operation. The browser is
  never the persistence authority.
- Python and TypeScript must not concurrently write the same data root. A
  differential comparison uses two isolated copies of the same fixture.
- Structured feature saves are parsed, validated, enum-checked, and
  canonicalized. Raw saves are parsed and enum-checked, normalize only line
  endings, and otherwise preserve the submitted source.
- Rename can rewrite run/report references and has compensating recovery;
  cross-folder file move currently does not perform that cascade. Preserve the
  distinction unless a separate approved change supersedes it.
- No database, external API, or data migration is implied by this design.

## Explicit migration exceptions

The target normally matches the Python contract exactly. The following
previously approved decisions conflict with current Python source and are
therefore exceptions, not claims of current parity:

| Exception | Current Python | TypeScript target | Required verification |
| --- | --- | --- | --- |
| Run `created_at` | Whole-run PATCH accepts the submitted value. | Reject a changed `created_at` at the API boundary and preserve stored value. | Changed value fails without persistence; same value succeeds. |
| Generic typed-area mutation | Generic folder rename/delete and file move are not consistently blocked. | Reject generic move, rename, and delete for typed areas. | Each prohibited route returns the decided error and leaves storage unchanged. |

These exceptions must remain visible in implementation and test documentation.
If exact Python parity is required instead, a human decision must explicitly
revoke the relevant exception; do not decide from code comments or old specs.

## Implementation order

1. Establish a Node/Next runtime, data-root configuration, one-writer policy,
   and local test command. The repository does not establish those choices.
2. Prove Gherkin, YAML, Allure, atomic-write, and SSE primitives against the
   fixture corpus before using them in route handlers.
3. Implement read-only tree/folder/file routes and the `/ui` negotiation
   contract.
4. Implement feature and enum writes, including raw-save compatibility and
   feature import.
5. Implement runs, Allure import, and reports.
6. Implement rename/move/delete after run/report reference handling exists.
7. Implement live refresh and complete compatible-host/browser verification.

## Compatibility spike status

The following temporary Node 24.19.0 spikes completed without changing
application code:

| Concern | Candidate / result | Migration implication |
| --- | --- | --- |
| Gherkin parse | `@cucumber/gherkin` `42.0.1` parsed a tagged two-scenario feature and reported an invalid dialect as a parse error. | Viable parser candidate; its AST/error mapping still needs differential fixtures against Python. |
| YAML | `yaml` `2.9.0` parsed run-shaped YAML with key order intact, but `stringify(parse(text))` changed quoting. | Viable semantic parser, not a byte-compatible serializer without custom formatting or an approved byte-comparison rule. |
| Atomic write | Node `open(..., "wx")`, file `sync()`, and `rename()` completed a same-directory replacement in a temporary directory. | Viable primitive only; failure recovery, path locking, and multi-file cascade rollback remain unverified. |

No parser or serializer is approved as final solely from this spike.

## First implemented slice: read-only tree

`js/` now contains an independent Next.js Node-runtime implementation of
`GET /api/tree`. It reads the configured filesystem root directly; it does
not import, call, or start Python application code. `TMS_DATA_ROOT` selects a
root for local runs; when absent, the server resolves the repository's
`project/` directory relative to the `js/` workspace.

The slice has fixture tests for recursive counts, `@auto` tag semantics,
malformed and zero-scenario feature fallback, typed-area hiding, folder-first
ordering, and the HTTP response. `npm test`, `npm run build`, and a local
Node-runtime request against the existing `project/` directory passed. This
does **not** yet prove complete differential parity with every Python tree
fixture, platform filesystem behaviour, or browser workflow.

`GET /api/folders/contents` and `GET /api/folders/<path>/contents` are also
implemented from the Node filesystem layer. They retain the depth-specific
listing shapes, typed-area and temp-file filtering, best-effort feature rows,
strict UTF-8 fallback, leading enum directives, and resolved enum labels.
The nested public URL is served by a terminal Next catch-all route because
Next does not allow a catch-all segment before a trailing `contents` segment.

That routing constraint exposed a parity gap: a non-public path captured by
the catch-all and an unsupported method initially received Next's empty
default `404`/`405`, whereas Python exposes framework-default HTML. The Node
routes now use a small Flask/Werkzeug-shaped HTML response for the captured
non-public folder path and explicitly unsupported methods; direct runtime
checks confirm `text/html` responses and the expected status/body class.
Unmatched paths still use Next's framework HTML page, preserving the public
HTML—not-JSON contract without requiring byte-identical framework markup.

`GET /api/enums/<project>` is implemented independently as a read-only
Node route. It returns the ordered vocabulary mapping, uses the current
empty-document and empty-kind normalization, maps a missing enum file to the
JSON `404 not_found` envelope, and maps YAML or schema failure to JSON `422
enums_parse_error` with line/column details. Its source and route fixtures
pass, as does a Node-runtime request against an existing project enum file.
Enum mutation, kind-label metadata, and enum-key cascades are deliberately
outside this slice.

The current Node slice now also covers the first feature-write and enum
mutation paths. Structured feature `PATCH` validates the payload, canonical
serializes it, and checks enum references; raw `PUT` parses and enum-checks
the submitted source while retaining its source formatting apart from line
ending normalization. Batch feature import accepts ordered `.feature` sources,
collects source-specific validation errors before writing, enforces the
20-file/3 MiB limits, generates the lowest available `<folder>_<n>.feature`
names, and compensates already-created files if a later create fails.
Enum initialization, whole-document replacement, in-use removal blocking,
clear, kind-label metadata, and selected-key cascade are implemented as
separate API routes. The cascade follows the Python alias-first ordering and
only rewrites references for the requested kind; full crash/restart recovery
and inter-process locking remain unverified.

The run and report persistence slices are now server-side Node routes as well.
Runs use validated YAML under the reserved `test-run` area, support group/run
CRUD and per-case result mutations, preserve insertion order, and reject a
changed `created_at` on whole-run PATCH (the approved target exception).
Allure single-file preview/commit parses nested suites, maps statuses,
collapses retries, resolves scenario names case-insensitively, enforces the
30 MiB input cap, and commits only when every row resolves. Reports use the
reserved `report` area with typed validation, live-reference cross-checks,
immutable `type`/`created_at` PATCH handling, and malformed-file tolerant list
summaries.

Generic folder/file rename, move, duplicate, and recursive delete routes are
also present. Generic operations reject paths through `test-run` or `report`;
same-parent feature rename and folder rename rewrite affected run/report
references, while cross-folder file move intentionally does not cascade.
Metadata rollback and concurrent-writer behavior are covered only by local
unit-level fixtures, not by a multi-process differential run. Representative
feature-model wire-shape, tree/folder route, feature-write, run-write,
report-write, enum-write, Allure-import, fresh-run, error-contract, relocation,
legacy-import, and batch-import differential tests now compare TypeScript
results with Python over disposable roots. A default-error contract test
checks the HTML status/content-type/body class. The feature-write
comparison also protects canonical
duplicate-tag deduplication, table-cell trimming/alignment, and raw
line-ending-only writes. The report comparison covers CRUD, live aggregation,
immutable timestamps, and persisted YAML semantics. The enum comparison covers
vocabulary replacement, kind-label metadata, usage, rename cascades, and
in-use guards. The Allure comparison covers nested suites, retry collapse,
status mapping, report-derived timestamps, and imported-run persistence. The
legacy-import comparison covers the original `{source}` preview/commit shape,
multi-scenario ordering, name mapping, duplicate rejection, and persisted
bytes. The batch comparison covers source/scenario order, explicit generated
names, and all-or-nothing source validation; the Chromium shell/deep-link
smokes pass. Fresh-run
creation also checks
the server-stamped UTC `+00:00` timestamp shape. The error-contract comparison
protects the required generic 500 for malformed nested run payloads.

`GET /api/events` now emits the `: connected` marker, `event: change` with an
empty data field, and 15-second heartbeat comments. A Node recursive watcher
publishes best-effort changes and suppresses events for paths marked by the
atomic-write adapter. The production Next server was manually exercised on
macOS: after the SSE connection was established, an external nested feature
file produced `event: change`. Recursive watcher support remains
host-dependent; Python FSEvents verification is outside this TypeScript
workability check.

The Next app shell now provides a responsive API-driven workspace with
recursive directory count badges, a collapsible directory tree whose expanded
paths survive tree refreshes, project/module/subfolder and feature create
actions, folder-detail scenario filtering and file-name/scenario-name sorting,
multi-file import, folder/file destructive actions, tree-backed feature move,
manual reload, and SSE-driven external-change handling (clean reload, dirty
conflict, and removed-file banners), field-level structured and raw feature
editors, snapshot-aware dirty tab switching, description-gated saves, the
structured save cleanup pass, and raw-save parse/validation errors rendered
inside the raw editor. Successful saves now show a transient Saved indicator
that is cleared by subsequent edits. Shared
shadcn primitives now back the run/report/enum cards, selected
inputs, tables, and action buttons without changing the request/state logic.
Runs expose an all-project listing sourced from `/api/run-groups` plus
project-scoped run detail, fresh-run creation, and preview-gated Allure import
actions, and a draft run editor for description, case results, remarks,
add/remove case rows, reload, and whole-document save while preserving the
approved `created_at` rule;
reports expose a global project listing with project filtering, definition and
rendered computed-view inspection (ranking/inventory disclosures and trend
tables), plus a draft data-source editor (run add/remove with the ten-run cap,
or folder scope editing), reload, and whole-document save while preserving
immutable fields; search exposes scope, description/tag matching, case
sensitivity, debounced input, distinct empty/no-match states, and single-hit
navigation; enums expose a global project chooser plus the existing
inline kind/entry creation and kind-label editing. Reports now include an
inline type-aware create form that posts the existing report contract; report
view data is also available through the server-side
`/api/reports/<project>/<file_name>/view` route. The browser remains an API
consumer rather than a filesystem client.
A real-browser workflow check now runs successfully against Chromium, covering
the workspace shell, narrow viewport, root query deep-link, legacy
`/ui/file`, `/ui/run`, and `/ui/report` deep links, bookmarked search,
dirty-editor tab protection, create/import/filter/recursive-delete,
run-edit/report-create, Allure preview/import, report computed-view editing,
inline enum kind/entry/label flows, folder rename, raw-save plus rename/move,
and the external-change UI handlers.
The Next shell now supports direct URL
rehydration with `/?tab=directory|runs|reports|enums`, optional `project`, and
directory `path` query parameters. State changes replace the current URL
without adding browser-history entries; this keeps the SPA navigation stable
while allowing bookmarks and refreshes to restore the selected view. The
legacy `/ui/*` paths are now exposed by a server-side compatibility adapter:
HTMX/headerless GETs receive HTML fragments backed by the Node domain layer,
while browser-navigation GETs receive a 200 HTML bridge into the real Next
shell with equivalent `tab`/`project`/`path` state. Fragment markup is intentionally not byte-for-
byte Jinja output; status, media type, route data, and user-visible content
are the parity boundary. Broader cross-surface workflows remain before
cutover.

Each slice follows Plan → Do → Check → Act:

- **Plan:** identify the Python route rows, fixtures, expected disk state, and
  any approved exception.
- **Do:** implement only that vertical slice.
- **Check:** run the differential tests in
  `specs/tech/14-tech-parity-tests-NEW.md`.
- **Act:** record a verified parity result or an explicit approved deviation
  before expanding scope.

## Affects

- The future TypeScript/Next.js server and UI — defines compatibility rather
  than a framework-specific architecture.
- `specs/tech/12-tech-python-api-contract-NEW.md` — supplies the contract
  this implementation must keep.
- `specs/tech/14-tech-parity-tests-NEW.md` — defines the proof required for
  every migrated route.

## Depends on

- The source-verified Python contract in
  `specs/tech/12-tech-python-api-contract-NEW.md`.
- A pre-implementation decision for TypeScript runtime/toolchain and data-root
  ownership; neither is confirmed by the current repository.
- The approved exception register above.

## Surface for follow-up

- A new API version, changed error semantics, or broader UX improvement can
  be proposed independently after parity is established.
- The document makes it possible to replace Flask/HTMX internals without
  changing consumer-visible behaviour.
