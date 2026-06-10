"""Quality-report domain model + write-time validation.

Persisted as a single YAML file at ``<project>/report/<file_name>.yaml`` —
see ``specs/features/12-feature-quality-report-NEW.md``. Pure (no FS, no
HTTP).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..errors import ValidationError
from ._common import (
    ENUM_IDENTIFIER_RE,
    REPORT_TYPES,
    RUN_RESULTS,
    RUN_SET_TYPES,
    _is_single_line,
)


@dataclass(slots=True)
class Report:
    """A persisted quality report.

    Stored as a single YAML file at ``<project>/report/<file_name>.yaml``.
    ``type`` is the immutable discriminator (:data:`REPORT_TYPES`); only the
    config fields relevant to that type are populated. Run-set types carry
    ``run_paths`` (editable); the folder type (``tag_inventory``) carries a
    ``scope`` + surveyed ``tag``. All paths are data-root-relative POSIX and
    include the project, consistent with :class:`RunResult` / :class:`TestRun`.
    """

    type: str = ""
    title: str = ""
    created_at: str = ""
    run_paths: list[str] = field(default_factory=list)
    scope: str = ""
    status: str = ""
    kind: str = ""
    case_path: str = ""
    tag: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "title": self.title,
            "created_at": self.created_at,
            "run_paths": list(self.run_paths),
            "scope": self.scope,
            "status": self.status,
            "kind": self.kind,
            "case_path": self.case_path,
            "tag": self.tag,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Report":
        return cls(
            type=str(payload.get("type", "")),
            title=str(payload.get("title", "")),
            created_at=str(payload.get("created_at", "")),
            run_paths=[str(p) for p in payload.get("run_paths", [])],
            scope=str(payload.get("scope", "")),
            status=str(payload.get("status", "")),
            kind=str(payload.get("kind", "")),
            case_path=str(payload.get("case_path", "")),
            tag=str(payload.get("tag", "")),
        )


def validate_report(report: Report) -> None:
    """Raise :class:`ValidationError` if ``report`` violates pure invariants.

    Disk/project cross-checks (does ``kind`` exist in ``enums.yaml``? do the
    ``run_paths`` resolve? is ``case_path`` / ``scope`` a real path?) are
    storage concerns, not model concerns — mirroring :func:`validate_feature`
    vs the storage enum cross-check in spec 11.
    """

    if report.type not in REPORT_TYPES:
        raise ValidationError(
            field="type",
            message=(
                f"Invalid report type: {report.type!r}. "
                f"Must be one of {sorted(REPORT_TYPES)}."
            ),
        )

    if not report.title.strip():
        raise ValidationError(
            field="title", message="Report title must not be empty."
        )
    if not _is_single_line(report.title):
        raise ValidationError(
            field="title", message="Report title must be single-line."
        )

    if not report.created_at.strip():
        raise ValidationError(
            field="created_at", message="created_at must not be empty."
        )
    if not _is_single_line(report.created_at):
        raise ValidationError(
            field="created_at", message="created_at must be single-line."
        )

    # -- Per-type config -------------------------------------------------
    if report.type == "enum_ranking":
        _require_run_status(report.status)
        if not report.kind or not ENUM_IDENTIFIER_RE.fullmatch(report.kind):
            raise ValidationError(
                field="kind",
                message=(
                    f"enum_ranking kind must match "
                    f"{ENUM_IDENTIFIER_RE.pattern}."
                ),
            )
    elif report.type == "tag_ranking":
        _require_run_status(report.status)
    elif report.type == "case_trend":
        if not report.case_path.strip():
            raise ValidationError(
                field="case_path",
                message="case_trend case_path must not be empty.",
            )
    elif report.type == "tag_inventory":
        if not report.tag.strip():
            raise ValidationError(
                field="tag",
                message="tag_inventory tag must not be empty.",
            )
        if not report.scope.strip():
            raise ValidationError(
                field="scope",
                message="tag_inventory scope must not be empty.",
            )

    # -- Data-source shape exclusivity -----------------------------------
    if report.type in RUN_SET_TYPES:
        if report.scope:
            raise ValidationError(
                field="scope",
                message="scope must be empty for run-set report types.",
            )
        if report.tag:
            raise ValidationError(
                field="tag",
                message="tag must be empty for run-set report types.",
            )
        if len(report.run_paths) > 10:
            raise ValidationError(
                field="run_paths",
                message="A report may reference at most 10 runs.",
            )
        seen: set[str] = set()
        for i, p in enumerate(report.run_paths):
            if not p:
                raise ValidationError(
                    field=f"run_paths[{i}]",
                    message="run path must not be empty.",
                )
            if p in seen:
                raise ValidationError(
                    field=f"run_paths[{i}]",
                    message=f"Duplicate run path: {p!r}.",
                )
            seen.add(p)
    else:  # FOLDER_TYPES
        if report.run_paths:
            raise ValidationError(
                field="run_paths",
                message="run_paths must be empty for folder report types.",
            )


def _require_run_status(status: str) -> None:
    if status not in RUN_RESULTS:
        raise ValidationError(
            field="status",
            message=(
                f"Invalid status: {status!r}. "
                f"Must be one of {list(RUN_RESULTS)}."
            ),
        )
