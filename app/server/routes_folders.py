"""Folder listing + mutation routes."""

from __future__ import annotations

from flask import Response, jsonify

from ._shared import (
    api,
    _error,
    _parent_to_segments,
    _require_json_object,
    _require_non_empty_string,
    _storage,
)


# ---------------------------------------------------------------------------
# Folder listings
# ---------------------------------------------------------------------------


@api.get("/folders/contents")
def get_root_contents() -> Response:
    return jsonify(_storage().list_folder(""))


@api.get("/folders/<path:p>/contents")
def get_folder_contents(p: str):
    try:
        return jsonify(_storage().list_folder(p))
    except ValueError as e:
        return _error("bad_request", str(e), 400)
    except FileNotFoundError as e:
        return _error("not_found", str(e), 404)


# ---------------------------------------------------------------------------
# Folder mutations
# ---------------------------------------------------------------------------


@api.post("/folders")
def post_folder():
    body = _require_json_object()
    name = _require_non_empty_string(body.get("name"), "name")
    segments = _parent_to_segments(body.get("parent", "")) + [name]
    _storage().create_folder(segments)
    return jsonify({"ok": True}), 201


@api.patch("/folders/<path:p>")
def patch_folder(p: str):
    body = _require_json_object()
    name = _require_non_empty_string(body.get("name"), "name")
    _storage().rename_folder(p, name)
    return jsonify({"ok": True})


@api.delete("/folders/<path:p>")
def delete_folder(p: str):
    _storage().delete_folder(p)
    # PLAN G5: 204 No Content on successful delete (idempotent).
    return "", 204
