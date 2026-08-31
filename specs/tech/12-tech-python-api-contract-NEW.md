# 12 · Python HTTP API contract — migration baseline

## Status and evidence

This is a source-verified description of the currently shipped Python HTTP
surface. It is the baseline for a TypeScript implementation; it is not a new
product specification.

Primary evidence is `app/server/routes_*.py`, shared request helpers in
`app/server/_shared.py`, and error handlers in `app/server/errors.py`.
Relevant smoke scripts are named in `specs/tech/14-tech-parity-tests-NEW.md`.
When source, tests, historical plans, or feature specifications disagree, the
conflict must be recorded rather than resolved from naming or convention.

## Scope

- JSON and raw-text endpoints below `/api`.
- Server-sent events at `/api/events`.
- The observable HTTP behaviour of HTML endpoints below `/ui`.
- HTTP status, response media type, response body shape, and persistent side
  effect where the current source establishes one.

This document does not define a new API version, authentication, database, or
network integration. Repository evidence shows none of those as part of this
application's current HTTP contract.

## Shared conventions

- `api` routes are mounted at `/api`; `ui` routes are mounted at `/ui`.
- Route `<path:p>` parameters represent data-root-relative, slash-separated
  logical paths. Request `parent` fields use the same form; `""` represents
  the root where a route permits it.
- JSON request routes require a JSON object. A non-object or unparsable body
  raises `ValueError`, normally returned as the JSON `400` envelope below.
- Successful mutating routes conventionally return `{"ok": true}` except
  where their endpoint row states a different body. Deletes returning `204`
  have no body.
- Feature raw reads return `text/plain; charset=utf-8`; raw writes take the
  request body as text, not JSON.
- A feature payload is
  `{description,tags,background:{steps},scenario:{kind,name,tags,steps,examples},enums}`.
  A step is `{keyword,text,data_table}`; an examples table is
  `{tags,name,header,rows}`. Tags omit their `@` prefix.
- A run payload is `{name,created_at,description,results}`. A result is
  `{file_path,result,remark}` and optionally
  `example:{table:<int>,row:<int>}`.
- A report payload is
  `{type,title,created_at,run_paths,scope,status,kind,case_path,tag}`.

### Listing, count, and search semantics

- Folder listings are `{kind:"root",projects}`, `{kind:"project",modules}`,
  or `{kind:"module"|"subfolder",folders,features}`. A feature summary is
  `{file_name,description,scenario_name,tags,enums}`. Parsing a listed feature
  is best-effort: malformed files remain present with empty summary fields.
- Tree counts are recursive and attach to every visible folder, including a
  project. They exclude the reserved `test-run` and `report` areas from the
  directory tree. For one feature source, `total` is its split scenario count;
  malformed or zero-scenario source is one non-auto case. Tag matching for
  `auto` is case-insensitive. If the feature has `@auto`, all its scenarios
  count as auto; otherwise only scenarios with `@auto` count as auto.
- Search returns `[]` for blank `q`. `scope` is `all`, `project:<name>`, or
  `module:<project>/<module>`; malformed scope is `400`. `match` is `text` or
  `tag`; malformed match is `400`. Text searches description or scenario name
  but reports `matched_field:"description"`; tag searches the de-duplicated
  union of feature and scenario tags. `case=true|1|yes` enables case-sensitive
  matching. Unparseable feature files are skipped by search.

## Error contract

Except for framework HTTP exceptions, API errors use:

```json
{"error":{"code":"<code>","message":"<message>","details":{}}}
```

`details` is omitted when absent. The current mappings are:

| Source failure | Status | `error.code` | Details when present |
| --- | ---: | --- | --- |
| `ValueError` | 400 | `bad_request` | — |
| `FileNotFoundError` | 404 | `not_found` | — |
| `NameConflictError` | 409 | `name_conflict` | `path` |
| `ValidationError` | 422 | `validation_error` | `field` |
| Gherkin parse error | 422 | `parse_error` | `line`, `column` |
| Run parse error | 422 | `run_parse_error` | `line`, `column` |
| Report parse error | 422 | `report_parse_error` | `line`, `column` |
| Enums parse error | 422 | `enums_parse_error` | `line`, `column` |
| Enum in use | 409 | `enum_in_use` | `kind`, `key`, `count`, `sample` |
| Import validation | 422 | `import_validation_error` | `reasons` |
| Other non-HTTP exception | 500 | `internal_error` | — |

Werkzeug HTTP exceptions, including unmatched `404` and unsupported-method
`405`, pass through Flask's default HTML handling. This is an observable
contract. UI routes only specially render `ValueError` (400) and
`FileNotFoundError` (404); other non-HTTP UI exceptions become a generic HTML
500 snippet.

## API endpoint contract

### Tree, folders, search, and events

