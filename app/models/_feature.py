"""Feature domain model + write-time validation.

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

from ..errors import ValidationError
from ._common import (
    CANONICAL_KEYWORDS,
    ENUM_IDENTIFIER_RE,
    ENUM_KEY_RE,
    SCENARIO_KINDS,
    _is_single_line,
)


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

    ``enums`` is a generic map of project-level enum kind → selected
    key (snake-case identifier). Keys (values of this dict) are the only
    thing stored on disk; display labels live in ``<project>/enums.yaml``
    and are resolved at render time. An empty-string value is the legal
    "unset" marker for that kind. See
    ``specs/features/11-feature-testcase-component-NEW.md``.
    """

    description: str = ""
    tags: list[str] = field(default_factory=list)
    background: Background = field(default_factory=Background)
    scenario: Scenario = field(default_factory=Scenario)
    enums: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "tags": list(self.tags),
            "background": self.background.to_dict(),
            "scenario": self.scenario.to_dict(),
            "enums": dict(self.enums),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Feature":
        raw_enums = payload.get("enums") or {}
        return cls(
            description=str(payload.get("description", "")),
            tags=[str(t) for t in payload.get("tags", [])],
            background=Background.from_dict(payload.get("background", {})),
            scenario=Scenario.from_dict(payload.get("scenario", {})),
            enums={str(k): str(v) for k, v in raw_enums.items()},
        )


# ---------------------------------------------------------------------------
# Validation helpers (used by gherkin_io serializer in Do step 4)
# ---------------------------------------------------------------------------


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


def _validate_enums(enums: dict[str, str]) -> None:
    """Pure-model validation for :attr:`Feature.enums`.

    Per ``specs/features/11-feature-testcase-component-NEW.md`` Q1: kind
    names (outer keys) must match :data:`ENUM_IDENTIFIER_RE`; selected
    keys (values) must either be the empty string (= unset) or match the
    same identifier regex. Project-aware cross-checking against
    ``<project>/enums.yaml`` happens in storage, not here — the model
    has no project context.
    """
    for kind, key in enums.items():
        if not ENUM_IDENTIFIER_RE.fullmatch(kind):
            raise ValidationError(
                field="enums",
                message=(
                    f"Invalid enum kind name: {kind!r}. Kinds must match "
                    f"{ENUM_IDENTIFIER_RE.pattern}."
                ),
            )
        if key != "" and not ENUM_KEY_RE.fullmatch(key):
            raise ValidationError(
                field=f"enums[{kind}]",
                message=(
                    f"Invalid enum key: {key!r}. Keys must match "
                    f"{ENUM_KEY_RE.pattern} or be empty (= unset)."
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
    _validate_enums(feature.enums)

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
