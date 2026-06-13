"""File CRUD routes (``.feature`` files)."""

from __future__ import annotations

from flask import Response, jsonify, request

from ..models import Feature
from ..storage import MAX_FOLDER_DEPTH
from ._shared import (
    api,
    _error,
    _is_feature_path,
    _parent_to_segments,
    _require_json_object,
    _require_non_empty_string,
    _storage,
)


@api.post("/files")
def post_file():
    body = _require_json_object()
    file_name = _require_non_empty_string(body.get("file_name"), "file_name")
    # tech-04 (Option B): scenario_name is the case identity but stays
    # OPTIONAL at the API (model permits an empty scenario name, V5; the
    # create modal enforces "required" client-side). Hard API enforcement
    # is tracked as a separate Must-have ("Require scenario_name at API").
    scenario_name = body.get("scenario_name", "")
    if not isinstance(scenario_name, str):
        raise ValueError("Body field 'scenario_name' must be a string.")
    description = body.get("description", "")
    if not isinstance(description, str):
        raise ValueError("Body field 'description' must be a string.")

    parent_segments = _parent_to_segments(body.get("parent", ""))
    # `.feature` files live inside a module (depth 2) or any sub-folder
    # below it (depth 3..MAX_FOLDER_DEPTH). Files directly under a
    # project (depth 1) or at the data root (depth 0) are not allowed
    # by current product rules; revise this guard if that ever changes.
    if not (2 <= len(parent_segments) <= MAX_FOLDER_DEPTH):
        raise ValueError(
            "Body field 'parent' must reference a module or sub-folder "
            f"(2..{MAX_FOLDER_DEPTH} segments); got "
            f"{len(parent_segments)} segment(s)."
        )

    _storage().create_file(
        parent_segments + [file_name], description, scenario_name=scenario_name
    )
    return jsonify({"ok": True}), 201


@api.get("/files/<path:p>")
def get_file(p: str):
    if not _is_feature_path(p):
        return _error(
            "unsupported_type",
            "File type not supported",
            415,
            details={"path": p},
        )
    feature = _storage().read_feature(p)
    return jsonify(feature.to_dict())


@api.patch("/files/<path:p>")
def patch_file(p: str):
    body = _require_json_object()
    feature = Feature.from_dict(body)
    _storage().write_feature(p, feature)
    return jsonify({"ok": True})


@api.delete("/files/<path:p>")
def delete_file(p: str):
    _storage().delete_file(p)
    # PLAN G5: 204 No Content on successful delete (idempotent).
    return "", 204


@api.patch("/files/<path:p>/rename")
def rename_file(p: str):
    body = _require_json_object()
    file_name = _require_non_empty_string(body.get("file_name"), "file_name")
    _storage().rename_file(p, file_name)
    return jsonify({"ok": True})


@api.patch("/files/<path:p>/move")
def move_file(p: str):
    body = _require_json_object()
    if "parent" not in body or not isinstance(body["parent"], str):
        raise ValueError("Body field 'parent' must be a string.")
    dest_parent_segments = _parent_to_segments(body["parent"])
    _storage().move_file(p, dest_parent_segments)
    return jsonify({"ok": True})


@api.post("/files/<path:p>/duplicate")
def duplicate_file(p: str):
    body = _require_json_object()
    file_name = _require_non_empty_string(body.get("file_name"), "file_name")
    _storage().duplicate_file(p, file_name)
    return jsonify({"ok": True}), 201


@api.get("/files/<path:p>/raw")
def get_file_raw(p: str):
    if not _is_feature_path(p):
        return _error(
            "unsupported_type",
            "File type not supported",
            415,
            details={"path": p},
        )
    text = _storage().read_raw(p)
    return Response(text, mimetype="text/plain; charset=utf-8")


@api.put("/files/<path:p>/raw")
def put_file_raw(p: str):
    if not _is_feature_path(p):
        return _error(
            "unsupported_type",
            "File type not supported",
            415,
            details={"path": p},
        )
    text = request.get_data(as_text=True)
    _storage().write_raw(p, text)
    return jsonify({"ok": True})
