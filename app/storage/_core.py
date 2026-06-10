"""Storage core: constants, free functions, the path lock, and the base.

This is the leaf of the storage package — it imports only stdlib + the
errors module, never a sibling mixin, so it can be imported by every mixin
without risking a cycle. :class:`_StorageBase` owns the shared instance
state (locks, self-write bookkeeping, the enums cache), path discipline,
and the atomic-write primitive used across the feature-area mixins.

Module-level :func:`cleanup_orphan_temp_files` remains a free function so
that ``app.create_app`` can call it before constructing :class:`Storage`.
"""

from __future__ import annotations

import os
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Union
from weakref import WeakValueDictionary

from ..errors import NameConflictError

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

#: Reserved typed-area folder name for persisted quality reports. Like
#: ``test-run``, it lives at depth 1 under a project and is written only
#: by the dedicated report APIs. See
#: ``specs/features/12-feature-quality-report-NEW.md``.
_REPORT_AREA = "report"

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
RESERVED_DEPTH2_NAMES: frozenset[str] = frozenset({"test-run", "report"})

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


def _normalize_report_filename(name: str) -> str:
    """Auto-append ``.yaml`` if no extension; reject any other extension.

    Report files live as ``<project>/report/<file_name>.yaml`` and are
    written exclusively by the typed-area APIs. Mirrors
    :func:`_normalize_run_filename`.
    """
    if not name:
        raise ValueError("Report file name must not be empty.")
    if name.lower().endswith(_RUN_EXT):
        return name
    if "." in name:
        raise ValueError(
            f"Report file name must end with '.yaml' (case-insensitive); "
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
# Storage base — shared state, path discipline, locking, atomic write
# ---------------------------------------------------------------------------


class _StorageBase:
    """Foundational layer shared by every storage mixin.

    Owns construction + the per-instance state (locks, self-write
    bookkeeping, enums cache), the path-discipline helpers, the per-path
    locking, and the atomic-write primitive. Mixins build feature-area
    methods on top of these via ``self`` on the composed :class:`Storage`.
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
