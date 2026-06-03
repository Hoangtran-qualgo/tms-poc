# PLAN.md — TMS (BDD Test Case Manager)

Implementation plan. Approved during the **Plan** phase of the PDCA workflow.
Updates to this file require explicit approval.

Companion documents:
- `README.md` — user-facing
- `AGENTS.md` — contributor source of truth

---

## 1. Process

Strict PDCA loop with explicit signals between phases and between Do-steps.

1. **Investigate** — completed. All product/UX/tech decisions captured.
2. **Plan** — this document.
3. **Do** — implement steps from §12 one-by-one, pausing after each for a "next" signal.
4. **Check** — full code-base review; produce a list of issues, tech debt, logic conflicts, mistakes. No fixes during Check.
5. **Act** — fix items from the Check list one-by-one. Re-run Check after Act completes. Loop Check ↔ Act until the list is empty or stop is signalled.

Rules:
- No code in Investigate or Plan phases.
- No multi-step implementation in Do without explicit signals.
- No new features in Act — only fixes for Check findings.
- Any mid-phase discovery that changes earlier decisions is surfaced, not silently adjusted.

---

## 2. Architecture Overview

```
┌──────────── Browser (single tab) ────────────┐
│  Jinja2-rendered HTML + Tailwind CDN + HTMX  │
│  - tree pane (SSE-driven, any depth)         │
│  - main pane (project / module / file view)  │
│  - top bar (search, breadcrumb)              │
└──────────────────┬───────────────────────────┘
                   │ HTTP (HTMX partials + JSON) + SSE
┌──────────────────▼───────────────────────────┐
│                 Flask app                    │
│  routes ──► storage ──► FS                   │
│              │                               │
│         gherkin_io                           │
│  watcher (watchdog) ──► pubsub ──► SSE       │
└──────────────────────────────────────────────┘
                   │
              ./project/  (data root, recursive watch)
```

Module boundaries:
- `routes` know HTTP; never touch FS directly.
- `storage` is the only module that reads/writes files.
- `gherkin_io` is pure: text-in → model, model → text-out. No FS.
- `watcher` runs in a background thread; publishes events to an in-memory pubsub. SSE endpoint subscribes per request. Also owns the `recent_writes` TTL set and the temp-file path filter (see §7).
- No `services` layer — routes call `storage` directly.

App startup actions (`create_app` factory):
1. Resolve and create the data root if missing.
2. **Scan the data root recursively for atomic-write orphan temp files** matching `.+\.tmp\.\d+\.[0-9a-f]+$` and delete them.
3. Start the watcher observer.
4. Register Flask blueprints.

---

## 3. Stack & Dependencies

- **Python**: 3.12+
- **Backend**: Flask, bound to `127.0.0.1` only (local tool; no auth, no CSRF / host-header hardening).
- **Frontend**: Jinja2 templates + HTMX 2 (with SSE extension) + Tailwind CSS v4 (Browser CDN).
- **Run**: `flask run` or `python -m app`.
- **No automated tests in v1.** (Documented risk in §13.)

`requirements.txt`:

| Package            | Pin             | Reason                  |
| ------------------ | --------------- | ----------------------- |
| `flask`            | `>=3.0,<4`      | server                  |
| `gherkin-official` | `>=32,<33`      | parse `.feature` to AST (latest stable 32.1.0) |
| `watchdog`         | `>=4,<7`        | recursive FS observer   |

Browser CDN URLs pinned in `templates/base.html`:
- Tailwind: `https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4`
- HTMX: `https://unpkg.com/htmx.org@2`
- HTMX SSE ext: `https://unpkg.com/htmx-ext-sse@2`

---

## 4. Domain Model (`app/models.py`)

All `@dataclass(slots=True)`. UI sends JSON; reconstruct via `from_dict`.

**Invariant**: each `.feature` file holds **exactly one** scenario (or scenario outline). The model reflects this — no list of scenarios.

```
Step
  keyword: Literal["Given","When","Then","And","But"]
  text: str                              # single-line; non-empty at write time
  data_table: list[list[str]] | None     # None when absent; row 0 is treated as the
                                         # header by tool convention (UI bolds it).
                                         # Cells store unescaped text; serializer/parser
                                         # handle `\|` and `\\` escaping (see §5).

ExamplesTable
  tags: list[str]                        # stored WITHOUT leading `@`
  name: str                              # "" means absent; single-line; validated at write
  header: list[str]
  rows: list[list[str]]                  # cells: same escaping as Step.data_table

Scenario
  kind: Literal["scenario","outline"]
  name: str                              # single-line; may be empty; validated at write
  tags: list[str]                        # stored WITHOUT leading `@`
  steps: list[Step]
  examples: list[ExamplesTable]
    # If kind == "outline", len(examples) >= 1 is required at write time.
    # Default for a freshly created outline: [ExamplesTable(header=["col1"], rows=[])].
    # If kind == "scenario", examples must be [].

Background
  steps: list[Step]                      # empty == not serialized

Feature
  description: str                       # multi-line in-memory; single line on disk with
                                         # real `\n` encoded as the literal two-char `\n`.
                                         # Non-empty; first physical line is non-blank.
                                         # When the source file has a multi-line body
                                         # description block under `Feature:`, the parser
                                         # concatenates: description = name + "\n" + body.
  tags: list[str]                        # stored WITHOUT leading `@`
  background: Background                 # always present in the model; omitted from disk when empty
  scenario: Scenario                     # exactly one
```

**Tag storage form**:
- Model holds tags as bare strings without the leading `@` (e.g., `"smoke"`, `"login"`).
- **Parser** strips a leading `@` from each AST tag on read.
- **Serializer** prepends `@` to each tag on write.
- **UI** chip badges render with `@` prefix; chip input strips a leading `@` if the user types it.

