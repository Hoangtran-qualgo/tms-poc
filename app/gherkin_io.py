"""Pure Gherkin parse + canonical serialize.

This module is pure: text in / model out (:func:`parse_feature`) and model
in / text out (:func:`serialize_feature`, implemented in Do step 4). No FS,
no HTTP.

Implementation notes for the parser (Do step 3):

- Input newlines are normalized to ``\\n`` before being handed to
  ``gherkin-official``'s :class:`~gherkin.parser.Parser`.
- The underlying parser already unescapes ``\\|`` and similar in table cells,
  so we take ``cell["value"]`` verbatim and do not double-unescape.
- Feature description is built from the AST as ``name + "\\n" + body`` (body
  omitted when empty), then every literal two-character ``\\n`` sequence in
  the resulting string is decoded into a real newline (round-trip support
  for files this tool itself wrote previously, see PLAN.md \u00a75.1).
- Tags are stored stripped of their leading ``@``.
- Step keywords are stripped of their trailing space and looked up in the
  five canonical English keywords; non-matching steps are silently dropped
  (documented as a data-loss risk in PLAN.md \u00a713).
- ``Rule:`` blocks and files containing more than one scenario raise
  :class:`~app.errors.GherkinParseError`.
- Zero-scenario files are repaired in-flight with a placeholder
  ``Scenario(kind="scenario")`` so the editor always has something to show.
"""

from __future__ import annotations

import re
from typing import Any

from gherkin.errors import CompositeParserException
from gherkin.parser import Parser

from .errors import GherkinParseError
from .models import (
    CANONICAL_KEYWORDS,
    ENUM_IDENTIFIER_RE,
    ENUM_KEY_RE,
    Background,
    ExamplesTable,
    Feature,
    Scenario,
    Step,
    validate_feature,
)

# Loose matcher for an ``# enum.<kind>: <key>`` directive. Anything matching
# the ``# enum.<…>:`` prefix is treated as a directive intent and then
# strict-validated against :data:`ENUM_IDENTIFIER_RE` for ``<kind>`` and
# :data:`ENUM_KEY_RE` for ``<key>``; failures surface as
# :class:`GherkinParseError`. Non-matching
# comments (e.g. ``# todo: refactor``, ``# note: see PR_47``) flow through
# unchanged and are discarded by the existing comments-are-dropped
# invariant. See ``specs/features/11-feature-testcase-component-NEW.md``.
_ENUM_DIRECTIVE_RE: re.Pattern[str] = re.compile(
    r"^#\s*enum\.([^:\s]+)\s*:\s*(.*?)\s*$"
)

