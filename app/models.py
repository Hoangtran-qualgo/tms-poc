"""Domain dataclasses for TMS.

A single ``.feature`` file maps to exactly one :class:`Feature`, which holds
exactly one :class:`Scenario` (or scenario outline). Wire-shape conventions
are documented in PLAN.md §4 (model) and §16 (JSON shapes).

Storage conventions:

- Tag values are stored **without** a leading ``@``. The parser strips and the
  serializer prepends.
- DataTable / Examples cells are stored **unescaped**. The parser unescapes
  ``\\|`` and ``\\\\``; the serializer re-escapes.
- Description strings hold real newlines. The serializer encodes them as the
  literal two-character sequence ``\\n`` when writing; the parser decodes back.

This module is pure (no FS, no HTTP). The serializer in ``gherkin_io`` calls
:func:`validate_feature` before writing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import ValidationError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Canonical English step keywords accepted by the parser and serializer.
CANONICAL_KEYWORDS: tuple[str, ...] = ("Given", "When", "Then", "And", "But")

#: Valid values for :attr:`Scenario.kind`.
SCENARIO_KINDS: tuple[str, ...] = ("scenario", "outline")

#: Valid values for :attr:`RunResult.result`. Order is meaningful only to
#: the UI (rendered left-to-right in the result `<select>`); on disk any
#: of these strings is accepted. Default for a newly-added case is
#: ``"PENDING"``.
RUN_RESULTS: tuple[str, ...] = (
    "PENDING",
    "IN-PROGRESS",
    "PASSED",
    "FAILED",
    "SKIPPED",
)

__all__ = [
    "Step",
    "ExamplesTable",
    "Scenario",
    "Background",
    "Feature",
    "RunResult",
    "TestRun",
    "CANONICAL_KEYWORDS",
    "SCENARIO_KINDS",
    "RUN_RESULTS",
    "validate_feature",
    "validate_run",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Step:
    """A single Given/When/Then/And/But step.

    ``text`` is single-line and non-empty at write time. ``data_table`` is
    ``None`` when absent; otherwise a rectangular ``list[list[str]]`` where
    row 0 is treated as the header by tool convention (the Gherkin spec
    itself does not formalize a header row — see PLAN.md §4).
    """

    keyword: str
    text: str
    data_table: list[list[str]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyword": self.keyword,
            "text": self.text,
            "data_table": (
                [list(row) for row in self.data_table]
                if self.data_table is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Step":
        dt = payload.get("data_table")
        return cls(
            keyword=str(payload.get("keyword", "")),
            text=str(payload.get("text", "")),
            data_table=(
                [[str(c) for c in row] for row in dt] if dt is not None else None
            ),
        )


@dataclass(slots=True)
class ExamplesTable:
    """A single ``Examples:`` block under a scenario outline.

    ``name`` is an empty string when absent. ``tags`` are stored without
    the leading ``@``.
    """

    tags: list[str] = field(default_factory=list)
    name: str = ""
    header: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tags": list(self.tags),
            "name": self.name,
            "header": list(self.header),
            "rows": [list(row) for row in self.rows],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ExamplesTable":
        return cls(
            tags=[str(t) for t in payload.get("tags", [])],
            name=str(payload.get("name", "")),
            header=[str(c) for c in payload.get("header", [])],
            rows=[[str(c) for c in row] for row in payload.get("rows", [])],
        )


@dataclass(slots=True)
class Scenario:
    """The single scenario (or scenario outline) carried by a feature.

    For ``kind == "outline"``, :attr:`examples` must contain at least one
    :class:`ExamplesTable` at write time. For ``kind == "scenario"``,
    :attr:`examples` must be empty.
    """

    kind: str = "scenario"
    name: str = ""
    tags: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    examples: list[ExamplesTable] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "name": self.name,
            "tags": list(self.tags),
            "steps": [s.to_dict() for s in self.steps],
            "examples": [e.to_dict() for e in self.examples],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Scenario":
        return cls(
            kind=str(payload.get("kind", "scenario")),
            name=str(payload.get("name", "")),
            tags=[str(t) for t in payload.get("tags", [])],
            steps=[Step.from_dict(s) for s in payload.get("steps", [])],
            examples=[
                ExamplesTable.from_dict(e) for e in payload.get("examples", [])
            ],
        )


@dataclass(slots=True)
class Background:
    """Optional ``Background:`` block. Omitted from disk when ``steps`` is empty."""

    steps: list[Step] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"steps": [s.to_dict() for s in self.steps]}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Background":
        return cls(steps=[Step.from_dict(s) for s in payload.get("steps", [])])


@dataclass(slots=True)
class Feature:
    """One ``.feature`` file.

    ``description`` may contain real newlines in-memory; the serializer
    encodes them as the literal sequence ``\\n`` on disk so the
    ``Feature:`` line stays single-line (see PLAN.md §4).
    """

    description: str = ""
    tags: list[str] = field(default_factory=list)
    background: Background = field(default_factory=Background)
    scenario: Scenario = field(default_factory=Scenario)

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "tags": list(self.tags),
            "background": self.background.to_dict(),
            "scenario": self.scenario.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Feature":
        return cls(
            description=str(payload.get("description", "")),
            tags=[str(t) for t in payload.get("tags", [])],
            background=Background.from_dict(payload.get("background", {})),
            scenario=Scenario.from_dict(payload.get("scenario", {})),
        )


# ---------------------------------------------------------------------------
# Validation helpers (used by gherkin_io serializer in Do step 4)
# ---------------------------------------------------------------------------


def _is_single_line(s: str) -> bool:
    """True if ``s`` contains no newline-like character (LF, CR)."""
    return "\n" not in s and "\r" not in s


def _is_valid_tag(t: str) -> bool:
    """Tag rule per PLAN.md §4:

    Non-empty, every character in ASCII-printable range ``0x21``–``0x7E``,
    excluding ``@`` (stripped by the parser) and ``,`` (chip-input separator).
    """
    if not t:
        return False
    for ch in t:
        cp = ord(ch)
        if cp < 0x21 or cp > 0x7E:
            return False
        if ch in "@,":
            return False
    return True


def _validate_tags(tags: list[str], field_prefix: str) -> None:
    for i, tag in enumerate(tags):
        if not _is_valid_tag(tag):
            raise ValidationError(
                field=f"{field_prefix}[{i}]",
                message=(
                    f"Invalid tag value: {tag!r}. Tags must be non-empty, "
                    "ASCII-printable, and contain no whitespace, '@', or ','."
                ),
            )


def _validate_steps(steps: list[Step], field_prefix: str) -> None:
    for i, step in enumerate(steps):
        loc = f"{field_prefix}[{i}]"
        if step.keyword not in CANONICAL_KEYWORDS:
            raise ValidationError(
                field=f"{loc}.keyword",
                message=(
                    f"Invalid step keyword: {step.keyword!r}. "
                    f"Must be one of {list(CANONICAL_KEYWORDS)}."
                ),
            )
        if not _is_single_line(step.text):
            raise ValidationError(
                field=f"{loc}.text",
                message="Step text must be single-line.",
            )
        if not step.text.strip():
            raise ValidationError(
                field=f"{loc}.text",
                message="Step text must not be empty.",
            )
        if step.data_table is not None:
            if not step.data_table:
                raise ValidationError(
                    field=f"{loc}.data_table",
                    message="An empty data table must be None, not [].",
                )
            row_len = len(step.data_table[0])
            if row_len == 0:
                raise ValidationError(
                    field=f"{loc}.data_table",
                    message="Data tables must have at least one column.",
                )
            for r, row in enumerate(step.data_table):
                if len(row) != row_len:
                    raise ValidationError(
                        field=f"{loc}.data_table[{r}]",
                        message=(
                            f"Row width {len(row)} does not match the first "
                            f"row width {row_len}."
                        ),
                    )


def _validate_examples(ex: ExamplesTable, field_prefix: str) -> None:
    if not _is_single_line(ex.name):
        raise ValidationError(
            field=f"{field_prefix}.name",
            message="Examples name must be single-line.",
        )
    _validate_tags(ex.tags, f"{field_prefix}.tags")
    if not ex.header:
        raise ValidationError(
            field=f"{field_prefix}.header",
            message="Examples table must have at least one column.",
        )
    header_len = len(ex.header)
    for r, row in enumerate(ex.rows):
        if len(row) != header_len:
            raise ValidationError(
                field=f"{field_prefix}.rows[{r}]",
                message=(
                    f"Row width {len(row)} does not match header width {header_len}."
                ),
            )


def validate_feature(feature: Feature) -> None:
    """Raise :class:`ValidationError` if ``feature`` violates write-time invariants.

    The checks performed here correspond to the "Pre-write validation" block
    in PLAN.md §5.2. The serializer calls this before producing any output.
    """

    # Feature description (multi-line allowed in the model; must be non-empty
    # after strip — empty/whitespace-only is not a meaningful name).
    if not feature.description.strip():
        raise ValidationError(
            field="description",
            message="Feature description must not be empty.",
        )

    _validate_tags(feature.tags, "tags")

    # Background steps share the same step rules as the scenario.
    _validate_steps(feature.background.steps, "background.steps")

    scenario = feature.scenario

    if scenario.kind not in SCENARIO_KINDS:
        raise ValidationError(
            field="scenario.kind",
            message=(
                f"Invalid scenario kind: {scenario.kind!r}. "
                f"Must be one of {list(SCENARIO_KINDS)}."
            ),
        )

    if not _is_single_line(scenario.name):
        raise ValidationError(
            field="scenario.name",
            message="Scenario name must be single-line.",
        )

    _validate_tags(scenario.tags, "scenario.tags")
    _validate_steps(scenario.steps, "scenario.steps")

    if scenario.kind == "scenario":
        if scenario.examples:
            raise ValidationError(
                field="scenario.examples",
                message="A plain scenario cannot carry Examples tables.",
            )
    else:  # outline
        if not scenario.examples:
            raise ValidationError(
                field="scenario.examples",
                message="A Scenario Outline requires at least one Examples table.",
            )
        for i, ex in enumerate(scenario.examples):
            _validate_examples(ex, f"scenario.examples[{i}]")


# ---------------------------------------------------------------------------
# Test run dataclasses (Phase 1 of the test-run feature, see
# specs/features/10-feature-test-run-NEW.md)
# ---------------------------------------------------------------------------


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