**Tag character rules** (validated at write and at UI chip-input time):
- Non-empty after the leading `@` strip.
- No whitespace anywhere in the tag value.
- ASCII-printable only (codepoints `0x21`–`0x7E`), excluding `@` (already stripped) and `,` (used as a chip separator).
- Duplicate tags within the same tag list are de-duplicated at write time (order preserved, first occurrence kept).

**Description encoding (`gherkin_io` boundary)**:
- The **model** stores `description` with real `\n` characters.
- The **serializer** encodes each real `\n` as the literal two-character sequence `\n` when writing, so the on-disk `Feature:` line is always a single line.
- The **parser** decodes each literal `\n` back into a real newline character on read; also concatenates the Gherkin body description block (if any) into `description`.
- The **API and UI** see real-newline strings end-to-end; no extra encoding at the API boundary.
- Caveat: a user-typed literal `\n` in the UI textarea round-trips as a line break on the next save. Documented in `README.md`.

**Cell escaping (DataTable + ExamplesTable rows/header)**:
- Cells stored in the model are **unescaped** text (may contain `|` and `\` freely).
- The **serializer** escapes `\` → `\\` first, then `|` → `\|` per cell.
- The **parser** unescapes `\|` → `|` and `\\` → `\` per cell.
- Leading/trailing whitespace per cell is stripped at serialize time; empty cells render as a single space between pipes (column-aligned).

**Newline normalization**:
- The parser converts all `\r\n` and lone `\r` to `\n` **before** passing source to `gherkin-official`. The model holds LF-only strings throughout. The serializer always writes LF.

Excluded from the model (parsed-and-discarded on read; never written):
- DocStrings (`"""…"""`)
- Comments
- Blank lines
- `# language:` headers (English only)
- **Steps whose AST keyword is not one of the canonical five** (`Given/When/Then/And/But`). Silently dropped on read (documented risk in §13).

Rejected outright on parse:
- `Rule:` blocks — incompatible with the one-scenario-per-file invariant.
- A file containing more than one `Scenario` or `Scenario Outline`.

Auto-corrected on read (lenient):
- A file with **zero** scenarios → parser inserts a placeholder `Scenario(kind="scenario", name="", steps=[], examples=[], tags=[])`. The next save persists it.

Step ordering is not restricted: any of the five keywords (Given / When / Then / And / But) may appear in any position. The UI keyword dropdown lists all five at all positions.

---

## 5. Gherkin I/O (`app/gherkin_io.py`)

### 5.1 Read path
- Normalize input newlines: `\r\n` → `\n`, lone `\r` → `\n`.
- `gherkin.parser.Parser().parse(source)` → `GherkinDocument` AST → our model.
- Mapped AST nodes: `Feature`, `Background`, `Scenario` (and outline via `examples`), `Step`, `DataTable`, `Examples`, `Tag`.
- Step keyword normalization: AST returns the keyword with trailing space (`"Given "`); strip and **lookup** against the five canonical English keywords. If the keyword does not match, the step is silently dropped (lossy; see §13).
- Tag normalization: strip any leading `@` per tag value.
- DataTable / Examples cells: per-cell `\|` → `|`, `\\` → `\` unescaping.
- Description assembly:
  - Start with the AST `feature.name`.
  - If the AST also has a `feature.description` body block, append `"\n"` then the body text verbatim (preserving its internal newlines).
  - Then decode every literal `\n` (two chars) in the resulting string to a real newline (covers files previously written by this tool).
- **Rejections** (raise `GherkinParseError`):
  - File contains a `Rule:` block.
  - File contains more than one scenario / scenario outline.
  - Any `CompositeParserException` from the underlying parser.
- **Lenient fixups**:
  - Zero scenarios → inject a placeholder `Scenario`.
  - Non-canonical step keywords → drop those steps.
- All `GherkinParseError`s carry `line`, `column`, and `message`. Messages are human-readable, no error codes (the API attaches HTTP status separately).

### 5.2 Write path (canonical serializer)
Pre-write validation (raises `ValidationError`):
- `Feature.description` is non-empty.
- All single-line fields (`Scenario.name`, step text, `ExamplesTable.name`) contain no real newline.
- All `Step.text` values are **non-empty** after trim.
- `Scenario.kind == "outline"` requires `len(examples) >= 1`.
- `Scenario.kind == "scenario"` requires `examples == []`.
- `ValidationError.message` is human-readable, attaches `field` (dotted path, e.g., `scenario.steps[2].text`).
- Tag values comply with the character rules in §4 (non-empty, no whitespace, ASCII-printable, no `,`).

Deterministic rules:

1. Feature-level tags on one line, space-separated, before `Feature:`, each prepended with `@`.
2. `Feature: <description>` — every real `\n` in the model is encoded as the literal two-character sequence `\n` here, so the line is always single-line on disk.
3. Blank line.
4. If `background.steps` non-empty: `  Background:` (2-space indent) + steps at 4-space indent, then blank line. Empty background: skip entirely.
5. The scenario (exactly one):
   - Tags on one line at 2-space indent (each prepended with `@`; skipped when empty).
   - `  Scenario:` or `  Scenario Outline:` + name (2-space indent). Name may be empty; in that case write just `  Scenario:` or `  Scenario Outline:`.
   - Steps at 4-space indent: `<Keyword> <text>`.
   - Step DataTable (if present): rows at 6-space indent, pipe-separated, **column-aligned** to the widest cell per column (post-escape, post-trim).
   - For outlines, each `Examples` block:
     - Tags at 4-space indent (each prepended with `@`; skipped when empty).
     - `    Examples:` at 4-space indent (name appended only if non-empty).
     - Header + rows at 6-space indent, pipe-separated, column-aligned.
6. Cells are first stripped of leading/trailing whitespace, then escaped (`\` → `\\`, `|` → `\|`), then padded with spaces for column alignment. Empty cell → single space.
7. File ends with exactly one trailing newline.
8. Always UTF-8 + LF (no CRLF on any platform).
9. Step text is trimmed of leading/trailing whitespace before being written (same policy as table cells).
10. Tag values are de-duplicated within each tag list before being written (order preserved, first occurrence kept).

Indent summary: `Feature:` 0 · `Background:` / `Scenario:` 2 · steps 4 · `Examples:` 4 · examples rows 6.

Idempotence target: `serialize(parse(serialize(parse(x)))) == serialize(parse(x))`. The first round-trip may change the file (canonicalization).

### 5.3 Public API
```
parse_feature(source: str) -> Feature
serialize_feature(feature: Feature) -> str
class GherkinParseError(Exception):
    line: int
    column: int
    message: str       # human-readable
class ValidationError(Exception):
    field: str         # dotted path
    message: str       # human-readable
```

---

## 6. Storage (`app/storage.py`)

Owns all FS access. Constructor: data root (default `./project/`).

### 6.1 Path discipline
- Public methods take **logical paths** (`project_name / module_name / file_name`), never raw FS paths.
- Internal `_resolve(parts) -> Path` asserts the result is inside the data root via `Path.resolve()` + `is_relative_to(root.resolve())`. Rejects `..`, absolute parts, empty parts.
- `parts` may be supplied as a string with `/` separator or as a list of segments; both forms are normalized via `_resolve`.
- Forbidden chars in any name segment: `/ \ : * ? " < > |` plus control chars.
- `.feature` extension auto-appended to file names on create if absent; rejected if a different extension is given. Extension comparison is **case-insensitive** (`.FEATURE`, `.Feature` and `.feature` are all treated as the canonical `.feature`).

### 6.2 Operations
```
list_tree() -> dict                           # full tree at any depth; entries flagged type=folder|feature|other; orphan temp files matching the atomic-write regex are filtered out
list_root() -> list[str]                      # depth-0 folder names (projects), OS listing order
list_folder(parts) -> FolderListing           # depth 0 or 1; see below
read_feature(parts) -> Feature                # raises GherkinParseError
write_feature(parts, feature: Feature) -> None
read_raw(parts) -> str
write_raw(parts, text: str) -> None           # parses first; rejects invalid via 422
create_folder(parts) -> None                  # depth-2+ rejected
rename_folder(parts, new_name) -> None        # same parent only
delete_folder(parts) -> None                  # idempotent on missing
create_file(parts, description: str) -> None  # writes Feature + placeholder Scenario
rename_file(parts, new_name) -> None          # same parent only
delete_file(parts) -> None                    # idempotent on missing
duplicate_file(parts, new_name) -> None       # same parent only
search(query, scope, match, case_sensitive) -> list[SearchHit]
cleanup_orphan_temp_files() -> int            # called at app boot; returns deleted count
```

`FolderListing` shape (three variants):
- Root: `{ kind: "root", projects: [folder_name, ...] }` — returned by `GET /api/folders/contents` (no path).
- Depth-0 (project): `{ kind: "project", modules: [folder_name, ...] }` (OS listing order).
- Depth-1 (module): `{ kind: "module", features: [{file_name, description, tags}, ...] }` (OS listing order, `.feature` only; extension match case-insensitive).
- Depth-2+ folders are visible in the tree but never queried for folder listings.

`SearchHit` shape: `{ file_path: str, description: str, matched_field: Literal["description","tag"], match_value: str }`.

Rename and duplicate are **same-parent only**. Cross-module moves require `delete_file` + `create_file` (or external move; watcher picks it up).

No `move_scenario` operation — with one scenario per file, moving a scenario equals moving the file.

### 6.3 Atomic writes
- Write to `<target>.tmp.<pid>.<uuid>` in the same directory (uuid = hex digits only).
- `fsync` → `os.replace` over the target.
- Cleanup of temp on any error.
- Watcher path filter ignores any path matching the regex `.+\.tmp\.\d+\.[0-9a-f]+$` (see §7).
- In addition, every write calls `watcher.note_write(target_path)` immediately before the rename and again immediately after, for defense in depth.
- `cleanup_orphan_temp_files()` recursively scans the data root for files matching the regex and deletes them. Called at app boot (see §2 startup sequence).

### 6.4 Uniqueness
- Validated against existing siblings before any write. Error class: `NameConflictError`.
- Comparison is **case-insensitive** (`str.casefold()`) and **scoped to the same parent only**:
  - File uniqueness: only against `.feature` files in the same module.
  - Folder uniqueness: only against folders in the same parent folder.

---

## 7. Watcher + Pub/Sub (`app/watcher.py`, `app/sse.py`)

Owns:
- `watchdog.observers.Observer`, recursive on data root, started at app boot via the `create_app` factory; stopped on app teardown.
- Event normalization to `{kind, path, is_dir, ts}` where `kind ∈ {created, deleted, modified, moved}`. For `moved`, `path` is the destination and `src_path` is included.
- **Path filter** dropped early in the consumer pipeline: any event whose path matches the regex `.+\.tmp\.\d+\.[0-9a-f]+$` (atomic-write temp files) is ignored.
- **`recent_writes`** TTL dict (`dict[normalized_path, expiry_monotonic_ts]`, TTL 500 ms):
  - Public function `note_write(path: str | Path)` — called by `storage` before and after every write.
  - Watcher consumer drops any incoming event whose normalized path is in the set.
  - Expired entries cleared lazily on read (no background sweep).
- **Debounce window**: 50 ms per path. Coalescing emits **a single event with the most recent kind seen in the window**.
- In-memory `PubSub`:
  - `subscribe() -> queue.Queue` (bounded; overflow discards the oldest event — the tree refetches the whole tree on every event, so missed events are harmless).
  - `publish(event)` — thread-safe.

SSE endpoint (`GET /api/events`, in `app/sse.py`):
- `text/event-stream`; subscribes to pubsub.
- Emits `event: change\ndata: <json>\n\n` per event.
- Heartbeat comment every 15 s.
- Clean teardown on client disconnect.

---

## 8. HTTP API (`app/server.py`)

**Content type for request bodies**: all non-raw endpoints accept `application/json`. The two raw endpoints accept `text/plain`.

**Content negotiation for responses**: HTML partial (default, for HTMX) or JSON (`Accept: application/json` or `?format=json`).

`parent` parameters in request bodies are **string paths** with `/` separator (`"proj1/mod1"`). Root parent is the empty string `""`.

### 8.1 Tree & events
- `GET /api/tree` — entire tree at any depth.
- `GET /api/events` — SSE.

### 8.2 Folders
- `GET /api/folders/contents` — root listing (depth-0 / projects). No path segment.
- `GET /api/folders/<path:p>/contents` — folder listing at depth 0 or 1. 400 if `<path:p>` is at depth ≥ 2.
- `POST /api/folders` — body `{ parent, name }`. Root parent → project; depth-1 parent → module. Depth-2+ parent → 400.
- `PATCH /api/folders/<path:p>` — body `{ name }` (rename). **Same parent only.** Any depth allowed.
- `DELETE /api/folders/<path:p>` — recursive; idempotent; returns **204 No Content** on success.

### 8.3 Files (test cases)
- `POST /api/files` — body `{ parent, file_name, description }`. **`parent` must be a module (depth-1)**; 400 otherwise. Both `file_name` and `description` are required and non-empty. Creates with empty `Background` + placeholder `Scenario(kind="scenario", name="")`. The scenario name is intentionally empty by default; not auto-derived from the feature description.
- `GET /api/files/<path:p>` — structured JSON payload (Feature `to_dict()`; see §16).
  - If the file extension is not `.feature` → returns 415 with `{ error: { code: "unsupported_type", message: "File type not supported" } }`. UI renders an "unsupported" page.
- `PATCH /api/files/<path:p>` — full `Feature` payload (no diff).
- `DELETE /api/files/<path:p>` — idempotent; returns **204 No Content** on success.
- `PATCH /api/files/<path:p>/rename` — body `{ file_name }`. **Same parent only.**
- `POST /api/files/<path:p>/duplicate` — body `{ file_name }`. **Same parent only.**
- `GET /api/files/<path:p>/raw` — `text/plain`.
- `PUT /api/files/<path:p>/raw` — `text/plain`; parser run; 422 on parse error.

No `scenarios/move` endpoint (one scenario per file). Cross-module moves require delete + create.

### 8.4 Search
- `GET /api/search?q=&scope=&match=&case=`
  - `scope`: `all` | `project:<name>` | `module:<proj>/<mod>`
  - `match`:
    - `text` — matches `Feature.description` only.
    - `tag` — matches `Scenario.tags` only.
  - `case`: `true` | `false` (default false; case-insensitive)
- Response (JSON shape; see §16): `{ hits: [SearchHit, ...] }`.
- `match_value` semantics: for `match=text`, it is the **user's query string** (echoed back for the result row badge); for `match=tag`, it is the matched tag value (without `@`). No snippet rendering in v1.
- UI behavior (see §9.6):
  - 0 hits → empty-state message.
  - 1 hit → open that file directly in the editor.
  - ≥ 2 hits → list view in main pane.

### 8.5 Errors
Uniform JSON body: `{ error: { code, message, details? } }`. HTTP codes:
- 400 — bad request / invalid name / disallowed depth / cross-parent rename attempt
- 404 — not found
- 409 — `NameConflictError`
- 415 — unsupported file type (non-`.feature`)
- 422 — `GherkinParseError` or `ValidationError` (`message` is human-readable)
- 500 — unexpected

---

## 9. UI (Jinja2 templates)

### 9.1 Layout (`templates/base.html`)
- Tailwind v4 Browser CDN (`https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4`).
- HTMX (`https://unpkg.com/htmx.org@2`) + HTMX SSE extension (`https://unpkg.com/htmx-ext-sse@2`).
- Top bar: app title, search input, scope select, match select, case toggle. The search input fires a request on **Enter** or after a **300 ms** typing pause (whichever first); empty queries do not fire.
- Two-pane below: `aside.tree` (left, ~280 px) and `main` (right, fills).
- Global `beforeunload` handler: warns when there is an unsaved buffer in the file editor.

### 9.2 Tree (`templates/tree.html`)
- Nested `<ul>` rendered server-side; collapsible. Renders **any depth** of folders and files.
- `hx-ext="sse"`, `sse-connect="/api/events"`, `sse-swap="change"` → on each event, refetch `/api/tree` and swap.
- Click behavior:
  - **Project (depth-0) folder**: opens project view in main pane.
  - **Module (depth-1) folder**: opens module view in main pane.
  - **Sub-folder (depth ≥ 2)**: expands/collapses in the tree only — main pane is unchanged. No folder-view representation.
  - **`.feature` file at any depth**: opens in the file editor.
  - **Non-`.feature` file**: opens the "unsupported" page.
- Per-node actions: rename (same-parent only), delete (any folder or file in the tree); duplicate (`.feature` files only); create child folder not offered on depth-2+ nodes.

### 9.3 Folder views (`templates/project_view.html`, `templates/module_view.html`)

**Empty data root**: main pane shows "No projects yet" + **Create project** button.

**Project view** (depth-0 folder selected):
- Heading: project name.
- Table: `module_name` (one column), default OS listing order. Click row → drill into module view.
- Toolbar: `+ New module`.

**Module view** (depth-1 folder selected):
- Heading: breadcrumb `<project> / <module>`.
- Table: `file_name | description | tags`. `.feature` files only. Tags rendered with `@` prefix in chips. The `description` column shows only the **first line** of `Feature.description`, truncated with an ellipsis if longer than the column width; multi-line descriptions never expand the row.
- Default order: OS listing order. Click column headers to sort client-side.
- Click row → opens file editor.
- Toolbar: `+ Create test case` (modal requires `file_name` + `description`).

Sub-folders (depth ≥ 2) have no folder view — clicking them in the tree only expands/collapses the tree node.

### 9.4 File editor (`templates/file_view.html` + partials)
- Header: breadcrumb, `file_name` (with rename action), **Save** button, dirty indicator, **Structured / Raw** tab.
- **No auto-save.** Edits live in a client-side buffer until the user clicks Save. `beforeunload` warns on dirty buffers.
- The **Save** button is also disabled (independently of the §9.5 banner) whenever `Feature.description` is empty or whitespace-only in the buffer.

**Save-click cleanup pass** (runs before validation / API call):
1. Drop any step (in Background or Scenario) whose `text` is empty/whitespace-only.
2. Drop any examples row consisting entirely of empty cells (header preserved).
3. If the buffer becomes invalid after cleanup (e.g., outline with no examples rows remaining), show inline error and abort the save (no API call).
4. The cleanup is silent for empty rows/steps; subsequent save proceeds normally with the cleaned payload.
5. The cleanup **does not** rewrite step keywords. After dropping steps, the remaining sequence may contain an orphan `And`/`But` (one whose preceding `Given`/`When`/`Then` was removed). This is preserved as-is on disk; downstream consumers like `behave` will resolve the orphan against whatever logical predecessor remains.

**Structured tab** — single scenario layout:
- `description` multi-line textarea (real newlines end-to-end; encoding to `\n` literal happens inside `gherkin_io`).
- Feature tags chip input. Chips render as `@tag`; the input strips a leading `@` if the user types it. Invalid characters (whitespace, non-ASCII, `,`) are rejected at type time with an inline message; valid bare strings are stored in the buffer. Pressing space, comma, or Enter commits the current chip.
- Background card (collapsible when empty); steps editable with drag-handle reorder.
- Scenario card:
  - Kind toggle (Scenario / Outline). Switching to Outline auto-creates the default examples table `[{ header: ["col1"], rows: [] }]` if none exists. Switching back to Scenario refuses if the current examples table differs from the default by exact case-sensitive comparison (header values, count, and any rows); the user must clear first.
  - Optional scenario name input (single-line `<input>`; may be empty).
  - Tags chip input (same rules as feature tags).
  - Steps list — each step: keyword `<select>` (Given / When / Then / And / But, all five available at every position), text input (single-line), drag-handle for reorder, "Add data" toggle for the inline DataTable.
    - Toggling **off** when the table is **non-empty**: confirm prompt ("Discard data table?"). Toggling off when empty: no prompt.
- **Grid editors** (DataTable + Examples) support: add column, remove column, add row, remove row, reorder rows via drag handle. Column reorder is **not** supported in v1.
  - Newly added columns default to header name `col<N>` where `N` is the smallest positive integer not already present in the header (e.g., adding to `["col1", "col3"]` produces `"col2"`). The user can rename immediately.
- **Visual distinction** between step-level inline DataTable ("data the step consumes") and scenario-level Examples table ("parameterization for `<placeholders>`"): different border, label, and color band.

**Raw tab**: `<textarea>` with raw `.feature` content; "Save raw" button. On submit, the server parses (via `PUT /raw`) and returns 422 with line/column/message on failure; UI shows error inline. Save blocked until the server accepts.

**Save flow** (three cases):
- If `file_name` changed → `PATCH /api/files/<old>/rename` first.
- If content changed → `PATCH /api/files/<current-or-new-path>` with the cleaned-up Feature payload.
- If both changed → rename PATCH first, then content PATCH at the post-rename URL.
- Any non-2xx aborts the chain; the editor stays on its current path with the dirty buffer intact.

### 9.5 External rename / delete / ancestor-rename of the open file
Detection: the SSE stream delivers a `moved` or `deleted` event whose path matches the currently open file (or one of its ancestor folders).

While the banner is active, the editor's **Save** button is **disabled**. The dirty buffer is preserved.

- **Open file was `moved`** (rename of the file or rename of any ancestor folder):
  - Banner: "This file moved on disk to `<new path>`."
  - Actions: **Save** (writes the buffer to `<new path>` via the §9.4 save flow; re-enables Save), **Discard** (drops the buffer and reloads tree).
- **Open file was `deleted`** (file or any ancestor folder gone):
  - Banner: "This file was removed on disk."
  - Actions:
    - **Save as…** — modal that asks **only for a new `file_name`** in the **same module** as the original. Client `POST /api/files` with the buffer's `description` to that module, then `PATCH` the new path with the rest of the buffer. If the module itself was also deleted, the modal substitutes a flat dropdown of all currently existing modules in the data root; if none exists, Save-as is disabled and only Discard remains.
    - **Discard** — drops the buffer and reloads tree.

### 9.6 Search results (`templates/search_results.html`)
- Renders in main pane.
- 0 hits → "No matches" message.
- 1 hit → client navigates straight to the file editor for that hit (no list intermediate).
- ≥ 2 hits → list view. Each row always shows `file_path` + the first line of `description` (truncated with ellipsis if long), plus a small badge indicating `matched_field` (`description` or `tag`) and the `match_value`. Clicking the row opens the file editor.

### 9.7 Unsupported-file view (`templates/unsupported.html`)
- Reached by opening any non-`.feature` file from the tree.
- Renders a centred message: "File type not supported" + the file's path.

### 9.8 Static assets
- `static/app.js`: table sort, chip input wiring, grid keyboard nav, dirty-buffer tracking, `beforeunload` hook, drag-handle reorder helper, Save-click cleanup pass.
- `static/app.css`: only if a Tailwind utility cannot cover it.

---

## 10. File Layout

```
tms/
├── app/
│   ├── __init__.py            # create_app factory; orphan scan; wires watcher
│   ├── __main__.py            # `python -m app`
│   ├── server.py              # Flask blueprint(s) + route handlers
│   ├── storage.py             # FS CRUD, atomic writes, search, orphan cleanup
│   ├── gherkin_io.py          # parse + canonical serialize (owns description + cell encoding)
│   ├── watcher.py             # watchdog observer + pubsub + recent_writes / note_write + tmp filter
│   ├── sse.py                 # SSE response helper
│   ├── models.py              # dataclasses + to_dict / from_dict
│   ├── errors.py              # exception types, HTTP mapping
│   ├── templates/
│   │   ├── base.html
│   │   ├── tree.html
│   │   ├── project_view.html
│   │   ├── module_view.html
│   │   ├── file_view.html
│   │   ├── search_results.html
│   │   ├── unsupported.html
│   │   └── _partials/
│   └── static/
│       ├── app.js
│       └── app.css
├── project/                   # data root (created on first run; .gitkeep)
├── requirements.txt
├── README.md
├── AGENTS.md
└── PLAN.md
```

No `services.py` — routes call `storage` directly.

---

## 11. Concurrency & Local-only Safety

- Flask in threaded mode (default).
- **Bind host**: `127.0.0.1` only. No external interfaces, no auth, no CSRF or host-header checks.
- Watcher runs in its own observer thread; stopped via `Observer.stop()` + `Observer.join()` on app teardown.
- Storage operations on the same file are serialized with per-path `threading.Lock` held in a `WeakValueDictionary[str, Lock]`.
- SSE generator yields from a per-request queue; no shared cursor state between clients.
- Save conflict policy: **last-write-wins** (UI overwrites disk silently on Save). Watcher still refreshes the tree.
- **Single-user, single-tab** assumption: races between a folder rename and a child-write (or two simultaneous writes) cannot occur in normal use and are not defended against in v1.

---

## 12. Do-phase Step Plan (14 steps)

Each step ends with a pause for a "next" signal. Acceptance is judged by the step's stated outcome.

1. **Scaffold + deps**: `app/` skeleton, `__init__.py` (with orphan-temp scan on boot), `__main__.py`, empty modules, `requirements.txt` (gherkin-official `>=32,<33`), `static/`, `templates/base.html` with pinned CDN URLs, `project/.gitkeep`. App boots on `127.0.0.1`, serves an empty page on `/`.
2. **Models** (`models.py`): dataclasses + `to_dict` / `from_dict` round-trip. Single-scenario `Feature`. Single-line validators. Outline-examples invariant. Cell text held unescaped. Tag values held without `@`.
3. **Gherkin parser** (`gherkin_io.parse_feature`): newline normalization, AST → model; rejects `Rule:` and multi-scenario files; auto-fills placeholder scenario when zero; drops steps with non-canonical keywords; concatenates body description; decodes literal `\n` → real newline; unescapes cell `\|` and `\\`; strips leading `@` from tags.
4. **Gherkin serializer** (`gherkin_io.serialize_feature`): model → canonical text per §5.2; pre-write validation (including non-empty step text); encodes real newlines → literal `\n`; cell whitespace trim + `\` and `|` escape + column alignment; prepends `@` to tags.
5. **Storage – reads**: `list_tree`, `list_root`, `list_folder` (project / module variants), `read_feature`, `read_raw`.
6. **Storage – file writes**: create / rename / delete / duplicate (same-parent); `write_feature`, `write_raw`; atomic write helper; case-insensitive uniqueness per parent; `note_write` integration; `cleanup_orphan_temp_files()`.
7. **Storage – folder writes**: create (depths 0/1 only) / rename (same-parent) / delete (any depth, idempotent).
8. **Storage – search**: `match=text` over `Feature.description`, `match=tag` over `Scenario.tags`, scoped, case-insensitive by default; `SearchHit` shape per §16.
9. **Watcher + pubsub + SSE** (`watcher.py` + `sse.py`): observer thread, regex-tightened temp path filter, 50 ms debounce (latest kind wins), `recent_writes` TTL set + `note_write()`, heartbeat, clean teardown.
10. **API routes – tree, folders, SSE, search**: wire to storage; HTML + JSON negotiation; `GET /api/folders/contents` (root) + depth-aware `GET /api/folders/<path>/contents`.
11. **API routes – files**: structured + raw + duplicate + rename; 415 on non-`.feature` open; 422 on parse/validation error.
12. **UI – shell + tree**: `base.html`, `tree.html`, SSE wiring, top-bar search inputs, empty-data-root placeholder.
13. **UI – folder views + unsupported page**: `project_view.html` (modules list + New module), `module_view.html` (test case table with `@`-prefixed tag chips + Create test case, OS-order default + click-to-sort), `unsupported.html`.
14. **UI – file editor + Save-as flow + search results + polish**: structured editor (single scenario, reorder handles, grid add/remove column + row, kind toggle with strict-default rule, DataTable vs Examples visual distinction, Save-click cleanup pass, tag chip with `@`-prefix render), Raw tab (server-side parse via `PUT /raw`), Save flow (rename → PATCH content), banner + Save-as flow for external rename/delete (same-module first, module dropdown fallback), `beforeunload` dirty-buffer warning, search results page (0 / 1 / ≥2 hit modes).

---

## 13. Risks & Documented Tradeoffs

- **No tests** + canonical reserialization = any serializer bug can silently rewrite user files on save. `gherkin_io` is structured so tests can be added later without refactor.
- **Comments, blank lines, DocStrings lost** on every save. Documented in `README.md`.
- **Non-canonical step keywords silently dropped** on read (e.g., non-English step keywords, typos). Data-loss risk for users importing externally-authored files. Documented in `README.md`.
- **Empty-text steps silently removed** at Save-click cleanup. Intentional UX simplification; documented in `README.md`.
- **Literal `\n` in description** round-trips as a real newline. Documented in `README.md`.
- **First-save reformat**: externally-authored files with a multi-line body description block become a single-line `Feature:` with `\n` literals on first save (no content loss, just reformat). Documented in `README.md`.
- **Editor swap files / dotfiles** (`.swp`, `~`, `.#…`) are not filtered from watcher events in v1; the tree may flicker briefly when external editors save. Acceptable for v1.
- **Large data roots**: tree is refetched whole on every FS event. Fine for hundreds of features; degrades beyond ~10k files. Acceptable for v1.
- **Multiple tabs**: out of scope; if opened, last-write-wins still applies.
- **One scenario per file** is a hard invariant; multi-scenario files imported from elsewhere will fail to open and must be split externally.
- **Sub-folders below modules** are visible in the tree only — no first-class management UI.
- **No column reorder** in grid editors (only row reorder). Columns can be added/removed.
- **Cross-module move** of a file requires delete + create. No move API.
- **Search scope** is narrow: `text` matches only `Feature.description`; `tag` matches only `Scenario.tags`. Step text, feature tags, and examples tags are not searched in v1.
- **Orphan `And`/`But` after cleanup**: the Save-click cleanup may drop a `Given`/`When`/`Then` and leave a following `And`/`But` with no canonical predecessor in the file. Preserved as-is; tools like `behave` resolve it to the nearest logical predecessor. Documented in `README.md`.
- **Tag character restrictions**: tag values must be non-empty, whitespace-free, ASCII-printable, and not contain `,`. Stricter than Gherkin's official rules (which allow more). External `.feature` files with non-conforming tags will fail validation on first save. Documented in `README.md`.

---

## 14. Resolved Decisions Log

| Topic | Decision |
| --- | --- |
| Backend framework | Flask |
| Frontend | Jinja2 + HTMX 2 (+ SSE ext) + Tailwind v4 Browser CDN; all CDN URLs pinned |
| Parser | `gherkin-official >=32,<33` (read); custom serializer (write) |
| Python | 3.12+ |
| Tests in v1 | None |
| Data root | `./project/` (single root) |
| Auth / multi-user | None (single-user, single-tab, localhost-only) |
| Host binding | `127.0.0.1` only; no host-header / CSRF hardening |
| Scenarios per file | Exactly one (placeholder injected if missing on read) |
| `Scenario.name` | Optional, single-line, may be empty; not auto-derived from feature description |
| `Step.text` | Required non-empty at write; empty steps removed by Save-click cleanup |
| Outline default examples | `[ExamplesTable(header=["col1"], rows=[])]` on creation or kind switch |
| Outline invariant | `len(examples) >= 1` at write time |
| Kind toggle Outline→Scenario | Refused if examples table differs from default (case-sensitive); user must clear first |
| Bulk operations | Duplicate test case only (move-scenario dropped) |
| Cross-parent rename / move | Not supported in v1 (delete + create) |
| Reorder | Background steps, Scenario steps, Examples rows, DataTable rows — within file only, via drag handles. Columns not reorderable. |
| Background | Always in model; omitted from disk when empty |
| Description encoding | Real `\n` end-to-end in API/UI; serializer encodes to literal `\n`, parser decodes back |
| Multi-line body description on read | Concatenated into `Feature.description` with `\n` separator |
| Newline normalization on read | `\r\n` and lone `\r` normalized to `\n` before parse |
| Cell escaping | Serializer escapes `\`→`\\` then `|`→`\|`; parser unescapes; cell whitespace trimmed at write |
| Tag storage | Model holds tags WITHOUT leading `@`; serializer prepends, parser strips; UI chips render with `@` prefix |
| Step keywords | Given, When, Then, And, But — no ordering restriction |
| Non-canonical step keywords | Silently dropped on read (data-loss risk documented) |
| `Rule:` blocks | Rejected on parse |
| Zero-scenario file on read | Placeholder scenario auto-injected (lenient) |
| DocStrings / comments / blank lines | Parsed and discarded on read |
| Name uniqueness | Case-insensitive (`casefold`), per parent only (files in same module; folders in same parent folder) |
| Filename / folder name chars | Any except `/ \ : * ? " < > |` and control chars |
| `.feature` extension | Auto-appended on create; rejected if another extension is given |
| Indentation | Feature 0 · Background/Scenario 2 · steps 4 · Examples 4 · Examples rows 6 |
| Save model | Explicit Save button; no auto-save; `beforeunload` warns on dirty buffer |
| Save conflict | Last-write-wins |
| Save when both rename + content changed | Rename first, then content PATCH at new URL; abort on first failure |
| Save click cleanup | Drops empty-text steps + all-empty-cell examples rows before validation |
| Open-file external rename | Banner: Save (to new path) / Discard; Save disabled meanwhile |
| Open-file external delete | Banner: Save as… (same-module file_name only; module dropdown fallback if module gone; Discard-only if data root empty) / Discard |
| Ancestor folder rename with open buffer | Same banner pattern as file rename, resolved against new ancestor |
| Self-write suppression | Watcher path filter on regex `.+\.tmp\.\d+\.[0-9a-f]+$` + `note_write(path)` TTL set; storage calls `note_write` before/after every write |
| Orphan temp cleanup | App boot scans data root and deletes any orphan atomic-write temp files |
| Debounce | 50 ms per path; emits a single event with the latest kind seen in the window |
| Non-`.feature` files | Visible in tree only; folder table hides them; opening shows "unsupported" page |
| Folder depth in UI | Tree any depth; folder view depths 0–1 only; depth ≥ 2 has no main-pane representation |
| Folder creation depth in API | Depth 0 (project) and 1 (module) only; deeper rejected |
| Folder rename / delete depth in API | Any depth; rename same-parent only |
| Empty data root | "No projects yet" placeholder + Create project button |
| Folder listing default order | OS listing order; column-header click sorts client-side |
| Root contents endpoint | `GET /api/folders/contents` |
| `parent` in request bodies | String path with `/` separator; root = `""` |
| Request body content-type | `application/json` for all non-raw endpoints; `text/plain` for `/raw` |
| Search `match=text` | `Feature.description` only |
| Search `match=tag` | `Scenario.tags` only |
| Search results UX | 0 hits → empty state; 1 hit → open directly; ≥2 hits → list view |
| `SearchHit` shape | `{file_path, description, matched_field, match_value}` |
| Concurrency | Single-user single-tab assumed; folder-rename vs child-write race not defended against |
| Error messages | Human-readable; no error codes in messages (HTTP status carries the kind) |
| `services.py` | Not introduced |
| Search input firing | On Enter or after 300 ms typing pause; empty queries do not fire |
| Description column in lists | Single first line, truncated; never expands row height |
| Save button enablement | Disabled when description is empty/whitespace, in addition to §9.5 banner disablement |
| Save-click cleanup vs keywords | Does not rewrite step keywords; orphan `And`/`But` possible after dropping empty steps |
| Search result row | Always shows `file_path` + first-line description + `matched_field` badge + `match_value` |
| Tag character rules | Non-empty, whitespace-free, ASCII-printable, no `,`; duplicates de-duplicated at write |
| `list_tree` temp filter | Orphan atomic-write temp files filtered out by same regex as watcher |
| `FolderListing` root variant | `{kind:"root", projects:[...]}` returned by `GET /api/folders/contents` |
| Tree JSON `depth` field | On folder entries only; file entries omit it |
| Grid new-column default header | `col<N>` where N is the smallest unused positive integer in the header |
| Successful DELETE response | 204 No Content (files and folders) |
| `match_value` in search hits | Text mode → user's query echoed; tag mode → matched tag value without `@` |
| `.feature` extension comparison | Case-insensitive (`.FEATURE`, `.Feature`, `.feature` all accepted) |
| Step text trim on write | Serializer strips leading/trailing whitespace from step text (same as cells) |

---

## 15. Change Control

This plan is the source of truth for implementation. Changes during Do/Check/Act require explicit approval and an updated revision of this file.

When `PLAN.md` changes materially, `README.md` and `AGENTS.md` are reviewed in the same session for consistency.

---

## 16. Wire Shapes (Appendix)

Canonical JSON shapes returned and accepted by the API. `to_dict()` on the models produces these exactly.

### 16.1 `Step.to_dict()`
```json
{
  "keyword": "Given",
  "text": "I am on the login page",
  "data_table": null
}
```
`data_table` is `null` when absent, else `[["h1","h2"], ["v1","v2"], ...]`.

### 16.2 `ExamplesTable.to_dict()`
```json
{
  "tags": ["smoke"],
  "name": "",
  "header": ["username", "password"],
  "rows": [["admin", "admin"], ["user1", "pwd1"]]
}
```

### 16.3 `Scenario.to_dict()`
```json
{
  "kind": "outline",
  "name": "",
  "tags": ["login"],
  "steps": [/* Step */],
  "examples": [/* ExamplesTable */]
}
```

### 16.4 `Background.to_dict()`
```json
{ "steps": [/* Step */] }
```

### 16.5 `Feature.to_dict()`
```json
{
  "description": "User login\nMore description...",
  "tags": ["auth"],
  "background": { "steps": [] },
  "scenario": { /* Scenario */ }
}
```

### 16.6 `GET /api/tree` response
```json
{
  "root": {
    "type": "folder",
    "name": "",
    "children": [
      {
        "type": "folder",
        "name": "proj1",
        "depth": 0,
        "children": [
          {
            "type": "folder",
            "name": "mod1",
            "depth": 1,
            "children": [
              { "type": "feature", "name": "login.feature", "path": "proj1/mod1/login.feature" },
              { "type": "other",   "name": "notes.txt",     "path": "proj1/mod1/notes.txt" }
            ]
          }
        ]
      }
    ]
  }
}
```
`type` ∈ `{"folder", "feature", "other"}`. `depth` is included on **folder entries only** (first-level folders are depth 0; root wrapper has no depth). File entries (`feature`/`other`) carry `path` instead; their depth is implicit from their position in the tree.

### 16.7 `GET /api/folders/<path>/contents` response
Two variants per `FolderListing` (§6.2):
- Depth-0 (project): `{ "kind": "project", "modules": ["mod1", "mod2"] }`.
- Depth-1 (module): `{ "kind": "module", "features": [{"file_name": "login.feature", "description": "...", "tags": ["auth"]}, ...] }`.

`GET /api/folders/contents` (root) returns: `{ "kind": "root", "projects": ["proj1", "proj2"] }`.

### 16.8 `GET /api/search` response
```json
{
  "hits": [
    {
      "file_path": "proj1/mod1/login.feature",
      "description": "User login",
      "matched_field": "description",
      "match_value": "login"
    }
  ]
}
```
`matched_field` ∈ `{"description", "tag"}`. `match_value`: for `text` mode, the user's query string echoed back; for `tag` mode, the matched tag value (without `@`).

### 16.9 Error response (uniform)
```json
{ "error": { "code": "name_conflict", "message": "A file with that name already exists.", "details": { "field": "file_name" } } }
```
`code` values: `bad_request`, `not_found`, `name_conflict`, `unsupported_type`, `parse_error`, `validation_error`, `internal_error`.
