"""Quality-report CRUD mixin (typed area under ``<project>/report/``).

Reports live under ``<project>/report/<file_name>.yaml``. Like the
test-run area, ``report/`` is reserved at depth 1 (hidden from the
Directory tree + project module listing via RESERVED_DEPTH2_NAMES);
the methods below are the only writers. Reports are flat under the
area (no group level). See
``specs/features/12-feature-quality-report-NEW.md``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import yaml

from ..errors import NameConflictError, ReportParseError, ValidationError
from ..models import FOLDER_TYPES, RUN_SET_TYPES, Report, validate_report
from ._core import (
    TEMP_FILE_RE,
    _ENUMS_FILE_NAME,
    _REPORT_AREA,
    _RUN_EXT,
    _TEST_RUN_AREA,
    _normalize_report_filename,
)


class ReportsMixin:
    """Report file lifecycle + project-relative cross-checks."""

    def _report_segments(
        self, project: str, file_name: str | None = None
    ) -> list[str]:
        """Build + validate the segment list for a path under ``report/``.

        Always returns at minimum ``[project, "report"]``. ``file_name`` is
        appended (normalised via :func:`_normalize_report_filename`) when
        provided.
        """
        self._validate_segment(project)
        segments = [project, _REPORT_AREA]
        if file_name is not None:
            leaf = _normalize_report_filename(file_name)
            self._validate_segment(leaf)
            segments.append(leaf)
        return segments

    @staticmethod
    def _report_to_persisted_dict(report: Report) -> dict[str, Any]:
        """Project a :class:`Report` to only the keys relevant to its type.

        ``type``/``title``/``created_at`` are always emitted; the config
        keys are limited to those the type uses so the on-disk file carries
        no dead fields.
        """
        out: dict[str, Any] = {
            "type": report.type,
            "title": report.title,
            "created_at": report.created_at,
        }
        if report.type == "enum_ranking":
            out["status"] = report.status
            out["kind"] = report.kind
            out["run_paths"] = list(report.run_paths)
        elif report.type == "tag_ranking":
            out["status"] = report.status
            out["run_paths"] = list(report.run_paths)
        elif report.type == "case_trend":
            out["case_path"] = report.case_path
            out["run_paths"] = list(report.run_paths)
        elif report.type == "tag_inventory":
            out["tag"] = report.tag
            out["scope"] = report.scope
        return out

    def _serialize_report(self, report: Report) -> bytes:
        """Render a :class:`Report` to canonical YAML bytes.

        Calls :func:`validate_report` first so invalid reports never reach
        disk; emits only the type-relevant keys. Dump flags match
        :meth:`_serialize_run` for canonical idempotence.
        """
        validate_report(report)
        text = yaml.safe_dump(
            self._report_to_persisted_dict(report),
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            width=10**9,
        )
        return text.encode("utf-8")

    @staticmethod
    def _parse_report(text: str) -> Report:
        """Parse YAML text back into a :class:`Report`.

        Wraps :class:`yaml.YAMLError` (and "root is not a mapping"
        rejections) into :class:`~app.errors.ReportParseError` so the HTTP
        layer can surface a uniform 422 envelope.
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
            raise ReportParseError(
                line=line, column=column, message=message
            ) from e
        if not isinstance(payload, dict):
            raise ReportParseError(
                line=0,
                column=0,
                message=(
                    f"Report file root must be a YAML mapping; "
                    f"got {type(payload).__name__}."
                ),
            )
        return Report.from_dict(payload)

    def _cross_check_report(self, project: str, report: Report) -> None:
        """Reject reports whose live references don't resolve on disk.

        Pure-shape rules live in :func:`validate_report`; this adds the
        project-relative existence checks: an ``enum_ranking`` ``kind``
        must be declared in ``enums.yaml``; every ``run_paths`` entry must
        be an existing run file under ``<project>/test-run/``; a
        ``case_trend`` ``case_path`` must be an existing file in the
        project; a ``tag_inventory`` ``scope`` must be an existing folder
        in the project. An empty run set skips the per-entry checks (D13).
        """
        if report.type == "enum_ranking":
            try:
                vocab = self.read_project_enums(project)
            except FileNotFoundError:
                raise ValidationError(
                    field="kind",
                    message=(
                        f"Cannot rank enum kind {report.kind!r}: project "
                        f"{project!r} has no {_ENUMS_FILE_NAME}."
                    ),
                )
            if report.kind not in vocab:
                raise ValidationError(
                    field="kind",
                    message=(
                        f"Unknown enum kind {report.kind!r}; not defined in "
                        f"{project}/{_ENUMS_FILE_NAME}."
                    ),
                )

        if report.type in RUN_SET_TYPES:
            for i, p in enumerate(report.run_paths):
                parts = p.split("/")
                if (
                    len(parts) != 4
                    or parts[0] != project
                    or parts[1] != _TEST_RUN_AREA
                ):
                    raise ValidationError(
                        field=f"run_paths[{i}]",
                        message=(
                            f"Run path must be "
                            f"{project}/{_TEST_RUN_AREA}/<group>/<file>: "
                            f"{p!r}."
                        ),
                    )
                if not self._resolve(parts).is_file():
                    raise ValidationError(
                        field=f"run_paths[{i}]",
                        message=f"Run not found: {p!r}.",
                    )

        if report.type == "case_trend":
            parts = report.case_path.split("/")
            if parts[0] != project:
                raise ValidationError(
                    field="case_path",
                    message=(
                        f"case_path must be inside project {project!r}: "
                        f"{report.case_path!r}."
                    ),
                )
            if not self._resolve(parts).is_file():
                raise ValidationError(
                    field="case_path",
                    message=f"Case not found: {report.case_path!r}.",
                )

        if report.type == "tag_inventory":
            parts = report.scope.split("/")
            if parts[0] != project:
                raise ValidationError(
                    field="scope",
                    message=(
                        f"scope must be inside project {project!r}: "
                        f"{report.scope!r}."
                    ),
                )
            if not self._resolve(parts).is_dir():
                raise ValidationError(
                    field="scope",
                    message=f"Scope folder not found: {report.scope!r}.",
                )

    def create_report(
        self, project: str, file_name: str, report: Report
    ) -> None:
        """Create a new report file.

        ``created_at`` is stamped server-side in UTC ISO-8601 form;
        callers cannot override it. Validates + cross-checks before any
        FS mutation so a rejected create writes nothing.

        Raises :class:`FileNotFoundError` if the project does not exist,
        :class:`NameConflictError` if the report file already exists, and
        :class:`~app.errors.ValidationError` on any invariant or
        cross-check violation.
        """
        segments = self._report_segments(project, file_name)
        area_path = self._resolve(segments[:2])
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
                    message=f"A report named {segments[-1]!r} already exists.",
                )
            report.created_at = datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            )
            validate_report(report)
            self._cross_check_report(project, report)
            # Mutations only after all checks pass.
            if not area_path.exists():
                area_path.mkdir(parents=False, exist_ok=False)
            data = self._serialize_report(report)
            self._atomic_write_bytes(target, data)
            self._mark_write(target)

    def read_report(self, project: str, file_name: str) -> Report:
        """Read + parse a report file.

        Raises :class:`FileNotFoundError` if the file is missing,
        :class:`~app.errors.ReportParseError` if the YAML is malformed.
        """
        segments = self._report_segments(project, file_name)
        target = self._resolve(segments)
        if not target.is_file():
            raise FileNotFoundError(f"Report not found: {target}")
        text = target.read_text(encoding="utf-8")
        return self._parse_report(text)

    def write_report(
        self, project: str, file_name: str, report: Report
    ) -> None:
        """Atomic whole-doc replace of an existing report file.

        Raises :class:`FileNotFoundError` if the target does not exist
        (use :meth:`create_report` instead). Validates + cross-checks
        before writing. ``created_at`` preservation across a PATCH is the
        HTTP layer's responsibility (it loads the existing report first).
        """
        segments = self._report_segments(project, file_name)
        target = self._resolve(segments)
        key = self._key(segments)
        with self._lock_for(key):
            if not target.is_file():
                raise FileNotFoundError(
                    f"Cannot update missing report: {target}"
                )
            validate_report(report)
            self._cross_check_report(project, report)
            data = self._serialize_report(report)
            self._atomic_write_bytes(target, data)
            self._mark_write(target)

    def delete_report(self, project: str, file_name: str) -> None:
        """Delete a report file. Idempotent on missing target."""
        segments = self._report_segments(project, file_name)
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

    def list_reports(self, project: str) -> list[dict[str, Any]]:
        """Return report-summary dicts for every report in ``<project>``.

        Each entry has shape ``{file_name, title, type, created_at,
        source}`` where ``source`` is a short human descriptor (the run
        count for run-set types, the scope for ``tag_inventory``). Files
        that fail to parse are still listed with empty fields so the UI can
        surface them for repair (mirrors :meth:`list_runs`).
        """
        area_path = self._resolve(self._report_segments(project))
        if not area_path.is_dir():
            return []
        out: list[dict[str, Any]] = []
        for entry in area_path.iterdir():
            name = entry.name
            if not entry.is_file() or TEMP_FILE_RE.match(name):
                continue
            if not name.lower().endswith(_RUN_EXT):
                continue
            try:
                report = self.read_report(project, name)
                source = (
                    report.scope
                    if report.type in FOLDER_TYPES
                    else f"{len(report.run_paths)} run(s)"
                )
                out.append(
                    {
                        "file_name": name,
                        "title": report.title,
                        "type": report.type,
                        "created_at": report.created_at,
                        "source": source,
                    }
                )
            except (ReportParseError, OSError, UnicodeDecodeError):
                out.append(
                    {
                        "file_name": name,
                        "title": "",
                        "type": "",
                        "created_at": "",
                        "source": "",
                    }
                )
        return out

    def list_report_tree(self) -> dict[str, Any]:
        """Return the aggregated ``report/`` subtree of every project.

        Shape mirrors :meth:`list_test_run_tree` but reports are flat
        under the area (no group level), so each project folder's children
        are report leaves directly. Leaves carry ``title`` + ``report_type``
        (best-effort; empty on parse error) so the Reports sidebar can label
        them without a second read.
        """
        children: list[dict[str, Any]] = []
        if not self.root.exists():
            return {"name": "", "children": children}
        for project_entry in self.root.iterdir():
            if not project_entry.is_dir() or TEMP_FILE_RE.match(
                project_entry.name
            ):
                continue
            report_dir = project_entry / _REPORT_AREA
            if not report_dir.is_dir():
                continue
            project = project_entry.name
            leaves: list[dict[str, Any]] = []
            for entry in report_dir.iterdir():
                name = entry.name
                if not entry.is_file() or TEMP_FILE_RE.match(name):
                    continue
                if not name.lower().endswith(_RUN_EXT):
                    continue
                try:
                    report = self.read_report(project, name)
                    title, report_type = report.title, report.type
                except (ReportParseError, OSError, UnicodeDecodeError):
                    title, report_type = "", ""
                leaves.append(
                    {
                        "type": "report",
                        "name": name,
                        "path": f"{project}/{_REPORT_AREA}/{name}",
                        "project": project,
                        "file_name": name,
                        "title": title,
                        "report_type": report_type,
                    }
                )
            children.append(
                {
                    "type": "folder",
                    "name": project,
                    "depth": 0,
                    "path": project,
                    "children": leaves,
                }
            )
        return {"name": "", "children": children}
