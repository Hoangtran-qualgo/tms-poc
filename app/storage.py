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
from pathlib import Path
from typing import Any, Union
from weakref import WeakValueDictionary

from .errors import GherkinParseError, NameConflictError
from .gherkin_io import parse_feature, serialize_feature
from .models import Feature, Scenario

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

#: How long after a successful write the watcher should ignore FS events
#: for that path (self-write suppression, PLAN.md §7). The watcher imports
#: this constant directly to ensure both sides agree on the window.
RECENT_WRITE_TTL_SECONDS: float = 0.5

#: Maximum allowed folder nesting depth. Depth-1 = project, depth-2 = module,
#: depth-3..MAX = arbitrary sub-folders under modules. A `.feature` file can
#: live in any folder at depth >= 2 (i.e. its path has 3..MAX+1 segments).
#: Revisits PLAN.md decision B4 which previously capped depth at 2.
MAX_FOLDER_DEPTH: int = 10


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

    def list_folder(self, parts: PartsLike) -> dict[str, Any]:
        """Return one folder's contents per PLAN.md §6.2 / §16.7.

        Variants returned by depth:

        - 0 (empty parts) → ``{kind: "root", projects: [name, ...]}``
        - 1 → ``{kind: "project", modules: [name, ...]}``
        - 2 → ``{kind: "module", folders: [name, ...], features: [...]}``
        - 3..MAX_FOLDER_DEPTH → ``{kind: "subfolder", folders: [...], features: [...]}``

        At depths 2 and beyond a folder may contain BOTH `.feature` files
        and sub-folders. This is the bullet "Increase folder nesting depth
        up to 10 levels" — see IN-PROGRESS.md.

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
                if entry.is_dir() and not TEMP_FILE_RE.match(entry.name):
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
            text = serialize_feature(feature)
            self._atomic_write_bytes(target, text.encode("utf-8"))
            self._mark_write(target)

    def write_feature(self, parts: PartsLike, feature: Feature) -> None:
        """Serialise and atomically write an existing file's :class:`Feature`.

        Raises :class:`FileNotFoundError` if the target file does not exist
        (use :meth:`create_file` instead). The serialiser performs all
        write-time validation; raises :class:`~app.errors.ValidationError`
        on any invariant violation.
        """
        segments = self._split(parts)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if not target.is_file():
                raise FileNotFoundError(
                    f"Cannot update missing file: {target}"
                )
            text = serialize_feature(feature)
            self._atomic_write_bytes(target, text.encode("utf-8"))
            self._mark_write(target)

    def write_raw(self, parts: PartsLike, text: str) -> None:
        """Atomically write raw text to an existing ``.feature`` file.

        Parses ``text`` first to enforce Gherkin validity (raises
        :class:`~app.errors.GherkinParseError` on bad input). Newlines are
        normalised to LF before being persisted so the file format stays
        consistent regardless of the editor's input encoding.
        """
        parse_feature(text)  # raises GherkinParseError on bad input
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")

        segments = self._split(parts)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if not target.is_file():
                raise FileNotFoundError(
                    f"Cannot update missing file: {target}"
                )
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
