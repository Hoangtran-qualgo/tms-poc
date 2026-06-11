"""Domain exception types + HTTP mapping.

Populated across PLAN.md Do steps 2–11.

Currently defined:
- ``ValidationError`` — raised by ``models.validate_feature`` and by the
  serializer pre-write validation (see PLAN.md §5.2).
- ``GherkinParseError`` — raised by ``gherkin_io.parse_feature`` on any
  parser failure or domain-level rejection (Rule blocks, multi-scenario).
- ``NameConflictError`` — raised by ``storage`` create / rename / duplicate
  operations when the target name already exists in its parent folder.
- ``RunParseError`` — raised by ``storage.read_run`` when a run file's YAML
  is malformed. Mirrors :class:`GherkinParseError`'s shape; maps to HTTP
  ``422``.
- ``EnumsParseError`` — raised by ``storage.read_project_enums`` when the
  project's ``enums.yaml`` is malformed or violates the schema. Mirrors
  :class:`RunParseError`'s shape; maps to HTTP ``422``.
"""

from __future__ import annotations


class ValidationError(Exception):
    """A model value violates a write-time invariant.

    ``field`` is a dotted path locating the offending value
    (e.g. ``scenario.steps[2].text``); ``message`` is human-readable.
    """

    __slots__ = ("field", "message")

    def __init__(self, *, field: str, message: str) -> None:
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message


class GherkinParseError(Exception):
    """Source text cannot be parsed into a :class:`~app.models.Feature`.

    Wraps either the underlying parser's failure or one of our domain-level
    rejections (Rule block, multi-scenario file, missing Feature header).
    ``line`` / ``column`` are 1-indexed when known, ``0`` when not available.
    """

    __slots__ = ("line", "column", "message")

    def __init__(self, *, line: int, column: int, message: str) -> None:
        super().__init__(f"{line}:{column}: {message}")
        self.line = line
        self.column = column
        self.message = message


class NameConflictError(Exception):
    """The target name already exists at its parent folder.

    Raised by storage create / rename / duplicate operations. Maps to HTTP
    ``409`` at the API layer.
    """

    __slots__ = ("path", "message")

    def __init__(self, *, path: str, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message


class RunParseError(Exception):
    """A run file's YAML cannot be parsed.

    Raised by ``storage.read_run`` when the on-disk YAML is malformed.
    ``line`` / ``column`` are 1-indexed when known and ``0`` when not
    available (PyYAML reports them on most syntax errors). Maps to HTTP
    ``422`` at the API layer.
    """

    __slots__ = ("line", "column", "message")

    def __init__(self, *, line: int, column: int, message: str) -> None:
        super().__init__(f"{line}:{column}: {message}")
        self.line = line
        self.column = column
        self.message = message


class ReportParseError(Exception):
    """A quality-report file's YAML cannot be parsed.

    Raised by ``storage.read_report`` when the on-disk YAML is malformed
    or its root is not a mapping. ``line`` / ``column`` are 1-indexed when
    PyYAML reports them and ``0`` otherwise. Maps to HTTP ``422``
    ``report_parse_error`` at the API layer (mirrors :class:`RunParseError`).
    """

    __slots__ = ("line", "column", "message")

    def __init__(self, *, line: int, column: int, message: str) -> None:
        super().__init__(f"{line}:{column}: {message}")
        self.line = line
        self.column = column
        self.message = message


class EnumInUseError(Exception):
    """A would-be enum removal/clear is blocked because a case still uses it.

    Raised by ``storage.write_project_enums`` (incidental removal) and
    ``storage.clear_project_enums`` when dropping a ``(kind, key)`` that at
    least one ``.feature`` still references. Carries the offending pair, the
    usage ``count``, and a small ``sample`` of referencing case paths so the
    UI can tell the user exactly which case to clear. Maps to HTTP ``409``
    ``enum_in_use`` at the API layer.
    """

    __slots__ = ("kind", "key", "count", "sample", "message")

    def __init__(
        self,
        *,
        kind: str,
        key: str,
        count: int,
        sample: list[str],
        message: str,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.key = key
        self.count = count
        self.sample = sample
        self.message = message


class EnumsParseError(Exception):
    """A project's ``enums.yaml`` is malformed or violates the schema.

    Raised by ``storage.read_project_enums`` for malformed YAML, for
    schema violations (non-list value under a kind, non-dict list element,
    invalid key identifier, multi-line label, duplicate inner key), and
    propagated through every storage path that cross-checks a saved
    ``Feature.enums`` against the project's vocabulary.

    ``line`` / ``column`` are 1-indexed when PyYAML reports a location
    (``MarkedYAMLError`` family) and ``0`` otherwise. Maps to HTTP
    ``422`` ``enums_parse_error`` at the API layer.
    """

    __slots__ = ("line", "column", "message")

    def __init__(self, *, line: int, column: int, message: str) -> None:
        super().__init__(f"{line}:{column}: {message}")
        self.line = line
        self.column = column
        self.message = message
