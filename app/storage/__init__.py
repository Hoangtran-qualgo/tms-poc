"""Storage layer (package split of the former ``storage.py``).

Owns all FS access to the data root. The single public entry point is
:class:`Storage`, assembled from per-domain mixins over the shared
:class:`._core._StorageBase`. The public surface is preserved verbatim:
``from app.storage import Storage`` and the module-level constants /
helpers (``TEMP_FILE_RE``, ``RECENT_WRITE_TTL_SECONDS``,
``MAX_FOLDER_DEPTH``, ``cleanup_orphan_temp_files``, ``_normalize_run_filename``,
``_PathLock``, …) all resolve as before.

Decentralisation map:

- ``_core``      — constants, free functions, ``_PathLock``, ``_StorageBase``
  (init + path discipline + locking + self-write + atomic write).
- ``_listing``   — root / tree / folder / project enumeration.
- ``_features``  — ``.feature`` reads + create/write/delete/rename.
- ``_enums``     — project ``enums.yaml`` read / init / parse / cross-check.
- ``_search``    — feature-content search + ``iter_feature_paths``.
- ``_folders``   — folder writes + cross-folder file move / duplicate.
- ``_runs``      — test-run typed-area CRUD.
- ``_reports``   — quality-report typed-area CRUD.

Each mixin imports only ``_core`` + stdlib + sibling app modules
(``errors`` / ``models`` / ``gherkin_io``) at module level — never a
sibling mixin — so the package graph stays acyclic. Cross-area method
calls (e.g. listing → ``read_feature``) resolve at runtime on the
composed instance.
"""

from __future__ import annotations

# Re-exported so callers/tests can reach the same `os` handle the former
# single-module `storage.py` exposed (the atomic-write smokes monkeypatch
# `app.storage.os.replace` / `.fsync`; `os` is a shared singleton, so the
# patch still reaches `_core._atomic_write_bytes`).
import os  # noqa: F401

from ._core import (
    MAX_FOLDER_DEPTH,
    RECENT_WRITE_TTL_SECONDS,
    RESERVED_DEPTH2_NAMES,
    TEMP_FILE_RE,
    PartsLike,
    _PathLock,
    _is_feature_name,
    _normalize_filename,
    _normalize_report_filename,
    _normalize_run_filename,
    _StorageBase,
    cleanup_orphan_temp_files,
)
from ._enums import EnumsMixin
from ._features import FeaturesMixin
from ._folders import FoldersMixin
from ._listing import ListingMixin
from ._reports import ReportsMixin
from ._runs import RunsMixin
from ._search import SearchMixin


class Storage(
    ListingMixin,
    FeaturesMixin,
    EnumsMixin,
    SearchMixin,
    FoldersMixin,
    RunsMixin,
    ReportsMixin,
    _StorageBase,
):
    """Single-instance owner of all FS reads/writes inside the data root.

    Every public method takes a "logical path", which may be either a string
    using ``/`` as a separator (root = ``""``) or a list of segments. The
    string form is the API/UI wire format; the list form is convenient inside
    the module. Paths are validated to stay inside :attr:`root`.

    See PLAN.md §6 for the full operations table and path discipline rules.
    The behaviour is identical to the former single-module ``Storage``; the
    class is now composed from per-domain mixins (see the package docstring).
    """


__all__ = [
    "Storage",
    "TEMP_FILE_RE",
    "RECENT_WRITE_TTL_SECONDS",
    "MAX_FOLDER_DEPTH",
    "RESERVED_DEPTH2_NAMES",
    "PartsLike",
    "cleanup_orphan_temp_files",
    "_normalize_filename",
    "_normalize_run_filename",
    "_normalize_report_filename",
    "_is_feature_name",
    "_PathLock",
]
