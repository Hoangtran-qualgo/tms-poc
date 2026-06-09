"""Storage layer: owns all FS access to the data root.

Read-side operations land in Do step 5 (this commit); writes and search land
in Do steps 6–8 per PLAN.md §12. The :class:`Storage` class is the single
public entry point for any FS access by upper layers.

Module-level :func:`cleanup_orphan_temp_files` remains a free function so
that ``app.create_app`` can call it before constructing :class:`Storage`.
"""

from __future__ import annotations

import os
import re
import secrets
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Union
from weakref import WeakValueDictionary

import yaml

from .errors import (
    EnumsParseError,
    GherkinParseError,
    NameConflictError,
    RunParseError,
    ValidationError,
)
from .gherkin_io import parse_feature, serialize_feature
from .models import (
    ENUM_IDENTIFIER_RE,
    Feature,
    RunResult,
    Scenario,
    TestRun,
    validate_run,
)

# Atomic-write temp file naming convention (see PLAN.md §6.3): every temp file
# is created as ``<target>.tmp.<pid>.<uuid_hex>`` in the same directory as the
# eventual target. The watcher and the boot-time scan share this regex.
TEMP_FILE_RE: re.Pattern[str] = re.compile(r".+\.tmp\.\d+\.[0-9a-f]+$")

#: Characters forbidden in any path segment, per PLAN.md §6.1.
_FORBIDDEN_CHARS: frozenset[str] = frozenset('/\\:*?"<>|') | frozenset(
    chr(c) for c in range(0x00, 0x20)
)

#: A "logical path" accepted by every public method on :class:`Storage`.
PartsLike = Union[str, list[str]]

#: Case-insensitive .feature extension test (see PLAN.md §6.1 and decision G7).
_FEATURE_EXT = ".feature"

#: Test-run file extension. Runs are persisted as YAML; see
#: ``specs/features/10-feature-test-run-NEW.md`` § "On-disk schema".
_RUN_EXT = ".yaml"

#: Single source-of-truth for the typed-area folder name. Kept as a
#: variable so future code (and tests) can refer to it without hard-coding.
_TEST_RUN_AREA = "test-run"

#: How long after a successful write the watcher should ignore FS events
#: for that path (self-write suppression, PLAN.md §7). The watcher imports
#: this constant directly to ensure both sides agree on the window.
RECENT_WRITE_TTL_SECONDS: float = 0.5

#: Maximum allowed folder nesting depth. Depth-1 = project, depth-2 = module,
#: depth-3..MAX = arbitrary sub-folders under modules. A `.feature` file can
#: live in any folder at depth >= 2 (i.e. its path has 3..MAX+1 segments).
#: Revisits PLAN.md decision B4 which previously capped depth at 2.
MAX_FOLDER_DEPTH: int = 10

#: Folder names that are reserved at depth 2 (i.e. as immediate children of
#: a project). The generic folder / file APIs reject any path that passes
#: through one of these names at index 1; the typed area's dedicated
#: methods (e.g. ``Storage.create_run_group``) are the only writers below.
#:
#: See ``specs/features/10-feature-test-run-NEW.md`` § "Reservation rules".
RESERVED_DEPTH2_NAMES: frozenset[str] = frozenset({"test-run"})

#: Project-level enums file name (lives at the project root, alongside
#: module folders and the typed-area folder). See
#: ``specs/features/11-feature-testcase-component-NEW.md``.
_ENUMS_FILE_NAME: str = "enums.yaml"

#: Default bytes written by ``init_project_enums`` and by the depth-1
#: branch of :meth:`Storage.create_folder`. The file starts with a single
#: declared kind (``components``) whose value is empty; PyYAML parses this
#: to ``{"components": None}`` which :meth:`Storage.read_project_enums`
#: normalises to ``{"components": {}}`` per the empty-value rule.
_ENUMS_DEFAULT_BYTES: bytes = b"components:\n"


def cleanup_orphan_temp_files(root: Path) -> int:
    """Recursively delete any orphan atomic-write temp files under ``root``.

    A previous process killed mid-write may leave behind temp files. They are
    safe to remove unconditionally because successful writes finish with an
    ``os.replace`` that consumes the temp file (see PLAN.md §6.3).

    Returns the count of files actually deleted. Best-effort: ``OSError`` on
    any individual unlink is swallowed so a single permission glitch does not
    abort app boot.
    """

    if not root.exists():
        return 0

    deleted = 0
    for path in root.rglob("*"):
        if path.is_file() and TEMP_FILE_RE.match(path.name):
            try:
                path.unlink()
            except OSError:
                continue
            deleted += 1
    return deleted


# ---------------------------------------------------------------------------
# Helpers (module-private)
# ---------------------------------------------------------------------------


def _is_feature_name(name: str) -> bool:
    """Case-insensitive ``.feature`` extension test."""
    return name.lower().endswith(_FEATURE_EXT)


def _normalize_filename(name: str) -> str:
    """Auto-append ``.feature`` if no extension; reject if a different ext.

    Comparison is case-insensitive per decision G7 (PLAN.md §14). A leading
    dot (e.g. ``".feature"``) is allowed since the caller's `_validate_segment`
    will independently reject ``.`` / ``..``.
    """
    if not name:
        raise ValueError("File name must not be empty.")
    if name.lower().endswith(_FEATURE_EXT):
        return name
    if "." in name:
        raise ValueError(
            f"File name must end with '.feature' (case-insensitive); got {name!r}."
        )
    return name + _FEATURE_EXT


def _normalize_run_filename(name: str) -> str:
    """Auto-append ``.yaml`` if no extension; reject any other extension.

    Run files live as ``<group>/<file_name>.yaml`` and are written
    exclusively by the typed-area APIs. Mirrors :func:`_normalize_filename`
    so the leaf-validation feel is consistent across the codebase.
    """
    if not name:
        raise ValueError("Run file name must not be empty.")
    if name.lower().endswith(_RUN_EXT):
        return name
    if "." in name:
        raise ValueError(
            f"Run file name must end with '.yaml' (case-insensitive); "
            f"got {name!r}."
        )
    return name + _RUN_EXT


class _PathLock:
    """Weakref-able context manager wrapping :class:`threading.Lock`.

    CPython's built-in ``threading.Lock`` is not weakly referenceable, so we
    wrap it in a slim Python class. The wrapper itself is what gets stored in
    the per-path :class:`WeakValueDictionary`; callers hold a strong reference
    to the wrapper for the duration of the ``with`` block, which prevents
    GC from racing the lock acquisition.
    """

    __slots__ = ("_lock", "__weakref__")

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def __enter__(self) -> "_PathLock":
        self._lock.acquire()
        return self

    def __exit__(self, *exc: object) -> None:
        self._lock.release()


# ---------------------------------------------------------------------------
# Storage class
# ---------------------------------------------------------------------------


