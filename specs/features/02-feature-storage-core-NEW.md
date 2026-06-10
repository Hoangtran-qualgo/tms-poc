# 02 · Storage core

_Retroactive spec: documents the as-shipped behaviour. Source files:_
_the `app/storage/` package — `_core.py` (constants + free functions +_
_`_PathLock` + `_StorageBase`) plus the `_listing` / `_features` / `_enums` /_
_`_search` / `_folders` / `_runs` / `_reports` mixins composed in `__init__.py`._

## Summary

The only module in the app permitted to touch the filesystem. Owns
the data-root sandbox, path validation, atomic writes, per-path
locking, name-uniqueness checks, and self-write bookkeeping for the
watcher. Higher layers (HTTP routes, UI handlers) call `Storage`
methods with logical path *parts* and never see raw `Path` objects.

## Scope

In scope:

- Resolving logical path parts against the data root.
- Validating path segments (forbidden chars, depth caps).
- Atomic write recipe with crash-safe temp files and boot-time
  orphan cleanup.
- Per-path locking for same-target serialisation; sorted dual-lock
  acquisition for rename / move / duplicate.
- Self-write bookkeeping (path + parent dir + TTL) consumed by the
  watcher.
- Read / list helpers for tree, folder, and file enumeration.
- Search over feature contents (`Feature.description`,
  `Scenario.tags`).

Out of scope:

- Parsing or serialising `.feature` content (delegated to
  `01-gherkin-io`).
- File-system event observation (`03-watcher-and-sse`).
- HTTP error mapping (`05-testcase-crud`, `04-folder-crud`,
  `09-search`).

## Public surface

Module constants:

- `MAX_FOLDER_DEPTH = 10`.
- `RECENT_WRITE_TTL_SECONDS = 0.5`.
- `TEMP_FILE_RE = r".+\.tmp\.\d+\.[0-9a-f]+$"`.

Module function:

- `cleanup_orphan_temp_files(root: Path) -> int` — boot-time scan
  that unlinks any file matching `TEMP_FILE_RE`. Returns count.

`Storage` class:

- Construction: `Storage(root: Path)`.
- Reads: `list_root()`, `list_tree()`, `list_folder(parts)`,
  `read_feature(parts) -> Feature`, `read_raw(parts) -> str`.
  (There is no `exists(parts)` helper; callers check via
  `target.is_file()` / `.is_dir()` after `_resolve`, or rely on
  the `FileNotFoundError` that read paths raise.)
- File mutations: `create_file(parts, description)`,
  `write_feature(parts, feature)`, `write_raw(parts, text)`,
  `rename_file(parts, new_name)`, `duplicate_file(parts, new_name)`,
  `move_file(source_parts, dest_parent)`, `delete_file(parts)`.
- Folder mutations: `create_folder(parts)`,
  `rename_folder(parts, new_name)`, `delete_folder(parts)`.
- Search: `search(query, *, scope="all", match="text",
  case_sensitive=False) -> list[SearchHit]`.
- Self-write protocol (consumed by `03-watcher-and-sse`):
  `was_recently_written(abs_path: str) -> bool`.

Errors raised:

- `ValueError` — bad input (forbidden chars, empty parts, depth
  cap, same-parent move, etc.) → HTTP 400.
- `FileNotFoundError` → HTTP 404.
- `NameConflictError(path, message)` → HTTP 409.
- `ValidationError` / `GherkinParseError` — bubble up from
  `01-gherkin-io` on write paths.

## Invariants & rules

**Path discipline**

- `_split(parts)` accepts either a list of segments or a `/`-joined
  string. Empty parts and `.` / `..` segments are rejected.
- `_validate_segment(seg)` rejects any segment containing
  `/ \ : * ? " < > |` or a control char (`0x00..0x1F`).
- `_resolve(parts)` returns an absolute `Path` strictly inside the
  data root; any escape raises `ValueError`.
- `.feature` extension auto-appended on create; rejected if a
  different extension is supplied. Case-insensitive comparisons.

**Depth rules**

- Folder creation: `1 <= depth <= MAX_FOLDER_DEPTH`.
- `.feature` file location: parent at `2 <= depth <=
  MAX_FOLDER_DEPTH` (enforced at the API layer, not in `create_file`
  itself — storage trusts the segments it receives).
- `list_folder` returns shape by depth: `0 → {kind: "root", …}`,
  `1 → {kind: "project", …}`, `2 → {kind: "module", folders,
  features}`, `3..MAX → {kind: "subfolder", folders, features}`.

