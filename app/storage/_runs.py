"""Run CRUD mixin (test-run typed area).

Runs live at ``<project>/test-run/<group>/<file_name>.yaml``. The
generic folder / file APIs reject any path passing through
``test-run`` at index 1 (see ``_StorageBase._reject_reserved_typed_area``);
the methods below are the *only* writers under the typed area.
See ``specs/features/10-feature-test-run-NEW.md`` for the design.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import yaml

from ..errors import NameConflictError, RunParseError
from ..models import RunResult, TestRun, validate_run
from ._core import TEMP_FILE_RE, _RUN_EXT, _TEST_RUN_AREA, _normalize_run_filename


class RunsMixin:
    """Group + run file lifecycle under ``<project>/test-run/``."""

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

    def import_test_run(
        self,
        project: str,
        group: str,
        name: str,
        file_name: str,
        created_at: str,
        results: list[RunResult],
        description: str = "",
    ) -> None:
        """Create a run file from imported results (feature-15).

        Unlike :meth:`create_run`, ``created_at`` is supplied by the caller
        (the source report's created time, not server-now) and ``results``
        carry their own per-case outcomes rather than seeding all-``PENDING``.
        Every other invariant is shared: the group must already exist, the
        target must not exist, and :meth:`_serialize_run` runs
        :func:`validate_run` before any bytes are written.

        Raises :class:`FileNotFoundError` if the group does not yet exist,
        :class:`NameConflictError` if the run file already exists, and
        :class:`~app.errors.ValidationError` on any invariant violation
        (empty name/created_at, duplicate ``file_path``, invalid result).
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
                created_at=created_at,
                description=description,
                results=list(results),
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
