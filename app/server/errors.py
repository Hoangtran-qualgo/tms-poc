"""Blueprint-wide error handlers for both the ``api`` and ``ui`` blueprints.

Exception → HTTP code mapping (PLAN.md §8.5):

- :class:`ValueError`                 → ``400 bad_request``
- :class:`FileNotFoundError`          → ``404 not_found``
- :class:`~app.errors.NameConflictError` → ``409 name_conflict``
- :class:`~app.errors.ValidationError`   → ``422 validation_error``
- :class:`~app.errors.GherkinParseError` → ``422 parse_error``
- :class:`~app.errors.RunParseError`     → ``422 run_parse_error``
- :class:`~app.errors.EnumsParseError`   → ``422 enums_parse_error``
- anything else                        → ``500 internal_error``
"""

from __future__ import annotations

from flask import current_app
from werkzeug.exceptions import HTTPException

from ..errors import (
    EnumInUseError,
    EnumsParseError,
    GherkinParseError,
    ImportValidationError,
    NameConflictError,
    ReportParseError,
    RunParseError,
    ValidationError,
)
from ._shared import api, ui, _error


# ---------------------------------------------------------------------------
# API blueprint error handlers
# ---------------------------------------------------------------------------


@api.errorhandler(ValueError)
def _handle_value_error(e: ValueError):
    return _error("bad_request", str(e), 400)


@api.errorhandler(FileNotFoundError)
def _handle_not_found(e: FileNotFoundError):
    return _error("not_found", str(e), 404)


@api.errorhandler(NameConflictError)
def _handle_conflict(e: NameConflictError):
    return _error("name_conflict", e.message, 409, details={"path": e.path})


@api.errorhandler(ValidationError)
def _handle_validation(e: ValidationError):
    return _error("validation_error", e.message, 422, details={"field": e.field})


@api.errorhandler(GherkinParseError)
def _handle_parse(e: GherkinParseError):
    return _error(
        "parse_error",
        e.message,
        422,
        details={"line": e.line, "column": e.column},
    )


@api.errorhandler(RunParseError)
def _handle_run_parse(e: RunParseError):
    return _error(
        "run_parse_error",
        e.message,
        422,
        details={"line": e.line, "column": e.column},
    )


@api.errorhandler(ReportParseError)
def _handle_report_parse(e: ReportParseError):
    return _error(
        "report_parse_error",
        e.message,
        422,
        details={"line": e.line, "column": e.column},
    )


@api.errorhandler(EnumInUseError)
def _handle_enum_in_use(e: EnumInUseError):
    return _error(
        "enum_in_use",
        e.message,
        409,
        details={
            "kind": e.kind,
            "key": e.key,
            "count": e.count,
            "sample": e.sample,
        },
    )


@api.errorhandler(ImportValidationError)
def _handle_import_validation(e: ImportValidationError):
    return _error(
        "import_validation_error",
        e.message,
        422,
        details={"reasons": e.reasons},
    )


@api.errorhandler(EnumsParseError)
def _handle_enums_parse(e: EnumsParseError):
    return _error(
        "enums_parse_error",
        e.message,
        422,
        details={"line": e.line, "column": e.column},
    )


@api.errorhandler(Exception)
def _handle_unexpected(e: Exception):
    # Let Werkzeug HTTPExceptions (404, 405, etc.) flow through the default
    # handlers; they already produce sensible responses.
    if isinstance(e, HTTPException):
        return e
    current_app.logger.exception("Unexpected error in API handler")
    return _error("internal_error", "An unexpected error occurred.", 500)


# ---------------------------------------------------------------------------
# UI blueprint error handlers
# ---------------------------------------------------------------------------


def _ui_error_html(message: str, status: int):
    """Render a small HTML error snippet suitable for direct swap into main-pane."""
    body = (
        '<div class="p-4 text-red-700 bg-red-50 border border-red-200 rounded">'
        f'{message}</div>'
    )
    return body, status


@ui.errorhandler(ValueError)
def _ui_value_error(e: ValueError):
    return _ui_error_html(str(e), 400)


@ui.errorhandler(FileNotFoundError)
def _ui_not_found(e: FileNotFoundError):
    return _ui_error_html(str(e), 404)


@ui.errorhandler(Exception)
def _ui_unexpected(e: Exception):
    if isinstance(e, HTTPException):
        return e
    current_app.logger.exception("Unexpected error in UI handler")
    return _ui_error_html("An unexpected error occurred.", 500)
