"""Shared constants and helpers for the models package.

Pure (no FS, no HTTP). Imported by the domain modules (``_feature``,
``_run``, ``_report``); it never imports them back, so the package's
internal dependency graph stays acyclic.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Canonical English step keywords accepted by the parser and serializer.
CANONICAL_KEYWORDS: tuple[str, ...] = ("Given", "When", "Then", "And", "But")

#: Valid values for :attr:`Scenario.kind`.
SCENARIO_KINDS: tuple[str, ...] = ("scenario", "outline")

#: Identifier regex for project-level enum kind names and keys per
#: ``specs/features/11-feature-testcase-component-NEW.md`` (Q1 / Q5).
#: Lowercase ``snake_case`` is conventional; this regex is the wire-level
#: validator (letters, digits, underscores; must start with a letter or
#: underscore). The ``# enum.<kind>: <key>`` on-disk directive parser in
#: ``gherkin_io`` and the project-level ``enums.yaml`` schema validator in
#: ``storage`` both reuse this constant.
ENUM_IDENTIFIER_RE: re.Pattern[str] = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

#: Valid values for :attr:`RunResult.result`. Order is meaningful only to
#: the UI (rendered left-to-right in the result `<select>`); on disk any
#: of these strings is accepted. Default for a newly-added case is
#: ``"PENDING"``.
RUN_RESULTS: tuple[str, ...] = (
    "PENDING",
    "EXECUTING",
    "PASSED",
    "FAILED",
    "SKIPPED",
)

#: Report ``type`` discriminators per
#: ``specs/features/12-feature-quality-report-NEW.md`` (D2/D3). Run-set
#: types draw from a list of run files; folder types from a folder scope.
RUN_SET_TYPES: frozenset[str] = frozenset(
    {"enum_ranking", "tag_ranking", "case_trend"}
)
FOLDER_TYPES: frozenset[str] = frozenset({"tag_inventory"})
REPORT_TYPES: frozenset[str] = RUN_SET_TYPES | FOLDER_TYPES


# ---------------------------------------------------------------------------
# Shared validation helper
# ---------------------------------------------------------------------------


def _is_single_line(s: str) -> bool:
    """True if ``s`` contains no newline-like character (LF, CR)."""
    return "\n" not in s and "\r" not in s