| Method and path | Request | Success response | Current failure / side-effect notes |
| --- | --- | --- | --- |
| `GET /api/tree` | — | Recursive directory tree `{name:"",children:[...]}`; visible folders include `counts:{total,auto,non_auto}`. | Malformed or zero-scenario feature files count as one non-auto case. |
| `GET /api/events` | — | `text/event-stream`; initial `: connected`, `event: change` with empty data, 15-second heartbeat comments. | In-process, watcher-driven stream. |
| `GET /api/folders/contents` | — | Root folder listing. | — |
| `GET /api/folders/<path>/contents` | — | Listing for the requested folder. | Explicit `400` for invalid depth/path, `404` for missing folder. |
| `POST /api/folders` | `{parent,name}` | `201 {"ok":true}` | Creates one folder; project creation also initializes enum storage. |
| `PATCH /api/folders/<path>` | `{name}` | `200 {"ok":true}` | Same-parent rename; may rewrite run/report references. |
| `DELETE /api/folders/<path>` | — | `204` | Recursive and idempotent for a missing target. |
| `GET /api/search?q=&scope=&match=&case=` | Query parameters optional. | `{"hits":[...]}` | Delegates to current storage search semantics. |

### Feature files and feature import

| Method and path | Request | Success response | Current failure / side-effect notes |
| --- | --- | --- | --- |
| `POST /api/files` | `{parent,file_name,scenario_name,description?}` | `201 {"ok":true}` | `parent` must be depth 2 through max depth; `scenario_name` must be non-blank. |
| `POST /api/files/import/preview` | Legacy `{source}` or batch `{sources:[{name,source}]}` | Legacy metadata or batch `{errors,enum_sources,enums_present,scenarios}`. | No write. Batch limit: 20 files and 3 MiB total UTF-8 source. |
| `POST /api/files/import` | Legacy `{parent,source,names,project?}` or batch replacing `source` with `sources`. | `201 {"ok":true,"created":[...]}` | Re-splits and validates on commit; all-or-nothing write. |
| `GET /api/files/<path>` | — | Feature payload. | Non-feature suffix returns `415 unsupported_type`. |
| `PATCH /api/files/<path>` | Full feature payload. | `200 {"ok":true}` | Structured write validates and canonically serializes. |
| `DELETE /api/files/<path>` | — | `204` | Idempotent for a missing file. |
| `PATCH /api/files/<path>/rename` | `{file_name}` | `200 {"ok":true}` | Same-parent rename; rewrites run/report references. |
| `PATCH /api/files/<path>/move` | `{parent}` | `200 {"ok":true}` | Cross-folder move; current code does not cascade references. |
| `POST /api/files/<path>/duplicate` | `{file_name}` | `201 {"ok":true}` | Same-parent copy. |
| `GET /api/files/<path>/raw` | — | Raw source as text/plain. | Non-feature suffix returns `415 unsupported_type`. |
| `PUT /api/files/<path>/raw` | Raw text body. | `200 {"ok":true}` | Parses and enum-checks; normalizes CRLF/lone CR to LF; otherwise keeps source formatting. Parseable-but-model-invalid source can currently succeed. |

### Project enums

| Method and path | Request | Success response | Current failure / side-effect notes |
| --- | --- | --- | --- |
| `GET /api/enums/<project>` | — | `{kind:{key:label}}` vocabulary. | Missing legacy enum file is `404`; malformed YAML is `422`. |
| `POST /api/enums/<project>` | — | `201` vocabulary. | Initializes default vocabulary; conflict if it already exists. |
| `PUT /api/enums/<project>` | Whole vocabulary `{kind:{key:label}}`. | Updated vocabulary. | Cannot remove in-use keys/kinds. |
| `PUT /api/enums/<project>/kind-labels` | `{kind_id:display_label}`. | Stored label map. | Stable kind IDs; metadata only. |
| `POST /api/enums/<project>/rename` | `{kind,old_key,new_key}` | `{"renamed":<count>}` | Cascades feature enum keys after preflight. |
| `POST /api/enums/<project>/clear` | — | `{"cleared":true}` | Refuses when any enum is still in use. |
| `GET /api/enums/<project>/usage?kind=&key=` | Required query parameters. | `{"count":<int>,"sample":<value>}` | Validates enum storage first. |

### Test runs and Allure import

