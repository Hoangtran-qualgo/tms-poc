"""Test-run domain model + write-time validation.

Persisted as a single YAML file at
``<project>/test-run/<group>/<file_name>.yaml`` — see
``specs/features/10-feature-test-run-NEW.md``. Pure (no FS, no HTTP).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..errors import ValidationError
from ._common import RUN_RESULTS, _is_single_line


@dataclass(slots=True)
class RunResult:
    """A single test case's recorded outcome inside a :class:`TestRun`.

    ``file_path`` is a data-root-relative POSIX path to a ``.feature`` file.
    The path is **not** validated against disk at write time — tombstone
    rendering is a UI concern. ``result`` must be one of :data:`RUN_RESULTS`.
    ``remark`` is freeform; may be empty.
    """

    file_path: str
    result: str = "PENDING"
    remark: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "result": self.result,
            "remark": self.remark,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RunResult":
        return cls(
            file_path=str(payload.get("file_path", "")),
            result=str(payload.get("result", "PENDING")),
            remark=str(payload.get("remark", "")),
        )


@dataclass(slots=True)
class TestRun:
    """One test run.

    Persisted as a single YAML file at
    ``<project>/test-run/<group>/<file_name>.yaml``. ``name`` is the human
    label (not the file name). ``created_at`` is an ISO-8601 string set at
    create time and never edited. ``results`` preserves insertion order;
    duplicate ``file_path`` values are rejected at write.
    """

    name: str = ""
    created_at: str = ""
    description: str = ""
    results: list[RunResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "created_at": self.created_at,
            "description": self.description,
            "results": [r.to_dict() for r in self.results],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TestRun":
        return cls(
            name=str(payload.get("name", "")),
            created_at=str(payload.get("created_at", "")),
            description=str(payload.get("description", "")),
            results=[
                RunResult.from_dict(r) for r in payload.get("results", [])
            ],
        )


def validate_run(run: TestRun) -> None:
    """Raise :class:`ValidationError` if ``run`` violates write-time invariants.

    Checks:

    - ``name`` is non-empty after strip and single-line.
    - ``created_at`` is non-empty and single-line.
    - Every ``result`` is one of :data:`RUN_RESULTS`.
    - No duplicate ``file_path`` across :attr:`TestRun.results`.
    - Every ``file_path`` is non-empty.

    Disk presence of each ``file_path`` is **not** checked here — tombstone
    state is a UI render-time concern, not a storage invariant.
    """

    if not run.name.strip():
        raise ValidationError(
            field="name",
            message="Run name must not be empty.",
        )
    if not _is_single_line(run.name):
        raise ValidationError(
            field="name",
            message="Run name must be single-line.",
        )

    if not run.created_at.strip():
        raise ValidationError(
            field="created_at",
            message="created_at must not be empty.",
        )
    if not _is_single_line(run.created_at):
        raise ValidationError(
            field="created_at",
            message="created_at must be single-line.",
        )

    seen: set[str] = set()
    for i, r in enumerate(run.results):
        loc = f"results[{i}]"
        if not r.file_path:
            raise ValidationError(
                field=f"{loc}.file_path",
                message="file_path must not be empty.",
            )
        if r.file_path in seen:
            raise ValidationError(
                field=f"{loc}.file_path",
                message=(
                    f"Duplicate file_path in run results: {r.file_path!r}."
                ),
            )
        seen.add(r.file_path)
        if r.result not in RUN_RESULTS:
            raise ValidationError(
                field=f"{loc}.result",
                message=(
                    f"Invalid result value: {r.result!r}. "
                    f"Must be one of {list(RUN_RESULTS)}."
                ),
            )
