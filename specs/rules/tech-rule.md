# Technical rules

Cross-cutting engineering rules every feature spec under
`/specs/features` must satisfy. Summarised from `PLAN.md`; refer
there for rationale and edge cases. Where `DONE.md` records a change
that supersedes `PLAN.md` (e.g., folder depth), the rule below
reflects the current state.

## Stack & runtime

- Python 3.12+ · Flask `>=3,<4` · `gherkin-official >=32,<33` ·
  `watchdog >=4,<7`.
- Frontend: Jinja2 + HTMX 2 (+ SSE ext) + Tailwind v4 browser CDN;
  all CDN URLs pinned in `templates/base.html`. No build step.
- Bind `127.0.0.1` only. No auth, CSRF, or host-header hardening.
- Threaded Flask. Per-path `_PathLock` (a weakref-able wrapper
  around `threading.Lock`, kept in a `WeakValueDictionary` keyed by
  the posix path string) serialises writes to the same file.
  Multi-target operations (rename / move / duplicate) acquire src
  and dst locks in sorted order to avoid deadlock.
- Single-user, single-tab assumption; save conflict = last-write-wins.

## Process (PDCA)

- Investigate → Plan → Do → Check → Act with explicit signals between
  phases and between Do-steps.
- No code in Investigate / Plan. Act fixes only — no new features.

## Module boundaries

- Routes (`app/server.py`) know HTTP only; never touch the FS.
- `app/storage.py` is the sole FS I/O module.
- `app/gherkin_io.py` is pure: text ↔ model, no I/O.
- `app/watcher.py` owns the observer, pubsub, `recent_writes` TTL set,
  and the temp-file path filter; SSE subscribes per request.
- No `services.py` layer — routes call `storage` directly.

## Filesystem

- Data root: `./project/`. Recursive `watchdog` observer started in
  `create_app`, stopped on app teardown.
- Storage takes logical path *parts* only. `_resolve` enforces the
  resolved path stays inside the data root; rejects `..`, absolute
  parts, empty parts.
- Forbidden chars in any name segment: `/ \ : * ? " < > |` plus
  control chars.
- `.feature` extension auto-appended on create; rejected if another
  extension is supplied. Comparisons are case-insensitive
  (`.FEATURE`, `.Feature`, `.feature` are all canonicalised).
- Folder nesting: 1..10 levels under the data root
  (`MAX_FOLDER_DEPTH = 10`, post-DONE.md). `.feature` files may live
  at depth 2..10.
- Atomic writes: `<target>.tmp.<pid>.<uuid>` (uuid = hex digits) →
  `fsync` → `os.replace`. Cleanup on error.
- Boot-time orphan scan deletes any leftover temp files matching
  `.+\.tmp\.\d+\.[0-9a-f]+$`.
- All files written UTF-8 + LF (no CRLF on any platform).

## Watcher + SSE

- Drop any event whose path matches the temp-file regex above.
- Self-write suppression: `Storage._mark_write(target)` records the
  written path (plus its immediate parent dir, to swallow the
  bubbled `DirModifiedEvent` from POSIX mtime propagation) into a
  TTL dict; TTL is `RECENT_WRITE_TTL_SECONDS = 0.5` (500 ms). The
  watcher consults `storage.was_recently_written(path)` and drops
  any matching event. Mark happens **after** every successful write
  (atomic-write temp regex covers the in-flight window before that).
- Debounce: a single global `_DebouncedEmitter` coalesces a burst of
  surviving FS events into one publish after
  `DEBOUNCE_SECONDS = 0.1` (100 ms). Each new event resets the
  timer; only the last deadline fires.
- SSE payload: every coalesced publish emits the literal event name
  `"change"` with an empty `data:` line — there is no per-event
  `{kind, path, ...}` JSON. The UI reacts by refetching the whole
  tree (and any open file partial), so the watcher does not need to
  describe what changed.
- SSE heartbeat comment every 15 s
  (`HEARTBEAT_INTERVAL_SECONDS = 15.0`); clean teardown on client
  disconnect via `EventBus.unsubscribe` in the generator's
  `finally`.
- Pubsub queue per subscriber is **unbounded** (`queue.Queue()`); a
  `queue.Full` branch exists in `EventBus.publish` for safety but is
  unreachable today. Per-event refetch keeps event loss harmless if
  it were ever bounded.

## HTTP API

- Request bodies: `application/json` for non-raw endpoints;
  `text/plain` for `/raw` endpoints.
- Response content negotiation: HTML partial (HTMX default) or JSON
  (`Accept: application/json` or `?format=json`).
- Uniform error body:
  `{ error: { code, message, details? } }`. `code` ∈ {
  `bad_request`, `not_found`, `name_conflict`, `unsupported_type`,
  `parse_error`, `validation_error`, `internal_error` }. Messages are
  human-readable; HTTP status carries the kind.
- HTTP status codes: 400 / 404 / 409 / 415 / 422 / 500. Successful
  DELETE → 204 No Content.
- `parent` request fields: string paths with `/` separator; root
  parent is the empty string `""`.

## Gherkin I/O

- On read, normalise `\r\n` and lone `\r` → `\n` before passing
  source to the parser.
- `Feature.description`: model holds real-newline strings end-to-end.
  Serializer encodes every real `\n` as the literal two-char sequence
  `\n` on disk (so the `Feature:` line is single-line). Parser
  decodes literal `\n` back to real newlines and concatenates any
  multi-line body description block.
- Cell escaping (DataTable + Examples header/rows): serializer
  escapes `\` → `\\` then `|` → `\|`; parser unescapes. Per-cell
  whitespace is trimmed at write; output is column-aligned;
  empty cells render as a single space.
- Tags: model stores bare values (no `@`). Serializer prepends `@`;
  parser strips a leading `@`. UI chips render with `@`. Tag chars
  must be non-empty, whitespace-free, ASCII-printable, and exclude
  `,`. Duplicates within a list are de-duped at write (first
  occurrence kept).
- Step text trimmed at write (same policy as cells).
- Idempotence target:
  `serialize(parse(serialize(parse(x)))) == serialize(parse(x))`.
  The first round-trip may canonicalise the file.

## Name uniqueness

- Scoped to the same parent only — files within a module, folders
  within their parent folder.
- Enforced via `target.exists()` (`pathlib.Path.exists`), so
  case-sensitivity follows the host filesystem (macOS HFS+/APFS
  default and Windows NTFS treat `Foo.feature` and `foo.feature`
  as the same path; ext4 / APFS-case-sensitive treat them as
  distinct). There is no explicit `casefold` / `lower`
  normalisation in storage.
- File-extension comparison IS explicitly case-insensitive via
  `name.lower()` (`MyTest.FEATURE` is normalised on every
  filesystem).
- Conflicts surface as `NameConflictError` → HTTP 409.

## Wire shapes

- `to_dict` / `from_dict` on the dataclass models produce the
  canonical JSON shapes documented in `PLAN.md` §16. Endpoints
  consume and emit those shapes verbatim.
