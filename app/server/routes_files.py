"""File CRUD routes (``.feature`` files)."""

from __future__ import annotations

from flask import Response, jsonify, request

from ..errors import ImportValidationError
from ..gherkin_io import split_feature_source, source_has_enum_directives
from ..models import Feature
from ..storage import MAX_FOLDER_DEPTH
from ._shared import (
    api,
    _error,
    _is_feature_path,
    _parent_to_segments,
    _require_json_object,
    _require_list_of_str,
    _require_non_empty_string,
    _storage,
)

#: Maximum size (bytes) of an imported ``.feature`` source (IM-F). Enforced
#: on both the preview and commit endpoints, measured on the UTF-8 payload.
_MAX_IMPORT_BYTES = 3 * 1024 * 1024


def _require_import_source(body: dict) -> str:
    """Return the ``source`` text from ``body``, enforcing the 3 MB cap."""
    source = body.get("source", "")
    if not isinstance(source, str):
        raise ValueError("Body field 'source' must be a string.")
    if len(source.encode("utf-8")) > _MAX_IMPORT_BYTES:
        raise ValueError(
            f"Imported file exceeds the {_MAX_IMPORT_BYTES // (1024 * 1024)} "
            f"MB limit."
        )
    return source


@api.post("/files")
def post_file():
    body = _require_json_object()
    file_name = _require_non_empty_string(body.get("file_name"), "file_name")
    # tech-07 (SN-1 = Option A): scenario_name is the case identity and is
    # REQUIRED at the API, matching the create modal's client-side gate
    # (tech-04 RG1) and the import path's server-side enforcement
    # (import_feature_cases). The model stays permissive (V5) by design, so
    # this is enforced here at the entry point. SN-3: whitespace-only counts
    # as empty (mirrors import's .strip() rule).
    scenario_name = _require_non_empty_string(
        body.get("scenario_name"), "scenario_name"
    )
    if not scenario_name.strip():
        raise ValueError("Body field 'scenario_name' must be a non-empty string.")
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


@api.post("/files/import/preview")
def post_import_preview():
    """Dry-run: split an uploaded ``.feature`` source into per-scenario metadata.

    Body ``{source}`` (text, no multipart). Returns the shared feature
    ``description`` / ``tags``, an ``enums_present`` flag (so the UI can warn
    that enum directives will be dropped), and one entry per scenario
    ``{scenario_name, step_count, scenario_tags}`` in document order. Performs
    no writes. A parse failure propagates as ``parse_error`` (line/col); a
    source larger than 3 MB is rejected as ``bad_request``.
    """
    body = _require_json_object()
    source = _require_import_source(body)
    features = split_feature_source(source)  # GherkinParseError on bad input
    scenarios = [
        {
            "scenario_name": f.scenario.name,
            "step_count": len(f.scenario.steps),
            "scenario_tags": list(f.scenario.tags),
        }
        for f in features
    ]
    return jsonify(
        {
            "description": features[0].description if features else "",
            "tags": list(features[0].tags) if features else [],
            "enums_present": source_has_enum_directives(source),
            "scenarios": scenarios,
        }
    )


@api.post("/files/import")
def post_import():
    """Commit an import: re-split server-side and write one file per scenario.

    Body ``{parent, source, names, project?}`` (text, no multipart). ``parent``
    is the destination folder path; ``names[i]`` is the user-supplied file name
    for scenario ``i`` (document order). ``project`` is optional and, when
    present, must equal the first segment of ``parent``. Enforces the 3 MB cap,
    requires ``len(names) == len(scenarios)``, and delegates the all-or-nothing
    pre-flight + write to :meth:`Storage.import_feature_cases`.
    """
    body = _require_json_object()
    source = _require_import_source(body)

    parent_segments = _parent_to_segments(body.get("parent", ""))
    if not (2 <= len(parent_segments) <= MAX_FOLDER_DEPTH):
        raise ValueError(
            "Body field 'parent' must reference a module or sub-folder "
            f"(2..{MAX_FOLDER_DEPTH} segments); got "
            f"{len(parent_segments)} segment(s)."
        )

    project = body.get("project")
    if project is not None:
        if not isinstance(project, str):
            raise ValueError("Body field 'project' must be a string.")
        if project and project != parent_segments[0]:
            raise ValueError(
                f"Body field 'project' ({project!r}) must match the first "
                f"segment of 'parent' ({parent_segments[0]!r})."
            )

    names = _require_list_of_str(body.get("names"), "names")
    features = split_feature_source(source)  # GherkinParseError on bad input
    if not features:
        raise ImportValidationError(reasons=["No scenarios to import."])
    if len(names) != len(features):
        raise ValueError(
            f"Expected {len(features)} file name(s) to match the "
            f"{len(features)} scenario(s); got {len(names)}."
        )

    created = _storage().import_feature_cases(
        parent_segments, list(zip(names, features))
    )
    return jsonify({"ok": True, "created": created}), 201


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