__all__ = [
    "parse_feature",
    "serialize_feature",
    "split_feature_source",
    "source_has_enum_directives",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_feature(source: str) -> Feature:
    """Parse a ``.feature`` file's source text into a :class:`Feature`.

    Raises :class:`~app.errors.GherkinParseError` on any parser failure, on
    files containing a ``Rule:`` block, on files containing more than one
    scenario / scenario outline, and on files with no ``Feature:`` header.
    """

    source = _normalize_newlines(source)

    try:
        gherkin_doc: dict[str, Any] = Parser().parse(source)
    except CompositeParserException as e:
        raise _wrap_parser_exception(e) from e

    feature_ast = gherkin_doc.get("feature")
    if feature_ast is None:
        raise GherkinParseError(
            line=1,
            column=1,
            message="No 'Feature:' header found in the file.",
        )

    enums = _extract_enum_directives(
        gherkin_doc.get("comments") or [],
        feature_ast,
    )

    background_ast, scenario_asts = _collect_children(feature_ast.get("children") or [])
    if len(scenario_asts) > 1:
        loc = (scenario_asts[1] or {}).get("location") or {}
        raise GherkinParseError(
            line=int(loc.get("line", 0) or 0),
            column=int(loc.get("column", 0) or 0),
            message=(
                "More than one scenario in the file. "
                "TMS requires exactly one scenario per .feature file."
            ),
        )
    scenario_ast = scenario_asts[0] if scenario_asts else None

    description = _assemble_description(
        name=feature_ast.get("name") or "",
        body=feature_ast.get("description") or "",
    )
    tags = [_strip_at(t) for t in (feature_ast.get("tags") or [])]

    background = Background(
        steps=_extract_steps(
            background_ast.get("steps") if background_ast else None
        )
    )

    if scenario_ast is None:
        # Lenient: file has Feature but no Scenario yet. Inject placeholder.
        scenario = Scenario(kind="scenario")
    else:
        scenario = _build_scenario(scenario_ast)

    return Feature(
        description=description,
        tags=tags,
        background=background,
        scenario=scenario,
        enums=enums,
    )


def split_feature_source(source: str) -> list[Feature]:
    """Split a multi-scenario ``.feature`` source into one :class:`Feature` per scenario.

    Pure (text in / models out): the import splitter. Unlike
    :func:`parse_feature` it accepts files with **more than one** scenario
    and returns a separate :class:`Feature` for each, all **sharing** the
    file-level ``description``, feature-level ``tags`` and ``background``.
    Each :class:`Feature` keeps **its own** scenario-level tags. Enum
    directives are **dropped** (``enums`` is always emptied).

    Behavior:

    - ``Rule:`` blocks raise :class:`~app.errors.GherkinParseError` (same as
      :func:`parse_feature`).
    - A missing ``Feature:`` header is repaired by synthesizing a blank one
      (the produced features share a blank description); a deterministic
      pre-scan decides this so genuine syntax errors are not masked. Parse
      error positions are corrected for the synthesized line.
    - A header with **zero** scenarios returns ``[]`` (the caller turns this
      into a "no scenarios to import" content error).
    """
    source = _normalize_newlines(source)
    prepared, line_offset = _ensure_feature_header(source)

    try:
        gherkin_doc: dict[str, Any] = Parser().parse(prepared)
    except CompositeParserException as e:
        raise _wrap_parser_exception(e, line_offset=line_offset) from e

    feature_ast = gherkin_doc.get("feature")
    if feature_ast is None:
        # Should not happen after synthesis, but guard rather than crash.
        raise GherkinParseError(
            line=1,
            column=1,
            message="No 'Feature:' header found in the file.",
        )

    background_ast, scenario_asts = _collect_children(
        feature_ast.get("children") or []
    )

    description = _assemble_description(
        name=feature_ast.get("name") or "",
        body=feature_ast.get("description") or "",
    )
    tags = [_strip_at(t) for t in (feature_ast.get("tags") or [])]

    features: list[Feature] = []
    for scenario_ast in scenario_asts:
        # A fresh Background per case (independent Step objects) so the
        # shared steps are never aliased between produced features.
        background = Background(
            steps=_extract_steps(
                background_ast.get("steps") if background_ast else None
            )
        )
        features.append(
            Feature(
                description=description,
                tags=list(tags),
                background=background,
                scenario=_build_scenario(scenario_ast),
                enums={},
            )
        )
    return features


def source_has_enum_directives(source: str) -> bool:
    """Return ``True`` if ``source`` contains any ``# enum.<kind>: <key>`` line.

    Used by the import preview to warn that enum directives will be dropped
    (:func:`split_feature_source` always empties ``enums``). Scans every line
    for the directive shape; a loose match is intentional (over-warning is
    harmless — the user just confirms the drop).
    """
    for raw in _normalize_newlines(source).split("\n"):
        if _ENUM_DIRECTIVE_RE.match(raw.strip()):
            return True
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_newlines(source: str) -> str:
    """Convert CRLF and lone CR to LF per PLAN.md \u00a75.1."""
    return source.replace("\r\n", "\n").replace("\r", "\n")


# Matches a ``Feature:`` header line (optional leading whitespace). English
# keyword only — localized ``# language:`` files are out of scope for import.
_FEATURE_HEADER_RE: re.Pattern[str] = re.compile(r"^\s*Feature\s*:")


def _ensure_feature_header(source: str) -> tuple[str, int]:
    """Synthesize a blank ``Feature:`` header when the source lacks one.

    Returns ``(prepared_source, line_offset)`` where ``line_offset`` is the
    number of lines prepended (``1`` when synthesized, else ``0``) so callers
    can correct reported parse-error line numbers.

    A deterministic pre-scan finds the first *significant* line (skipping
    blank lines, ``#`` comments and ``@tag`` lines). If that line is not a
    ``Feature:`` header, ``Feature:\\n`` is prepended. Using a pre-scan
    rather than catching parse exceptions avoids masking genuine syntax
    errors elsewhere in the file.
    """
    for raw in source.split("\n"):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("@"):
            continue
        if _FEATURE_HEADER_RE.match(raw):
            return source, 0
        break
    return "Feature:\n" + source, 1


def _extract_enum_directives(
    comments: list[dict[str, Any]], feature_ast: dict[str, Any]
) -> dict[str, str]:
    """Walk leading ``# enum.<kind>: <key>`` directives into a key-only map.

    Cutoff line = ``min(feature.location.line, first_tag.location.line)``
    when the feature has tags, else ``feature.location.line``. Only
    comments with ``location.line < cutoff`` are considered \u2014 directives
    must precede both the feature-level tags and the ``Feature:`` keyword,
    mirroring the placement of the built-in ``# language:`` directive.

    Any comment whose text matches :data:`_ENUM_DIRECTIVE_RE` is treated
    as an enum directive (regardless of whether ``<kind>`` and ``<key>``
    are valid identifiers \u2014 a malformed directive is a hard parse error,
    not a silently-ignored comment). Duplicate ``<kind>`` in the leading
    block is rejected.
    """
    feature_line = int((feature_ast.get("location") or {}).get("line") or 0)
    tags = feature_ast.get("tags") or []
    first_tag_line = (
        int((tags[0].get("location") or {}).get("line") or feature_line)
        if tags
        else feature_line
    )
    cutoff = min(feature_line, first_tag_line) if feature_line else 0

    enums: dict[str, str] = {}
    for comment in comments:
        loc = comment.get("location") or {}
        line = int(loc.get("line") or 0)
        column = int(loc.get("column") or 0)
        if cutoff and line >= cutoff:
            continue
        text = (comment.get("text") or "").strip()
        match = _ENUM_DIRECTIVE_RE.match(text)
        if not match:
            continue
        kind, key = match.group(1), match.group(2)
        if not ENUM_IDENTIFIER_RE.fullmatch(kind):
            raise GherkinParseError(
                line=line,
                column=column,
                message=(
                    f"Invalid enum directive: kind {kind!r} must match "
                    f"{ENUM_IDENTIFIER_RE.pattern}."
                ),
            )
        if not ENUM_KEY_RE.fullmatch(key):
            raise GherkinParseError(
                line=line,
                column=column,
                message=(
                    f"Invalid enum directive: key {key!r} for kind "
                    f"{kind!r} must match {ENUM_KEY_RE.pattern}."
                ),
            )
        if kind in enums:
            raise GherkinParseError(
                line=line,
                column=column,
                message=(
                    f"Duplicate enum directive for kind {kind!r}."
                ),
            )
        enums[kind] = key
    return enums


def _wrap_parser_exception(
    exc: CompositeParserException, *, line_offset: int = 0
) -> GherkinParseError:
    """Convert a ``CompositeParserException`` into our domain error type.

    Surfaces the *first* inner error's line/column so the UI can highlight
    a single position. The remaining errors are summarized in the message.

    ``line_offset`` is subtracted from the reported line so that positions
    stay correct for callers that synthesized a leading ``Feature:`` line
    (see :func:`split_feature_source`); the reported line is clamped to a
    minimum of 1.
    """
    inner_errors = getattr(exc, "errors", None) or []
    if inner_errors:
        first = inner_errors[0]
        loc = getattr(first, "location", None) or {}
        line = int(loc.get("line", 0) or 0)
        column = int(loc.get("column", 0) or 0)
        if line_offset and line:
            line = max(1, line - line_offset)
        message = getattr(first, "message", None) or str(first)
        if len(inner_errors) > 1:
            message = f"{message} (and {len(inner_errors) - 1} more parse error(s))"
        return GherkinParseError(line=line, column=column, message=message)
    return GherkinParseError(line=0, column=0, message=str(exc))


def _collect_children(
    children: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Walk the feature's children, returning (background, [scenario_ast]).

    Collects **every** scenario child in document order; the caller decides
    the single-vs-multi policy (``parse_feature`` rejects ``len > 1``,
    :func:`split_feature_source` keeps them all). Raises
    :class:`GherkinParseError` if a ``rule`` child is encountered.
    """
    background_ast: dict[str, Any] | None = None
    scenario_asts: list[dict[str, Any]] = []

    for child in children:
        if "rule" in child:
            loc = (child["rule"] or {}).get("location") or {}
            raise GherkinParseError(
                line=int(loc.get("line", 0) or 0),
                column=int(loc.get("column", 0) or 0),
                message="'Rule:' blocks are not supported (one scenario per file).",
            )
        if "background" in child:
            # If multiple Backgrounds were declared (unusual), the last wins;
            # gherkin-official already raises on this so we should not see it,
            # but guard defensively.
            background_ast = child["background"]
        elif "scenario" in child:
            scenario_asts.append(child["scenario"])

    return background_ast, scenario_asts


def _strip_at(tag: dict[str, Any]) -> str:
    """Return the tag value without its leading ``@``."""
    name = tag.get("name") or ""
    return name[1:] if name.startswith("@") else name


def _assemble_description(name: str, body: str) -> str:
    """Build ``Feature.description`` per PLAN.md \u00a75.1.

    Concatenates the inline name and the optional body block with a single
    newline, then decodes any literal two-character ``\\n`` back into a
    real newline (round-trip with files this tool serialized previously).
    """
    raw = name if not body else f"{name}\n{body}"
    return raw.replace("\\n", "\n")


def _extract_steps(steps_ast: list[dict[str, Any]] | None) -> list[Step]:
    """Build a list of :class:`Step`, silently dropping non-canonical keywords."""
    if not steps_ast:
        return []
    result: list[Step] = []
    for s in steps_ast:
        kw = (s.get("keyword") or "").strip()
        if kw not in CANONICAL_KEYWORDS:
            # Non-English keyword, '*' bullet, or anything unrecognized.
            continue
        result.append(
            Step(
                keyword=kw,
                text=s.get("text") or "",
                data_table=_extract_data_table(s.get("dataTable")),
            )
        )
    return result


def _extract_data_table(
    dt_ast: dict[str, Any] | None,
) -> list[list[str]] | None:
    if not dt_ast:
        return None
    rows = dt_ast.get("rows") or []
    if not rows:
        return None
    return [
        [(cell.get("value") or "") for cell in (row.get("cells") or [])]
        for row in rows
    ]


def _build_scenario(scen_ast: dict[str, Any]) -> Scenario:
    keyword = (scen_ast.get("keyword") or "").strip()
    examples_ast = scen_ast.get("examples") or []

    # Detect outline first by keyword (most reliable: "Scenario Outline" or
    # the "Scenarios" alias); fall back to "has examples" for forgiving input.
    is_outline = keyword in ("Scenario Outline", "Scenarios") or bool(examples_ast)

    examples: list[ExamplesTable] = (
        [_build_examples(ex) for ex in examples_ast] if is_outline else []
    )

    return Scenario(
        kind="outline" if is_outline else "scenario",
        name=scen_ast.get("name") or "",
        tags=[_strip_at(t) for t in (scen_ast.get("tags") or [])],
        steps=_extract_steps(scen_ast.get("steps")),
        examples=examples,
    )


def _build_examples(ex: dict[str, Any]) -> ExamplesTable:
    header_cells = (ex.get("tableHeader") or {}).get("cells") or []
    header = [(c.get("value") or "") for c in header_cells]
    rows: list[list[str]] = [
        [(c.get("value") or "") for c in (row.get("cells") or [])]
        for row in (ex.get("tableBody") or [])
    ]
    return ExamplesTable(
        tags=[_strip_at(t) for t in (ex.get("tags") or [])],
        name=ex.get("name") or "",
        header=header,
        rows=rows,
    )


# ---------------------------------------------------------------------------
# Serializer (Do step 4)
# ---------------------------------------------------------------------------


def serialize_feature(feature: Feature) -> str:
    """Render a :class:`Feature` as canonical ``.feature`` source text.

    Behavior per PLAN.md §5.2:

    - Calls :func:`~app.models.validate_feature` first; raises
      :class:`~app.errors.ValidationError` on any invariant violation.
    - Tags are de-duplicated within each tag list (order preserved, first
      occurrence kept) and prepended with ``@``.
    - ``Feature.description`` has real newlines encoded as the literal
      two-character sequence ``\\n`` so the ``Feature:`` line is single-line.
    - Step text is trimmed of leading/trailing whitespace.
    - Table cells are trimmed, then escaped (``\\`` first, then ``|``).
      Empty cells become a single space. All cells in a table are padded
      with trailing spaces so columns align to the widest cell.
    - Output is UTF-8 / LF and ends with exactly one trailing newline.
    """

    validate_feature(feature)

    lines: list[str] = []

    # --- Enum directives --------------------------------------------------
    # One ``# enum.<kind>: <key>`` line per non-empty entry, alphabetical by
    # kind for canonical formatting. Empty values are skipped so files that
    # never set a given kind round-trip byte-identically even when the
    # project's ``enums.yaml`` later adds that kind.
    for kind in sorted(feature.enums):
        key = feature.enums[kind]
        if key:
            lines.append(f"# enum.{kind}: {key}")

    # --- Feature header ---------------------------------------------------
    feat_tags = _dedupe(feature.tags)
    if feat_tags:
        lines.append(" ".join(f"@{t}" for t in feat_tags))
    lines.append(f"Feature: {_encode_description(feature.description)}")
    lines.append("")

    # --- Optional Background ---------------------------------------------
    if feature.background.steps:
        lines.append("  Background:")
        _emit_steps(lines, feature.background.steps, step_indent=4)
        lines.append("")

    # --- Scenario / Scenario Outline -------------------------------------
    scenario = feature.scenario
    sc_tags = _dedupe(scenario.tags)
    if sc_tags:
        lines.append("  " + " ".join(f"@{t}" for t in sc_tags))

    keyword_word = "Scenario Outline" if scenario.kind == "outline" else "Scenario"
    header_line = f"  {keyword_word}:"
    if scenario.name:
        header_line += f" {scenario.name}"
    lines.append(header_line)

    _emit_steps(lines, scenario.steps, step_indent=4)

    if scenario.kind == "outline":
        for examples in scenario.examples:
            _emit_examples(lines, examples)

    return "\n".join(lines) + "\n"


# --- Serializer helpers ----------------------------------------------------


def _dedupe(items: list[str]) -> list[str]:
    """Return ``items`` with duplicates removed, preserving first occurrence."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _encode_description(description: str) -> str:
    """Encode real newlines as the literal two-character sequence ``\\n``."""
    return description.replace("\n", "\\n")


def _emit_steps(lines: list[str], steps: list[Step], *, step_indent: int) -> None:
    """Append step lines (and any data tables) to ``lines``."""
    pad = " " * step_indent
    for step in steps:
        lines.append(f"{pad}{step.keyword} {step.text.strip()}")
        if step.data_table:
            lines.extend(_render_table(step.data_table, indent=step_indent + 2))


def _emit_examples(lines: list[str], examples: ExamplesTable) -> None:
    """Append an Examples block (tags, header, header row, body rows) to ``lines``."""
    ex_tags = _dedupe(examples.tags)
    if ex_tags:
        lines.append("    " + " ".join(f"@{t}" for t in ex_tags))
    header_line = "    Examples:"
    if examples.name:
        header_line += f" {examples.name}"
    lines.append(header_line)
    table_rows: list[list[str]] = [examples.header, *examples.rows]
    lines.extend(_render_table(table_rows, indent=6))


def _render_table(rows: list[list[str]], *, indent: int) -> list[str]:
    """Render a rectangular table as pipe-separated, column-aligned lines.

    All cells are processed by :func:`_process_cell` (trim → escape →
    empty-as-single-space) before being padded to the widest cell in each
    column.
    """
    if not rows:
        return []

    processed: list[list[str]] = [
        [_process_cell(cell) for cell in row] for row in rows
    ]
    width = len(processed[0])
    col_widths = [0] * width
    for row in processed:
        for i in range(width):
            if i < len(row):
                col_widths[i] = max(col_widths[i], len(row[i]))

    pad = " " * indent
    out: list[str] = []
    for row in processed:
        cells = [row[i].ljust(col_widths[i]) for i in range(width)]
        out.append(f"{pad}| " + " | ".join(cells) + " |")
    return out


def _process_cell(value: str) -> str:
    """Trim, escape backslashes then pipes; empty cells become a single space."""
    trimmed = value.strip()
    if not trimmed:
        return " "
    # Order matters: escape backslashes first so we do not double-escape the
    # backslash we are about to introduce for the ``|`` escape.
    return trimmed.replace("\\", "\\\\").replace("|", "\\|")