**Atomic write recipe**

- Temp name: `<target>.tmp.<pid>.<uuid_hex>` in the same directory
  as the target.
- Open, write, `fsync`, close → `os.replace` over the target.
- On any failure, unlink the temp; original exception propagates.
- Boot-time `cleanup_orphan_temp_files` deletes leftover temps
  matching the regex above.

**Name uniqueness**

- Scoped to the same parent only.
- Enforced via `target.exists()` (Python `pathlib.Path.exists`).
  Case-sensitivity therefore follows the host filesystem: macOS
  HFS+/APFS-default and Windows NTFS treat `Foo.feature` and
  `foo.feature` as the same path; ext4 / APFS-case-sensitive
  treat them as distinct. There is no explicit `casefold` /
  `lower` normalisation in storage.
- File-extension matching IS explicitly case-insensitive via
  `name.lower()` — so `MyTest.FEATURE` is accepted on any
  filesystem.
- Conflicts raise `NameConflictError`; HTTP layer maps to 409.

**Locking**

- `_lock_for(path_key) -> _PathLock` (a weakref-able wrapper around
  `threading.Lock`, kept in a `WeakValueDictionary`).
- Single-target mutations: acquire one lock.
- Dual-target mutations (rename / move / duplicate): acquire
  `sorted([src_key, dst_key])` — fixed ordering avoids deadlock.

**Self-write bookkeeping**

- After every successful mutation, `_mark_write(target)` records
  `target` *and* `target.parent` (POSIX `DirModifiedEvent` bubbles
  up one level on mtime change).
- Entries expire `RECENT_WRITE_TTL_SECONDS` (500 ms) after they're
  written; opportunistic cleanup runs in the same lock window.

**Search**

- `match="text"` substring-matches `Feature.description`; at most
  one hit per file.
- `match="tag"` substring-matches each tag in `Scenario.tags`; one
  hit per matching tag (multiple per file allowed) so the UI can
  show which tag matched.
- `scope`: `all` | `project:<name>` | `module:<proj>/<mod>`.
- Hit shape:
  `{ file_path, description, matched_field, match_value }`.

## Affects

- `01-gherkin-io`: storage is the only caller of
  `parse_feature` / `serialize_feature`. It is also the only place
  that catches `GherkinParseError` / `ValidationError` and lets
  them propagate to the HTTP layer.
- `03-watcher-and-sse`: consumes `was_recently_written` and
  `TEMP_FILE_RE`; would never emit any user-visible event without
  this contract.
- `04-folder-crud`, `05-testcase-crud`, `09-search`: every public
  HTTP route in those features delegates to a single `Storage`
  method.
- `06-tree-pane`, `07-folder-views`: render `list_tree()` /
  `list_folder()` output verbatim.

## Depends on

- `01-gherkin-io` (called by every read/write path that touches
  feature content).
- `app/errors.py` for the domain error types.
- Python stdlib only: `pathlib`, `os`, `secrets`, `time`,
  `threading`, `weakref`. No third-party dependency.
- POSIX-style `os.replace` semantics (atomic on the same
  filesystem). Behaviour on cross-device renames is **not** tested
  and not supported.

## Surface for follow-up

- `10-feature-test-run` (shipped) extends this module with run
  CRUD methods, the `RESERVED_DEPTH2_NAMES` set, and the
  `_normalize_run_filename` helper. The depth-0-is-a-project
  assumption in `list_folder` was preserved by reserving the
  `test-run` name at depth 2 rather than carving out a separate
  typed-area concept. A second typed area (e.g. `test-report/`)
  would generalise `RESERVED_DEPTH2_NAMES` into a typed-area
  registry; see the follow-up note in `10-feature-test-run`.
- Adding cross-device or cross-volume move support would require
  replacing `os.replace` with a fallback copy-then-delete sequence;
  current code does not.
- Pluggable "data root" backends (e.g. S3, sqlite) would replace
  this whole module behind the same method surface — no other
  feature would need to change.

## Acceptance criteria

- Reads, writes, and renames stay strictly inside the data root;
  any `..` or absolute segment raises `ValueError`.
- Crash mid-write leaves the target byte-identical to the
  pre-write state; the temp file is recovered by the next boot
  scan.
- Concurrent saves of the same file via two threads are
  serialised; last-write-wins by lock release order.
- Rename / move / duplicate never deadlock under any src/dst
  combination.
- `_mark_write` plus `TEMP_FILE_RE` together suppress every
  watcher event generated by storage's own writes — no spurious
  SSE notification reaches the UI.