class Storage:
    """Single-instance owner of all FS reads/writes inside the data root.

    Every public method takes a "logical path", which may be either a string
    using ``/`` as a separator (root = ``""``) or a list of segments. The
    string form is the API/UI wire format; the list form is convenient inside
    the module. Paths are validated to stay inside :attr:`root`.

    See PLAN.md §6 for the full operations table and path discipline rules.
    """

    def __init__(self, root: Path) -> None:
        self.root: Path = root.resolve()
        # Per-path lock dict for serialising same-target writes. Keys are the
        # canonical posix-path string ("p/m/x.feature"). Entries fall out of
        # the dict once no caller holds the wrapper.
        self._locks: WeakValueDictionary[str, _PathLock] = WeakValueDictionary()
        self._locks_guard: threading.Lock = threading.Lock()
        # Self-write suppression bookkeeping: absolute-path string -> wall time.
        self._recent_writes: dict[str, float] = {}
        self._recent_writes_lock: threading.Lock = threading.Lock()
        # Project-level enums.yaml cache: project name -> (mtime_ns, parsed).
        # Invalidated by an mtime mismatch on read or by an internal write.
        # See specs/features/11-feature-testcase-component-NEW.md (Caching).
        self._enums_cache: dict[str, tuple[int, dict[str, dict[str, str]]]] = {}
        self._enums_cache_lock: threading.Lock = threading.Lock()

    # -- Self-write suppression ------------------------------------------

    def _mark_write(self, target: Path) -> None:
        """Record ``target`` as just-written so the watcher can suppress it.

        Also marks the immediate parent directory: most FS mutations bubble
        a ``DirModifiedEvent`` up one level (parent's mtime changes when a
        child is created, modified, deleted, or renamed). Without this the
        watcher would emit a stray notification per user-initiated write.
        """
        now = time.monotonic()
        with self._recent_writes_lock:
            self._recent_writes[str(target)] = now
            parent = target.parent
            if parent != target:  # not at the filesystem root
                self._recent_writes[str(parent)] = now
            # Opportunistic cleanup: drop entries older than 2x TTL so the dict
            # cannot grow unbounded under bursty writes.
            cutoff = now - (RECENT_WRITE_TTL_SECONDS * 2)
            stale = [p for p, t in self._recent_writes.items() if t < cutoff]
            for p in stale:
                del self._recent_writes[p]

    def was_recently_written(self, abs_path: str) -> bool:
        """Return ``True`` if ``abs_path`` was written within the TTL window."""
        with self._recent_writes_lock:
            t = self._recent_writes.get(abs_path)
            if t is None:
                return False
            if time.monotonic() - t > RECENT_WRITE_TTL_SECONDS:
                del self._recent_writes[abs_path]
                return False
            return True

    # -- Locking ----------------------------------------------------------

    def _lock_for(self, path_key: str) -> _PathLock:
        """Return (creating if needed) the per-path :class:`_PathLock`."""
        with self._locks_guard:
            lock = self._locks.get(path_key)
            if lock is None:
                lock = _PathLock()
                self._locks[path_key] = lock
        return lock

    @staticmethod
    def _key(segments: list[str]) -> str:
        return "/".join(segments)

    # -- Path discipline --------------------------------------------------

    @staticmethod
    def _split(parts: PartsLike) -> list[str]:
        """Normalise a logical path into a list of segments.

        Rejects absolute paths up front so a value like ``"/etc/passwd"``
        cannot bypass the per-segment validation.
        """
        if isinstance(parts, str):
            if parts.startswith("/"):
                raise ValueError(f"Absolute path not allowed: {parts!r}")
            return [p for p in parts.split("/") if p]
        if isinstance(parts, list):
            return list(parts)
        raise TypeError(
            f"parts must be str or list[str], got {type(parts).__name__}"
        )

    @staticmethod
    def _validate_segment(seg: str) -> None:
        if not seg:
            raise ValueError("Empty path segment.")
        if seg in (".", ".."):
            raise ValueError(f"Disallowed path segment: {seg!r}")
        for ch in seg:
            if ch in _FORBIDDEN_CHARS:
                raise ValueError(
                    f"Forbidden character {ch!r} in path segment: {seg!r}"
                )

    def _resolve(self, parts: PartsLike) -> Path:
        """Return an absolute :class:`Path` for ``parts`` guaranteed to be
        inside :attr:`root`.
        """
        segments = self._split(parts)
        for seg in segments:
            self._validate_segment(seg)
        target = self.root.joinpath(*segments).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError(f"Path escapes data root: {parts!r}")
        return target

    @staticmethod
    def _reject_reserved_typed_area(segments: list[str]) -> None:
        """Reject any path that passes through a reserved depth-2 name.

        The generic folder / file create APIs delegate here so the typed
        area (currently only ``test-run``) can only be written via its
        dedicated methods. Raises :class:`NameConflictError` so the HTTP
        layer surfaces a 409, reusing the existing name-conflict envelope
        per the spec-10 lock-in.
        """
        if len(segments) >= 2 and segments[1] in RESERVED_DEPTH2_NAMES:
            raise NameConflictError(
                path="/".join(segments),
                message=(
                    f"{segments[1]!r} is a reserved typed area under "
                    f"{segments[0]!r}; writes must go through the dedicated "
                    f"API (e.g. /api/runs)."
                ),
            )

    # -- Listings ---------------------------------------------------------

    def list_root(self) -> list[str]:
        """Return depth-0 folder names (projects), in OS listing order."""
        out: list[str] = []
        if not self.root.exists():
            return out
        for entry in self.root.iterdir():
            if entry.is_dir() and not TEMP_FILE_RE.match(entry.name):
                out.append(entry.name)
        return out

    def list_tree(self) -> dict[str, Any]:
        """Return the full recursive tree as a JSON-serialisable dict.

        Shape matches PLAN.md §16.6: a root wrapper ``{name: "", children:
        [...]}``, folder nodes carrying a ``depth`` field (root's children
        are depth 0), file nodes typed ``feature`` or ``other``. Orphan
        atomic-write temp files are filtered out at every level.
        """
        return {
            "name": "",
            "children": self._tree_children(self.root, depth=0),
        }

    def _tree_children(self, dir_path: Path, depth: int) -> list[dict[str, Any]]:
        children: list[dict[str, Any]] = []
        if not dir_path.exists():
            return children
        for entry in dir_path.iterdir():
            name = entry.name
            if TEMP_FILE_RE.match(name):
                continue
            # Hide the reserved typed area (test-run/) from the directory
            # tree. It lives at depth 1 (direct child of a project) and is
            # surfaced via the separate Test-run sidebar tab; see
            # `list_test_run_tree`.
            if depth == 1 and name in RESERVED_DEPTH2_NAMES:
                continue
            # Hide the project-level enums.yaml file from the directory
            # tree per spec 11. v1 has no in-app surface for editing it
            # beyond the `Initialize enums file` action; teams hand-edit
            # the file on disk.
            if depth == 1 and name == _ENUMS_FILE_NAME and entry.is_file():
                continue
            rel = entry.relative_to(self.root).as_posix()
            if entry.is_dir():
                children.append(
                    {
                        "type": "folder",
                        "name": name,
                        "depth": depth,
                        "path": rel,
                        "children": self._tree_children(entry, depth + 1),
                    }
                )
            elif entry.is_file():
                children.append(
                    {
                        "type": "feature" if _is_feature_name(name) else "other",
                        "name": name,
                        "path": rel,
                    }
                )
        return children

    def list_test_run_tree(self) -> dict[str, Any]:
        """Return the aggregated ``test-run/`` subtree of every project.

        Shape mirrors :meth:`list_tree` for template-reuse convenience but
        marks leaves with ``type: "run"`` so the Test-run sidebar template
        can render them as ``/ui/run/...`` links rather than generic files.
        Projects without a ``test-run/`` folder are omitted; the resulting
        root has no children if no project has runs yet.

        Per-node shape:

        - project: ``{type:"folder", name, depth:0, path:<project>,
          children:[<group>...]}``
        - group: ``{type:"folder", name, depth:1, path:<project>/test-run/<group>,
          children:[<run>...]}``
        - run: ``{type:"run", name:<file_name>, path:<project>/test-run/<group>/<file_name>,
          project, group, file_name}``

        Non-YAML files inside groups and any nested folders are ignored;
        the typed area's structure is fixed (see
        ``specs/features/10-feature-test-run-NEW.md``).
        """
        children: list[dict[str, Any]] = []
        if not self.root.exists():
            return {"name": "", "children": children}
        for project_entry in self.root.iterdir():
            if not project_entry.is_dir() or TEMP_FILE_RE.match(project_entry.name):
                continue
            test_run_dir = project_entry / _TEST_RUN_AREA
            if not test_run_dir.is_dir():
                continue
            project = project_entry.name
            groups: list[dict[str, Any]] = []
            for group_entry in test_run_dir.iterdir():
                if not group_entry.is_dir() or TEMP_FILE_RE.match(group_entry.name):
                    continue
                group = group_entry.name
                runs: list[dict[str, Any]] = []
                for run_entry in group_entry.iterdir():
                    name = run_entry.name
                    if TEMP_FILE_RE.match(name) or not run_entry.is_file():
                        continue
                    if not name.lower().endswith(".yaml"):
                        continue
                    runs.append(
                        {
                            "type": "run",
                            "name": name,
                            "path": f"{project}/{_TEST_RUN_AREA}/{group}/{name}",
                            "project": project,
                            "group": group,
                            "file_name": name,
                        }
                    )
                groups.append(
                    {
                        "type": "folder",
                        "name": group,
                        "depth": 1,
                        "path": f"{project}/{_TEST_RUN_AREA}/{group}",
                        "children": runs,
                    }
                )
            children.append(
                {
                    "type": "folder",
                    "name": project,
                    "depth": 0,
                    "path": project,
                    "children": groups,
                }
            )
        return {"name": "", "children": children}

    def list_projects(self) -> list[str]:
        """Return all project (depth-0) directory names, sorted.

        Backs the ``GET /api/run-groups`` endpoint's ``projects`` field
        so the "+ New run" modal's "Create new group..." sub-form can
        offer existing projects as a target. Temp-suffixed directories
        are excluded; ordering is case-insensitive ascending for stable
        UI between requests.
        """
        if not self.root.exists():
            return []
        out: list[str] = []
        for entry in self.root.iterdir():
            if not entry.is_dir() or TEMP_FILE_RE.match(entry.name):
                continue
            out.append(entry.name)
        out.sort(key=str.lower)
        return out

    def list_folder(self, parts: PartsLike) -> dict[str, Any]:
        """Return one folder's contents per PLAN.md §6.2 / §16.7.

        Variants returned by depth:

        - 0 (empty parts) → ``{kind: "root", projects: [name, ...]}``
        - 1 → ``{kind: "project", modules: [name, ...]}``
        - 2 → ``{kind: "module", folders: [name, ...], features: [...]}``
        - 3..MAX_FOLDER_DEPTH → ``{kind: "subfolder", folders: [...], features: [...]}``

        At depths 2 and beyond a folder may contain BOTH `.feature` files
        and sub-folders.

        Raises :class:`ValueError` for depth > MAX_FOLDER_DEPTH;
        :class:`FileNotFoundError` if the resolved path does not exist or
        is not a directory.

        For module / sub-folder listings, each ``.feature`` file is parsed
        best-effort to extract ``description`` and the scenario's ``tags``.
        Files that fail to parse are still listed, with empty description
        and empty tags so the user can find and repair them.
        """

        segments = self._split(parts)
        for seg in segments:
            self._validate_segment(seg)

        if len(segments) == 0:
            return {"kind": "root", "projects": self.list_root()}

        if len(segments) > MAX_FOLDER_DEPTH:
            raise ValueError(
                f"list_folder only supports paths up to depth {MAX_FOLDER_DEPTH}; "
                f"got depth {len(segments)}."
            )

        target = self._resolve(segments)
        if not target.is_dir():
            raise FileNotFoundError(f"Folder not found: {target}")

        if len(segments) == 1:
            modules: list[str] = []
            for entry in target.iterdir():
                if not entry.is_dir() or TEMP_FILE_RE.match(entry.name):
                    continue
                # Hide the reserved typed area from the project module
                # listing; runs are reached via the Test-run sidebar tab.
                if entry.name in RESERVED_DEPTH2_NAMES:
                    continue
                modules.append(entry.name)
            return {"kind": "project", "modules": modules}

        # depth >= 2 — module or sub-folder listing. Both folders and
        # features can coexist; collect each in its own list.
        folders: list[str] = []
        features: list[dict[str, Any]] = []
        for entry in target.iterdir():
            name = entry.name
            if TEMP_FILE_RE.match(name):
                continue
            if entry.is_dir():
                folders.append(name)
                continue
            if not entry.is_file():
                continue
            if not _is_feature_name(name):
                continue
            try:
                feature = self.read_feature([*segments, name])
                description = feature.description
                tags = list(feature.scenario.tags)
            except (GherkinParseError, OSError, UnicodeDecodeError):
                description = ""
                tags = []
            features.append(
                {
                    "file_name": name,
                    "description": description,
                    "tags": tags,
                }
            )
        kind = "module" if len(segments) == 2 else "subfolder"
        return {"kind": kind, "folders": folders, "features": features}

    # -- Reads -----------------------------------------------------------

    def read_feature(self, parts: PartsLike) -> Feature:
        """Read and parse a ``.feature`` file.

        Raises :class:`FileNotFoundError` if the file is missing, and
        :class:`~app.errors.GherkinParseError` if the file is unparseable.
        Encoding errors (non-UTF-8) propagate as :class:`UnicodeDecodeError`.
        """
        target = self._resolve(parts)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {target}")
        text = target.read_text(encoding="utf-8")
        return parse_feature(text)

    def read_raw(self, parts: PartsLike) -> str:
        """Return the raw UTF-8 text of any file inside the data root."""
        target = self._resolve(parts)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {target}")
        return target.read_text(encoding="utf-8")

    # -- Atomic write primitive ------------------------------------------

    def _atomic_write_bytes(self, target: Path, data: bytes) -> None:
        """Write ``data`` to ``target`` atomically per PLAN.md §6.3.

        Steps: write to ``<target>.tmp.<pid>.<uuid_hex>`` in the same
        directory; ``fsync`` the file descriptor; ``os.replace`` the temp
        over the target (single atomic rename on POSIX). The temp is
        unlinked on any error so we do not leave orphans during normal
        operation (the boot-time scan handles crashes).

        Requires the parent directory to already exist; raises
        :class:`FileNotFoundError` otherwise.
        """
        if not target.parent.is_dir():
            raise FileNotFoundError(
                f"Parent folder does not exist: {target.parent}"
            )

        tmp_name = f"{target.name}.tmp.{os.getpid()}.{secrets.token_hex(8)}"
        tmp = target.parent / tmp_name
        try:
            with open(tmp, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, target)
        except BaseException:
            # Best-effort cleanup; ignore unlink failures so the original
            # exception is what propagates.
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass
            raise

    # -- Writes / creates / mutations ------------------------------------

    def create_file(self, parts: PartsLike, description: str) -> None:
        """Create a new ``.feature`` file with a placeholder scenario.

        The leaf segment of ``parts`` is normalised by :func:`_normalize_filename`
        (auto-append ``.feature`` if missing; reject any other extension).
        Raises :class:`NameConflictError` if a file already exists at the
        resolved path; :class:`FileNotFoundError` if the parent folder is
        missing; :class:`~app.errors.ValidationError` if ``description`` is
        empty or otherwise invalid for write-time invariants.
        """
        segments = self._split(parts)
        if not segments:
            raise ValueError("create_file requires a non-empty path.")

        leaf = _normalize_filename(segments[-1])
        final_segments = [*segments[:-1], leaf]
        for seg in final_segments:
            self._validate_segment(seg)
        self._reject_reserved_typed_area(final_segments)

        target = self._resolve(final_segments)
        key = self._key(final_segments)
        with self._lock_for(key):
            if target.exists():
                raise NameConflictError(
                    path=key,
                    message=f"A file named {leaf!r} already exists.",
                )
            feature = Feature(
                description=description,
                scenario=Scenario(kind="scenario", name=""),
            )
            # Cross-check (no-op for the default empty enums dict; kept for
            # symmetry with write_feature / write_raw so future create-time
            # enum assignment goes through the same gate).
            self._cross_check_enums(final_segments[0], feature)
            text = serialize_feature(feature)
            self._atomic_write_bytes(target, text.encode("utf-8"))
            self._mark_write(target)

    def write_feature(self, parts: PartsLike, feature: Feature) -> None:
        """Serialise and atomically write an existing file's :class:`Feature`.

        Raises :class:`FileNotFoundError` if the target file does not exist
        (use :meth:`create_file` instead). The serialiser performs all
        write-time validation; raises :class:`~app.errors.ValidationError`
        on any invariant violation. Also cross-checks any non-empty
        ``feature.enums`` entries against the project's ``enums.yaml`` per
        spec 11; raises :class:`~app.errors.ValidationError` (422) on
        unknown kind / key or a missing enums.yaml.
        """
        segments = self._split(parts)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if not target.is_file():
                raise FileNotFoundError(
                    f"Cannot update missing file: {target}"
                )
            self._cross_check_enums(segments[0], feature)
            text = serialize_feature(feature)
            self._atomic_write_bytes(target, text.encode("utf-8"))
            self._mark_write(target)

    def write_raw(self, parts: PartsLike, text: str) -> None:
        """Atomically write raw text to an existing ``.feature`` file.

        Parses ``text`` first to enforce Gherkin validity (raises
        :class:`~app.errors.GherkinParseError` on bad input). Newlines are
        normalised to LF before being persisted so the file format stays
        consistent regardless of the editor's input encoding. Cross-checks
        the parsed feature's ``enums`` against the project's ``enums.yaml``
        per spec 11.
        """
        parsed = parse_feature(text)  # raises GherkinParseError on bad input
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")

        segments = self._split(parts)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if not target.is_file():
                raise FileNotFoundError(
                    f"Cannot update missing file: {target}"
                )
            self._cross_check_enums(segments[0], parsed)
            self._atomic_write_bytes(target, normalized.encode("utf-8"))
            self._mark_write(target)

    def delete_file(self, parts: PartsLike) -> None:
        """Delete a file. Idempotent: succeeds if the file was already gone."""
        segments = self._split(parts)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            try:
                target.unlink()
            except FileNotFoundError:
                return  # idempotent per PLAN.md §6.2
            except IsADirectoryError as e:
                raise ValueError(
                    f"Target is a directory, not a file: {target}"
                ) from e
            self._mark_write(target)

    def rename_file(self, parts: PartsLike, new_name: str) -> None:
        """Rename a file within its existing parent folder.

        ``new_name`` is normalised the same way as in :meth:`create_file`.
        Raises :class:`FileNotFoundError` if the source is missing,
        :class:`NameConflictError` if the destination name is already taken,
        and :class:`ValueError` if ``new_name`` is invalid.

        Same-parent only by construction: the destination shares the source's
        parent segments — there is no way for callers to move across folders
        via this API (per PLAN.md §6.2 / decision B2).
        """
        segments = self._split(parts)
        if not segments:
            raise ValueError("rename_file requires a non-empty path.")
        source = self._resolve(segments)
        if not source.is_file():
            raise FileNotFoundError(f"File not found: {source}")

        new_leaf = _normalize_filename(new_name)
        self._validate_segment(new_leaf)
        target_segments = [*segments[:-1], new_leaf]
        target = self._resolve(target_segments)

        if source == target:
            return  # no-op rename

        # Acquire both locks in a stable order to avoid deadlock.
        src_key = self._key(segments)
        dst_key = self._key(target_segments)
        first, second = sorted([src_key, dst_key])
        with self._lock_for(first), self._lock_for(second):
            if target.exists():
                raise NameConflictError(
                    path=dst_key,
                    message=f"A file named {new_leaf!r} already exists.",
                )
            os.replace(source, target)
            self._mark_write(source)
            self._mark_write(target)

    # -- Project-level enums --------------------------------------------
    #
    # See specs/features/11-feature-testcase-component-NEW.md. Each project
    # carries one ``enums.yaml`` at its root listing the canonical
    # ``<kind>: [- <key>: <label>]`` vocabulary used by ``Feature.enums``.
    # Reads are mtime-cached per project so the cross-check on every
    # test-case save costs one ``os.stat`` plus a dict lookup on the hot
    # path. Hand-edits to the file take effect on the next access.

    def read_project_enums(self, project: str) -> dict[str, dict[str, str]]:
        """Read + parse + schema-validate ``<project>/enums.yaml``.

        Returns the outer-kind → inner ``{key: label}`` map (insertion
        order preserved). An empty file, a comment-only file, or a YAML
        document whose top-level is ``None`` normalises to ``{}``; a kind
        whose value is ``None`` or ``[]`` normalises to an empty inner map.

        Raises :class:`FileNotFoundError` if the file is missing,
        :class:`~app.errors.EnumsParseError` on malformed YAML or any
        schema violation (rules (a)–(d) in the spec).

        Cached per project keyed on ``os.stat().st_mtime_ns``; the cache
        is refreshed transparently on every mtime mismatch and on
        internal writes (``init_project_enums``).
        """
        target = self._resolve([project]) / _ENUMS_FILE_NAME
        try:
            st = target.stat()
        except FileNotFoundError:
            self._invalidate_enums_cache(project)
            raise
        mtime_ns = st.st_mtime_ns
        with self._enums_cache_lock:
            cached = self._enums_cache.get(project)
            if cached is not None and cached[0] == mtime_ns:
                return cached[1]
        try:
            raw = target.read_bytes()
        except FileNotFoundError:
            self._invalidate_enums_cache(project)
            raise
        parsed = self._parse_project_enums(raw)
        with self._enums_cache_lock:
            self._enums_cache[project] = (mtime_ns, parsed)
        return parsed

    def init_project_enums(self, project: str) -> dict[str, dict[str, str]]:
        """Write the default ``components:\\n`` file for ``project``.

        Returns the parsed enums dict (``{"components": {}}``) on success
        so the caller can update an in-memory cache without an extra
        round-trip. Raises :class:`~app.errors.NameConflictError` if the
        file already exists (no overwrite), :class:`FileNotFoundError` if
        the project folder is missing.

        Used both by the manual ``POST /api/enums/<project>`` action and
        by callers who want to reconcile a legacy project. The project-
        create auto-init in :meth:`create_folder` inlines the same bytes
        write so it can stay inside the project-folder lock region; this
        method takes its own per-path lock.
        """
        project_dir = self._resolve([project])
        if not project_dir.is_dir():
            raise FileNotFoundError(
                f"Project folder does not exist: {project!r}"
            )
        target = project_dir / _ENUMS_FILE_NAME
        key = f"{project}/{_ENUMS_FILE_NAME}"
        with self._lock_for(key):
            if target.exists():
                raise NameConflictError(
                    path=key,
                    message=(
                        f"A file named {_ENUMS_FILE_NAME!r} already "
                        f"exists under project {project!r}."
                    ),
                )
            self._atomic_write_bytes(target, _ENUMS_DEFAULT_BYTES)
            self._mark_write(target)
        self._invalidate_enums_cache(project)
        return self.read_project_enums(project)

    def _invalidate_enums_cache(self, project: str) -> None:
        with self._enums_cache_lock:
            self._enums_cache.pop(project, None)

    @staticmethod
    def _parse_project_enums(raw: bytes) -> dict[str, dict[str, str]]:
        """Parse + schema-validate the bytes of ``<project>/enums.yaml``.

        Wraps :class:`yaml.YAMLError` into :class:`EnumsParseError` with a
        location when PyYAML reports one; enforces:

        (a) every inner list element is a single-key mapping;
        (b) every key matches :data:`ENUM_IDENTIFIER_RE`;
        (c) every label is a non-empty string with no embedded newline;
        (d) keys are unique within a kind.
        """
        try:
            payload = yaml.safe_load(raw)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None) or getattr(
                e, "context_mark", None
            )
            line = (mark.line + 1) if mark is not None else 0
            column = (mark.column + 1) if mark is not None else 0
            message = getattr(e, "problem", None) or str(e)
            raise EnumsParseError(
                line=line, column=column, message=message
            ) from e

        if payload is None:
            return {}
        if not isinstance(payload, dict):
            raise EnumsParseError(
                line=0,
                column=0,
                message=(
                    f"enums.yaml root must be a YAML mapping; "
                    f"got {type(payload).__name__}."
                ),
            )

        out: dict[str, dict[str, str]] = {}
        for kind, value in payload.items():
            if not isinstance(kind, str) or not ENUM_IDENTIFIER_RE.fullmatch(
                kind
            ):
                raise EnumsParseError(
                    line=0,
                    column=0,
                    message=(
                        f"Invalid enum kind name {kind!r}; kinds must "
                        f"match {ENUM_IDENTIFIER_RE.pattern}."
                    ),
                )
            if value is None:
                out[kind] = {}
                continue
            if not isinstance(value, list):
                raise EnumsParseError(
                    line=0,
                    column=0,
                    message=(
                        f"Value under kind {kind!r} must be a list of "
                        f"single-key mappings (- <key>: <label>); got "
                        f"{type(value).__name__}."
                    ),
                )
            inner: dict[str, str] = {}
            for i, item in enumerate(value):
                if not isinstance(item, dict) or len(item) != 1:
                    raise EnumsParseError(
                        line=0,
                        column=0,
                        message=(
                            f"Element {i} under kind {kind!r} must be a "
                            f"single-key mapping (- <key>: <label>)."
                        ),
                    )
                ((key, label),) = item.items()
                if not isinstance(key, str) or not ENUM_IDENTIFIER_RE.fullmatch(
                    key
                ):
                    raise EnumsParseError(
                        line=0,
                        column=0,
                        message=(
                            f"Invalid enum key {key!r} under kind "
                            f"{kind!r}; keys must match "
                            f"{ENUM_IDENTIFIER_RE.pattern}."
                        ),
                    )
                if key in inner:
                    raise EnumsParseError(
                        line=0,
                        column=0,
                        message=(
                            f"Duplicate enum key {key!r} under kind "
                            f"{kind!r}."
                        ),
                    )
                if not isinstance(label, str):
                    raise EnumsParseError(
                        line=0,
                        column=0,
                        message=(
                            f"Label for key {key!r} under kind {kind!r} "
                            f"must be a string; got "
                            f"{type(label).__name__}."
                        ),
                    )
                if not label:
                    raise EnumsParseError(
                        line=0,
                        column=0,
                        message=(
                            f"Label for key {key!r} under kind {kind!r} "
                            f"must be non-empty."
                        ),
                    )
                if "\n" in label:
                    raise EnumsParseError(
                        line=0,
                        column=0,
                        message=(
                            f"Label for key {key!r} under kind {kind!r} "
                            f"must be single-line."
                        ),
                    )
                inner[key] = label
            out[kind] = inner
        return out

    def _cross_check_enums(self, project: str, feature: Feature) -> None:
        """Reject saves whose enums don't resolve in ``<project>/enums.yaml``.

        Skips entirely when ``feature.enums`` has no non-empty entries
        (storage never forces a value to be set; *unset* is always
        legal). Missing-file rule: when there ARE non-empty entries but
        the YAML is absent, every entry is treated as orphan and the
        save is rejected with a hint pointing at the `Initialize enums
        file` action. ``EnumsParseError`` from a malformed YAML
        propagates to the API layer as a 422 envelope.
        """
        nonempty = {k: v for k, v in feature.enums.items() if v}
        if not nonempty:
            return
        try:
            vocab = self.read_project_enums(project)
        except FileNotFoundError:
            raise ValidationError(
                field="enums",
                message=(
                    f"Cannot save enum values: project {project!r} has no "
                    f"{_ENUMS_FILE_NAME}. Run the 'Initialize enums file' "
                    f"action to create one before assigning enum values."
                ),
            )
        for kind, key in nonempty.items():
            kind_entries = vocab.get(kind)
            if kind_entries is None:
                raise ValidationError(
                    field=f"enums[{kind}]",
                    message=(
                        f"Unknown enum kind {kind!r}; not defined in "
                        f"{project}/{_ENUMS_FILE_NAME}."
                    ),
                )
            if key not in kind_entries:
                raise ValidationError(
                    field=f"enums[{kind}]",
                    message=(
                        f"Unknown enum key {key!r} for kind {kind!r}; "
                        f"not defined in {project}/{_ENUMS_FILE_NAME}."
                    ),
                )

    # -- Search ----------------------------------------------------------

    def search(
        self,
        query: str,
        *,
        scope: str = "all",
        match: str = "text",
        case_sensitive: bool = False,
    ) -> list[dict[str, Any]]:
        """Substring-search ``.feature`` files for ``query``.

        Parameters
        ----------
        query:
            The search term. Empty/whitespace-only queries return ``[]``.
        scope:
            ``"all"`` (default), ``"project:<name>"``, or ``"module:<proj>/<mod>"``.
        match:
            ``"text"`` — matches ``Feature.description`` only.
            ``"tag"`` — matches ``Scenario.tags`` only. Other fields are not
            searched in v1 per PLAN.md §13.
        case_sensitive:
            Default ``False`` (case-insensitive substring match).

        Returns a list of :class:`SearchHit`-shaped dicts (see PLAN.md §16.8).
        For ``match="tag"`` a file with multiple matching tags emits one hit
        per matching tag so the UI can display which tag matched. For
        ``match="text"`` at most one hit per file is emitted.

        ``match_value`` semantics per decision G6:

        - ``text`` mode: the caller's ``query`` string echoed back.
        - ``tag`` mode: the matched tag value (without the leading ``@``).
        """
        if not query or not query.strip():
            return []
        if match not in ("text", "tag"):
            raise ValueError(
                f"Invalid match mode: {match!r}. Must be 'text' or 'tag'."
            )

        base_segments = self._scope_to_segments(scope)
        base = self._resolve(base_segments) if base_segments else self.root
        if not base.is_dir():
            return []

        needle = query if case_sensitive else query.lower()
        hits: list[dict[str, Any]] = []

        for path in self._iter_feature_files(base):
            rel = path.relative_to(self.root).as_posix()
            try:
                feature = self.read_feature(rel)
            except (GherkinParseError, OSError, UnicodeDecodeError):
                # Unparseable files are silent — surface them via the tree /
                # module listing where the user can repair them.
                continue

            if match == "text":
                haystack = (
                    feature.description if case_sensitive
                    else feature.description.lower()
                )
                if needle in haystack:
                    hits.append(
                        {
                            "file_path": rel,
                            "description": feature.description,
                            "matched_field": "description",
                            "match_value": query,
                        }
                    )
            else:  # match == "tag"
                for tag in feature.scenario.tags:
                    tag_hay = tag if case_sensitive else tag.lower()
                    if needle in tag_hay:
                        hits.append(
                            {
                                "file_path": rel,
                                "description": feature.description,
                                "matched_field": "tag",
                                "match_value": tag,
                            }
                        )

        return hits

    @staticmethod
    def _scope_to_segments(scope: str) -> list[str]:
        """Parse a scope token into a list of path segments rooted at the data root.

        Raises :class:`ValueError` on any malformed scope.
        """
        if scope in ("", "all"):
            return []
        if scope.startswith("project:"):
            name = scope[len("project:"):]
            if not name or "/" in name:
                raise ValueError(
                    f"project scope must be 'project:<name>', got {scope!r}"
                )
            return [name]
        if scope.startswith("module:"):
            parts = [p for p in scope[len("module:"):].split("/") if p]
            if len(parts) != 2:
                raise ValueError(
                    f"module scope must be 'module:<proj>/<mod>', got {scope!r}"
                )
            return parts
        raise ValueError(
            f"Invalid scope: {scope!r}. "
            "Must be 'all', 'project:<name>', or 'module:<proj>/<mod>'."
        )

    def _iter_feature_files(self, base: Path):
        """Yield every ``.feature`` file under ``base``, excluding temp orphans."""
        for path in base.rglob("*"):
            if (
                path.is_file()
                and _is_feature_name(path.name)
                and not TEMP_FILE_RE.match(path.name)
            ):
                yield path

    # -- Folder writes ----------------------------------------------------

    def create_folder(self, parts: PartsLike) -> None:
        """Create a folder at depth 1..MAX_FOLDER_DEPTH.

        Depth 1 = project, depth 2 = module, depth 3..MAX = arbitrary
        sub-folder. Raises :class:`NameConflictError` if the folder already
        exists, and :class:`FileNotFoundError` if the immediate parent
        (depth ≥ 2) is missing. ``parents=False`` prevents typos in the
        parent chain from creating intermediate folders implicitly.
        """
        segments = self._split(parts)
        if not segments:
            raise ValueError("create_folder requires a non-empty path.")
        for seg in segments:
            self._validate_segment(seg)
        if len(segments) > MAX_FOLDER_DEPTH:
            raise ValueError(
                f"create_folder only supports paths up to depth "
                f"{MAX_FOLDER_DEPTH}; got depth {len(segments)}."
            )
        self._reject_reserved_typed_area(segments)

        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if target.exists():
                raise NameConflictError(
                    path=key,
                    message=f"A folder named {segments[-1]!r} already exists.",
                )
            if len(segments) >= 2 and not target.parent.is_dir():
                raise FileNotFoundError(
                    f"Parent folder does not exist: {'/'.join(segments[:-1])!r}"
                )
            target.mkdir(parents=False, exist_ok=False)
            self._mark_write(target)
            # Project-create auto-init: write the default `enums.yaml` next
            # to the newly-created project folder per spec 11. The two
            # writes are sequential, not atomic; a crash between them
            # leaves a legacy-shaped project (no enums file) that the user
            # reconciles via `Initialize enums file`. Same code path.
            if len(segments) == 1:
                enums_target = target / _ENUMS_FILE_NAME
                self._atomic_write_bytes(enums_target, _ENUMS_DEFAULT_BYTES)
                self._mark_write(enums_target)

    def rename_folder(self, parts: PartsLike, new_name: str) -> None:
        """Rename a folder within its existing parent. Any depth allowed.

        Same-parent only by construction (the destination shares the
        source's parent segments). Raises :class:`FileNotFoundError` for a
        missing source, :class:`NameConflictError` if the destination is
        already taken, and :class:`ValueError` if ``new_name`` is invalid.
        """
        segments = self._split(parts)
        if not segments:
            raise ValueError("rename_folder requires a non-empty path.")
        source = self._resolve(segments)
        if not source.is_dir():
            raise FileNotFoundError(f"Folder not found: {source}")

        self._validate_segment(new_name)
        target_segments = [*segments[:-1], new_name]
        target = self._resolve(target_segments)

        if source == target:
            return  # no-op

        src_key = self._key(segments)
        dst_key = self._key(target_segments)
        first, second = sorted([src_key, dst_key])
        with self._lock_for(first), self._lock_for(second):
            if target.exists():
                raise NameConflictError(
                    path=dst_key,
                    message=f"A folder named {new_name!r} already exists.",
                )
            os.replace(source, target)
            self._mark_write(source)
            self._mark_write(target)

    def delete_folder(self, parts: PartsLike) -> None:
        """Recursively delete a folder. Idempotent on missing target.

        Any depth allowed. Raises :class:`ValueError` if ``parts`` is empty
        (would delete the data root) or if the resolved target is a file
        rather than a folder.
        """
        segments = self._split(parts)
        if not segments:
            raise ValueError("Cannot delete the data root.")
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if not target.exists():
                return  # idempotent per PLAN.md §6.2
            if not target.is_dir():
                raise ValueError(
                    f"Target is a file, not a folder: {target}"
                )
            shutil.rmtree(target)
            self._mark_write(target)

    # -- File move --------------------------------------------------------

    def move_file(
        self, parts: PartsLike, dest_parent: PartsLike
    ) -> None:
        """Move a ``.feature`` file to a different parent folder.

        The leaf (file name) is preserved — renaming is a separate operation
        (:meth:`rename_file`). The destination parent must be an existing
        folder at depth ``2..MAX_FOLDER_DEPTH`` (same rule that gates
        :meth:`create_file`); a move into the source's current parent is
        rejected as a no-op so the caller is forced to surface a clearer
        intent.

        Raises :class:`FileNotFoundError` if the source file or the
        destination parent folder is missing; :class:`NameConflictError`
        if a file of the same name already exists at the destination;
        :class:`ValueError` for invalid paths, depth out of range, or
        same-parent attempts.

        Locking mirrors :meth:`rename_file` / :meth:`duplicate_file`:
        acquires source + destination locks in sorted order to avoid
        deadlocks under concurrent moves.
        """
        segments = self._split(parts)
        if not segments:
            raise ValueError("move_file requires a non-empty source path.")
        for seg in segments:
            self._validate_segment(seg)

        dest_parent_segments = self._split(dest_parent)
        for seg in dest_parent_segments:
            self._validate_segment(seg)
        if not (2 <= len(dest_parent_segments) <= MAX_FOLDER_DEPTH):
            raise ValueError(
                "move_file destination parent must be a module or sub-folder "
                f"(2..{MAX_FOLDER_DEPTH} segments); got "
                f"{len(dest_parent_segments)} segment(s)."
            )

        source = self._resolve(segments)
        if not source.is_file():
            raise FileNotFoundError(f"File not found: {source}")

        if dest_parent_segments == segments[:-1]:
            raise ValueError(
                "move_file destination parent is the same as the source "
                "parent; use rename_file or omit the move."
            )

        dest_parent_path = self._resolve(dest_parent_segments)
        if not dest_parent_path.is_dir():
            raise FileNotFoundError(
                f"Destination folder does not exist: "
                f"{'/'.join(dest_parent_segments)!r}"
            )

        leaf = segments[-1]
        target_segments = [*dest_parent_segments, leaf]
        target = self._resolve(target_segments)

        src_key = self._key(segments)
        dst_key = self._key(target_segments)
        first, second = sorted([src_key, dst_key])
        with self._lock_for(first), self._lock_for(second):
            if target.exists():
                raise NameConflictError(
                    path=dst_key,
                    message=f"A file named {leaf!r} already exists at "
                            f"{'/'.join(dest_parent_segments)!r}.",
                )
            os.replace(source, target)
            self._mark_write(source)
            self._mark_write(target)

    # -- File duplicate ---------------------------------------------------

    def duplicate_file(self, parts: PartsLike, new_name: str) -> None:
        """Copy a file to a new name within the same parent folder.

        Same-parent and same-extension rules as :meth:`rename_file`. Uses the
        atomic-write primitive so the destination appears in one step.
        """
        segments = self._split(parts)
        if not segments:
            raise ValueError("duplicate_file requires a non-empty path.")
        source = self._resolve(segments)
        if not source.is_file():
            raise FileNotFoundError(f"File not found: {source}")

        new_leaf = _normalize_filename(new_name)
        self._validate_segment(new_leaf)
        target_segments = [*segments[:-1], new_leaf]
        target = self._resolve(target_segments)

        if source == target:
            raise ValueError("Duplicate name must differ from source.")

        src_key = self._key(segments)
        dst_key = self._key(target_segments)
        first, second = sorted([src_key, dst_key])
        with self._lock_for(first), self._lock_for(second):
            if target.exists():
                raise NameConflictError(
                    path=dst_key,
                    message=f"A file named {new_leaf!r} already exists.",
                )
            data = source.read_bytes()
            self._atomic_write_bytes(target, data)
            self._mark_write(target)

    # -- Run CRUD (test-run typed area) ---------------------------------
    #
    # Runs live at ``<project>/test-run/<group>/<file_name>.yaml``. The
    # generic folder / file APIs reject any path passing through
    # ``test-run`` at index 1 (see :meth:`_reject_reserved_typed_area`);
    # the methods below are the *only* writers under the typed area.
    # See ``specs/features/10-feature-test-run-NEW.md`` for the design.

    def _run_segments(
        self,
        project: str,
        group: str | None = None,
        file_name: str | None = None,
    ) -> list[str]:
        """Build + validate the segment list for a path under the typed area.

        Always returns at minimum ``[project, "test-run"]``. ``group`` and
        ``file_name`` are appended when provided. ``file_name`` is
        normalised via :func:`_normalize_run_filename`.
        """
        self._validate_segment(project)
        segments = [project, _TEST_RUN_AREA]
        if group is not None:
            self._validate_segment(group)
            segments.append(group)
            if file_name is not None:
                leaf = _normalize_run_filename(file_name)
                self._validate_segment(leaf)
                segments.append(leaf)
        return segments

    @staticmethod
    def _serialize_run(run: TestRun) -> bytes:
        """Render a :class:`TestRun` to canonical YAML bytes.

        Calls :func:`validate_run` first so invalid runs never reach disk.
        Dump flags are chosen for canonical idempotence: insertion-order
        keys, block style, no line wrapping, full Unicode passthrough.
        """
        validate_run(run)
        text = yaml.safe_dump(
            run.to_dict(),
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            width=10**9,
        )
        return text.encode("utf-8")

    @staticmethod
    def _parse_run(text: str) -> TestRun:
        """Parse YAML bytes back into a :class:`TestRun`.

        Wraps :class:`yaml.YAMLError` (and "root is not a mapping"
        rejections) into :class:`RunParseError` so the HTTP layer can
        surface a uniform 422 envelope.
        """
        try:
            payload = yaml.safe_load(text)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None) or getattr(
                e, "context_mark", None
            )
            line = (mark.line + 1) if mark is not None else 0
            column = (mark.column + 1) if mark is not None else 0
            message = getattr(e, "problem", None) or str(e)
            raise RunParseError(
                line=line, column=column, message=message
            ) from e
        if not isinstance(payload, dict):
            raise RunParseError(
                line=0,
                column=0,
                message=(
                    f"Run file root must be a YAML mapping; "
                    f"got {type(payload).__name__}."
                ),
            )
        return TestRun.from_dict(payload)

    def create_run_group(self, project: str, group: str) -> None:
        """Create ``<project>/test-run/<group>/`` lazily.

        Auto-creates ``<project>/test-run/`` if missing (this is the
        single intended writer of that folder). The project folder
        itself must already exist. Raises :class:`NameConflictError`
        if the group folder already exists,
        :class:`FileNotFoundError` if the project is missing.
        """
        segments = self._run_segments(project, group)
        area_segments = segments[:2]
        area_path = self._resolve(area_segments)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if not area_path.parent.is_dir():
                raise FileNotFoundError(
                    f"Project folder does not exist: {project!r}"
                )
            if target.exists():
                raise NameConflictError(
                    path=key,
                    message=f"A group named {group!r} already exists.",
                )
            # Lazy-create the typed-area folder first; ``parents=False``
            # keeps the project-must-exist check above honest.
            if not area_path.exists():
                area_path.mkdir(parents=False, exist_ok=False)
                self._mark_write(area_path)
            target.mkdir(parents=False, exist_ok=False)
            self._mark_write(target)

    def delete_run_group(self, project: str, group: str) -> None:
        """Delete an empty group folder. Idempotent on missing target.

        Refuses if the group contains any runs (forces explicit
        :meth:`delete_run` first). The typed-area folder ``test-run/``
        itself is left in place even if it becomes empty — its lifecycle
        is owned by :meth:`create_run_group`.
        """
        segments = self._run_segments(project, group)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if not target.exists():
                return  # idempotent
            if not target.is_dir():
                raise ValueError(
                    f"Target is a file, not a folder: {target}"
                )
            if any(target.iterdir()):
                raise ValueError(
                    f"Group {group!r} is not empty; delete its runs first."
                )
            target.rmdir()
            self._mark_write(target)

    def list_run_groups(self, project: str) -> list[str]:
        """Return group folder names under ``<project>/test-run/``.

        Returns ``[]`` if the project has no ``test-run/`` folder yet
        (lazy creation: the folder is only made by the first
        :meth:`create_run_group` call).
        """
        segments = self._run_segments(project)
        area_path = self._resolve(segments)
        if not area_path.is_dir():
            return []
        out: list[str] = []
        for entry in area_path.iterdir():
            if entry.is_dir() and not TEMP_FILE_RE.match(entry.name):
                out.append(entry.name)
        return out

    def list_runs(self, project: str, group: str) -> list[dict[str, Any]]:
        """Return run-summary dicts for every run in ``<project>/<group>``.

        Each entry has shape::

            {
              "file_name": str,
              "name": str,
              "created_at": str,
              "case_count": int,
              "results_count_by_status": {<status>: int, ...},
            }

        Files that fail to parse are still listed with empty fields so
        the UI can surface them for repair (mirrors :meth:`list_folder`'s
        best-effort policy for unparseable ``.feature`` files).
        """
        segments = self._run_segments(project, group)
        target = self._resolve(segments)
        if not target.is_dir():
            return []
        out: list[dict[str, Any]] = []
        for entry in target.iterdir():
            name = entry.name
            if not entry.is_file():
                continue
            if TEMP_FILE_RE.match(name):
                continue
            if not name.lower().endswith(_RUN_EXT):
                continue
            try:
                run = self.read_run(project, group, name)
                counts: dict[str, int] = {}
                for r in run.results:
                    counts[r.result] = counts.get(r.result, 0) + 1
                out.append(
                    {
                        "file_name": name,
                        "name": run.name,
                        "created_at": run.created_at,
                        "case_count": len(run.results),
                        "results_count_by_status": counts,
                    }
                )
            except (RunParseError, OSError, UnicodeDecodeError):
                out.append(
                    {
                        "file_name": name,
                        "name": "",
                        "created_at": "",
                        "case_count": 0,
                        "results_count_by_status": {},
                    }
                )
        return out

    def create_run(
        self,
        project: str,
        group: str,
        name: str,
        file_name: str,
        case_paths: list[str],
        description: str = "",
    ) -> None:
        """Create a new run file.

        ``case_paths`` becomes the initial ``results`` list, each entry
        a fresh :class:`RunResult` with ``"PENDING"`` and empty remark.
        ``created_at`` is stamped server-side in UTC ISO-8601 form;
        callers cannot override it.

        Raises :class:`FileNotFoundError` if the group does not yet
        exist (use :meth:`create_run_group` first),
        :class:`NameConflictError` if the run file already exists,
        and :class:`~app.errors.ValidationError` on any invariant
        violation (empty name, duplicate case_paths, etc.).
        """
        segments = self._run_segments(project, group, file_name)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if not target.parent.is_dir():
                raise FileNotFoundError(
                    f"Group does not exist: {project}/{_TEST_RUN_AREA}/{group}"
                )
            if target.exists():
                raise NameConflictError(
                    path=key,
                    message=f"A run named {segments[-1]!r} already exists.",
                )
            run = TestRun(
                name=name,
                created_at=datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                description=description,
                results=[
                    RunResult(file_path=p, result="PENDING", remark="")
                    for p in case_paths
                ],
            )
            data = self._serialize_run(run)
            self._atomic_write_bytes(target, data)
            self._mark_write(target)

    def read_run(
        self, project: str, group: str, file_name: str
    ) -> TestRun:
        """Read + parse a run file.

        Raises :class:`FileNotFoundError` if the file is missing,
        :class:`~app.errors.RunParseError` if the YAML is malformed.
        """
        segments = self._run_segments(project, group, file_name)
        target = self._resolve(segments)
        if not target.is_file():
            raise FileNotFoundError(f"Run not found: {target}")
        text = target.read_text(encoding="utf-8")
        return self._parse_run(text)

    def write_run(
        self,
        project: str,
        group: str,
        file_name: str,
        run: TestRun,
    ) -> None:
        """Atomic whole-doc replace of an existing run file.

        Raises :class:`FileNotFoundError` if the target file does not
        exist (use :meth:`create_run` instead). Pre-write validation is
        performed by :meth:`_serialize_run`.
        """
        segments = self._run_segments(project, group, file_name)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if not target.is_file():
                raise FileNotFoundError(
                    f"Cannot update missing run: {target}"
                )
            data = self._serialize_run(run)
            self._atomic_write_bytes(target, data)
            self._mark_write(target)

    def delete_run(
        self, project: str, group: str, file_name: str
    ) -> None:
        """Delete a run file. Idempotent on missing target."""
        segments = self._run_segments(project, group, file_name)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            try:
                target.unlink()
            except FileNotFoundError:
                return  # idempotent
            except IsADirectoryError as e:
                raise ValueError(
                    f"Target is a directory, not a file: {target}"
                ) from e
            self._mark_write(target)

    def add_run_case(
        self,
        project: str,
        group: str,
        file_name: str,
        case_path: str,
    ) -> None:
        """Append a fresh :class:`RunResult` (``PENDING``, empty remark).

        Rejects duplicates with :class:`NameConflictError` (409). Per
        the spec, ``case_path`` is not validated against disk — tombstone
        rendering at the UI layer handles missing files.
        """
        if not case_path:
            raise ValueError("case_path must be a non-empty string.")
        segments = self._run_segments(project, group, file_name)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if not target.is_file():
                raise FileNotFoundError(
                    f"Cannot mutate missing run: {target}"
                )
            run = self._parse_run(target.read_text(encoding="utf-8"))
            if any(r.file_path == case_path for r in run.results):
                raise NameConflictError(
                    path=f"{self._key(segments)}#{case_path}",
                    message=(
                        f"Case {case_path!r} is already in this run."
                    ),
                )
            run.results.append(
                RunResult(file_path=case_path, result="PENDING", remark="")
            )
            data = self._serialize_run(run)
            self._atomic_write_bytes(target, data)
            self._mark_write(target)

    def remove_run_case(
        self,
        project: str,
        group: str,
        file_name: str,
        case_path: str,
    ) -> None:
        """Remove the matching :class:`RunResult`. Idempotent.

        Silently returns if no entry has ``case_path`` (mirrors
        :meth:`delete_file` / :meth:`delete_run` semantics).
        """
        if not case_path:
            raise ValueError("case_path must be a non-empty string.")
        segments = self._run_segments(project, group, file_name)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if not target.is_file():
                raise FileNotFoundError(
                    f"Cannot mutate missing run: {target}"
                )
            run = self._parse_run(target.read_text(encoding="utf-8"))
            kept = [r for r in run.results if r.file_path != case_path]
            if len(kept) == len(run.results):
                return  # idempotent: nothing to remove
            run.results = kept
            data = self._serialize_run(run)
            self._atomic_write_bytes(target, data)
            self._mark_write(target)

    def update_run_result(
        self,
        project: str,
        group: str,
        file_name: str,
        case_path: str,
        *,
        result: str | None = None,
        remark: str | None = None,
    ) -> None:
        """Partial update of a single :class:`RunResult`.

        ``result`` and ``remark`` are independently optional; at least
        one must be provided. Raises :class:`FileNotFoundError` if the
        run is missing; :class:`ValueError` if the case is not in the
        run (use :meth:`add_run_case` first) or both kwargs are
        ``None``; :class:`~app.errors.ValidationError` (via
        :meth:`_serialize_run`) if ``result`` is not in
        :data:`~app.models.RUN_RESULTS`.
        """
        if not case_path:
            raise ValueError("case_path must be a non-empty string.")
        if result is None and remark is None:
            raise ValueError(
                "update_run_result requires at least one of 'result' "
                "or 'remark'."
            )
        segments = self._run_segments(project, group, file_name)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if not target.is_file():
                raise FileNotFoundError(
                    f"Cannot mutate missing run: {target}"
                )
            run = self._parse_run(target.read_text(encoding="utf-8"))
            for r in run.results:
                if r.file_path == case_path:
                    if result is not None:
                        r.result = result
                    if remark is not None:
                        r.remark = remark
                    break
            else:
                raise ValueError(
                    f"Case {case_path!r} is not in this run; "
                    "add it via add_run_case first."
                )
            data = self._serialize_run(run)
            self._atomic_write_bytes(target, data)
            self._mark_write(target)
