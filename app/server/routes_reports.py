"""Quality-report routes (typed area under ``<project>/report/``).

See specs/features/12-feature-quality-report-NEW.md. Reports persist the
definition only; results recompute live on every read via
`reporting.compute_report`. PATCH preserves the immutable
`type` / `created_at` (mirroring the run editor's created_at handling).
"""

from __future__ import annotations

from flask import jsonify

from ..errors import ValidationError
from ..models import Report
from ._shared import (
    api,
    _require_json_object,
    _require_non_empty_string,
    _storage,
)


@api.post("/reports/<project>")
def post_report(project: str):
    body = _require_json_object()
    file_name = _require_non_empty_string(body.get("file_name"), "file_name")
    report = Report.from_dict(body)
    _storage().create_report(project, file_name, report)
    return jsonify({"ok": True}), 201


@api.get("/reports/<project>")
def get_report_list(project: str):
    return jsonify({"reports": _storage().list_reports(project)})


@api.get("/reports/<project>/<file_name>")
def get_report(project: str, file_name: str):
    return jsonify(_storage().read_report(project, file_name).to_dict())


@api.patch("/reports/<project>/<file_name>")
def patch_report(project: str, file_name: str):
    """Whole-doc update. ``type`` and ``created_at`` are immutable.

    The existing report is loaded first (404 if missing). An incoming
    body that changes ``type`` or a non-empty ``created_at`` that differs
    is rejected with 422; otherwise the server-stamped ``created_at`` is
    preserved and the rest of the document is re-validated + cross-checked
    by :meth:`Storage.write_report`.
    """
    body = _require_json_object()
    s = _storage()
    existing = s.read_report(project, file_name)
    incoming = Report.from_dict(body)
    if incoming.type != existing.type:
        raise ValidationError(
            field="type",
            message=(
                f"Report type is immutable; cannot change "
                f"{existing.type!r} to {incoming.type!r}."
            ),
        )
    if incoming.created_at and incoming.created_at != existing.created_at:
        raise ValidationError(
            field="created_at", message="created_at is immutable."
        )
    incoming.created_at = existing.created_at
    s.write_report(project, file_name, incoming)
    return jsonify({"ok": True})


@api.delete("/reports/<project>/<file_name>")
def delete_report(project: str, file_name: str):
    _storage().delete_report(project, file_name)
    return "", 204
