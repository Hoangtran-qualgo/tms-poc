"""Domain dataclasses for TMS (package split of the former ``models.py``).

This package decentralises the old single ``models.py`` into per-domain
modules (``_feature``, ``_run``, ``_report``) over a shared ``_common``
leaf. The public surface is preserved verbatim: every existing import
site continues to use ``from app.models import <name>``.

This package is pure (no FS, no HTTP). The serializer in ``gherkin_io``
calls :func:`validate_feature` before writing; ``storage`` calls
:func:`validate_run` / :func:`validate_report`.
"""

from __future__ import annotations

from ._common import (
    CANONICAL_KEYWORDS,
    ENUM_IDENTIFIER_RE,
    ENUM_KEY_RE,
    FOLDER_TYPES,
    REPORT_TYPES,
    RUN_RESULTS,
    RUN_SET_TYPES,
    SCENARIO_KINDS,
)
from ._feature import (
    Background,
    ExamplesTable,
    Feature,
    Scenario,
    Step,
    _is_valid_tag,
    validate_feature,
)
from ._report import Report, validate_report
from ._run import RunResult, TestRun, validate_run

__all__ = [
    "Step",
    "ExamplesTable",
    "Scenario",
    "Background",
    "Feature",
    "RunResult",
    "TestRun",
    "Report",
    "CANONICAL_KEYWORDS",
    "SCENARIO_KINDS",
    "RUN_RESULTS",
    "ENUM_IDENTIFIER_RE",
    "ENUM_KEY_RE",
    "RUN_SET_TYPES",
    "FOLDER_TYPES",
    "REPORT_TYPES",
    "validate_feature",
    "validate_run",
    "validate_report",
]