| Method and path | Request | Success response | Current failure / side-effect notes |
| --- | --- | --- | --- |
| `GET /api/run-groups` | — | `{"projects":[...],"groups":[{project,group}]}` | Projects without run groups remain visible. |
| `POST /api/runs/<project>/groups` | `{name}` | `201 {"ok":true}` | Creates a group. |
| `DELETE /api/runs/<project>/groups/<group>` | — | `204` | Refuses to delete a non-empty group. |
| `POST /api/runs` | `{project,group,name,file_name,case_paths,description?}` | `201 {"ok":true}` | Requires an existing group; server stamps `created_at`. |
| `POST /api/runs/import/preview` | `{project,html}` | `{report_name,created_at,scenarios,counts,errors}` | No write; HTML text cap is 30 MiB. |
| `POST /api/runs/import` | `{project,group,name,file_name,description?,html}` | `201 {"ok":true}` | Re-parses/re-resolves on commit; all-or-nothing; preserves report-derived `created_at`. |
| `GET /api/runs/<project>/<group>` | — | `{"runs":[...]}` | — |
| `GET /api/runs/<project>/<group>/<file_name>` | — | Run payload. | — |
| `PATCH /api/runs/<project>/<group>/<file_name>` | Full run payload. | `200 {"ok":true}` | Whole-document write. Current Python route accepts the incoming `created_at`; see the decision register below. |
| `DELETE /api/runs/<project>/<group>/<file_name>` | — | `204` | — |
| `POST /api/runs/<project>/<group>/<file_name>/cases` | `{file_path}` | `201 {"ok":true}` | Adds a pending result. |
| `DELETE /api/runs/<project>/<group>/<file_name>/cases/<case_path>` | — | `204` | URL-decodes case path; idempotent when no matching result. |
| `PATCH /api/runs/<project>/<group>/<file_name>/cases/<case_path>` | `{result?,remark?}` | `200 {"ok":true}` | Updates the matching result. |
| `GET /api/runs/<project>` | — | `{"runs":[{path,group,file_name,name,created_at}]}` | Newest first, then path tie-break. |

### Quality reports

| Method and path | Request | Success response | Current failure / side-effect notes |
| --- | --- | --- | --- |
| `POST /api/reports/<project>` | Report payload plus `file_name`. | `201 {"ok":true}` | Server stamps report `created_at`. |
| `GET /api/reports/<project>` | — | `{"reports":[...]}` | — |
| `GET /api/reports/<project>/<file_name>` | — | Report payload. | — |
| `PATCH /api/reports/<project>/<file_name>` | Full report payload. | `200 {"ok":true}` | `type` and `created_at` are immutable; differing values return `422`. |
| `DELETE /api/reports/<project>/<file_name>` | — | `204` | — |

## UI HTTP contract

The UI routes are HTML endpoints, not JSON API aliases:

- Sidebar fragments: `/ui/tree`, `/ui/test-run-tree`, `/ui/reports-tree`, and
  `/ui/enums-tree`.
- Main-pane routes: `/ui/enums/<project>`, `/ui/folder[/<path>]`,
  `/ui/file/<path>`, `/ui/run/<project>/<group>/<file_name>`,
  `/ui/report/<project>/<file_name>`, and `/ui/search`.
- For a non-HTMX browser navigation with `Sec-Fetch-Mode: navigate`, item
  routes return the complete base shell. HTMX requests and headerless callers
  receive the HTML fragment. A missing item on a direct navigation therefore
  loads a shell before its main-pane fetch displays the error fragment.

The TypeScript UI may replace Jinja and HTMX, but it must preserve this
observable request/response distinction until an approved contract change.

## Decision register: current Python versus migration target

These entries prevent the contract from silently claiming incompatible things.

| Behaviour | Current Python evidence | Approved migration direction | Contract status |
| --- | --- | --- | --- |
| Run `created_at` on whole-run PATCH | The route deserializes and writes the submitted value. | API-boundary `created_at` immutability was explicitly approved. | Intentional target divergence; do not describe it as current Python parity. |
| Generic operations in typed areas | Generic creation rejects reserved typed areas; generic folder rename/delete and file move do not consistently guard them. | Generic move, rename, and delete must be prohibited for typed areas. | Intentional target divergence; needs a negative contract test. |
| Raw feature save | Validates Gherkin syntax and enum references; persists normalized-LF source without structured canonicalization. | Preserve current behaviour. | Current parity rule. |

## Affects

- `app/server/routes_*.py` — records their current externally observable
  surface for migration comparison.
- `app/server/_shared.py` and `app/server/errors.py` — define shared request,
  error, and UI negotiation behaviour.
- `specs/tech/13-tech-ts-api-parity-NEW.md` — reuses this table as the
  TypeScript compatibility definition.
- `specs/tech/14-tech-parity-tests-NEW.md` — supplies verification for this
  contract.

## Depends on

- Current route registration in `app/server/__init__.py` and the Flask
  blueprints in `app/server/_shared.py`.
- Current storage, Gherkin, YAML, Allure, and watcher behaviours beneath the
  route layer.
- Explicit user-approved migration decisions recorded above.

## Surface for follow-up

- A TypeScript route implementation can use this document without copying
  Flask or HTMX internals.
- Any proposed API improvement must first be recorded as a contract change,
  not silently introduced while migrating.
