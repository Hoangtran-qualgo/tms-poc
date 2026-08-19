"""File CRUD routes (``.feature`` files)."""

from __future__ import annotations

from flask import Response, jsonify, request

from ..errors import GherkinParseError, ImportValidationError
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
#: on one-file legacy requests and on the cumulative source text of a batch,
#: measured on the UTF-8 payload.
_MAX_IMPORT_BYTES = 3 * 1024 * 1024
#: Maximum number of selected source files in one batch (feature-17).
_MAX_IMPORT_FILES = 20


def _require_import_source(body: dict) -> str:
    """Return legacy one-file ``source`` text, enforcing the 3 MB cap."""
    source = body.get("source", "")
    if not isinstance(source, str):
        raise ValueError("Body field 'source' must be a string.")
    if len(source.encode("utf-8")) > _MAX_IMPORT_BYTES:
        raise ValueError(
            f"Imported file exceeds the {_MAX_IMPORT_BYTES // (1024 * 1024)} "
            f"MB limit."
        )
    return source


def _require_import_sources(body: dict) -> list[dict[str, str]]:
    """Return validated multi-file ``sources`` entries with batch limits.

    Each entry is ``{name, source}``: ``name`` is display/error context only;
    source-array order remains the association key. File-type and Gherkin
    errors are deliberately collected by :func:`_split_import_sources` so the
    preview can show every bad source together.
    """
    raw_sources = body.get("sources")
    if not isinstance(raw_sources, list):
        raise ValueError("Body field 'sources' must be a list.")
    if not raw_sources:
        raise ValueError("Body field 'sources' must contain at least one file.")
    if len(raw_sources) > _MAX_IMPORT_FILES:
        raise ValueError(
            f"Import batch exceeds the {_MAX_IMPORT_FILES}-file limit."
        )

    sources: list[dict[str, str]] = []
    total_bytes = 0
    for index, raw_source in enumerate(raw_sources):
        field = f"sources[{index}]"
        if not isinstance(raw_source, dict):
            raise ValueError(f"Body field {field!r} must be an object.")
        name = raw_source.get("name")
        source = raw_source.get("source")
        if not isinstance(name, str) or not name:
            raise ValueError(
                f"Body field {field + '.name'!r} must be a non-empty string."
            )
        if not isinstance(source, str):
            raise ValueError(
                f"Body field {field + '.source'!r} must be a string."
            )
        total_bytes += len(source.encode("utf-8"))
        sources.append({"name": name, "source": source})

    if total_bytes > _MAX_IMPORT_BYTES:
        raise ValueError(
            f"Import batch exceeds the {_MAX_IMPORT_BYTES // (1024 * 1024)} "
            "MB total limit."
        )
    return sources


def _split_import_sources(
    sources: list[dict[str, str]],
) -> tuple[
    list[tuple[int, str, Feature]], list[dict[str, object]], list[dict[str, object]]
]:
    """Split every batch source, collecting source-specific blocking errors."""
    cases: list[tuple[int, str, Feature]] = []
    errors: list[dict[str, object]] = []
    enum_sources: list[dict[str, object]] = []

    for index, item in enumerate(sources):
        source_name = item["name"]
        source = item["source"]
        base = {"source_index": index, "source_name": source_name}
        if not source_name.lower().endswith(".feature"):
            errors.append(
                {
                    **base,
                    "code": "invalid_file_type",
                    "message": "Source file must end with .feature.",
                }
            )
            continue
        try:
            features = split_feature_source(source)
        except GherkinParseError as exc:
            errors.append(
                {
                    **base,
                    "code": "parse_error",
                    "message": exc.message,
                    "line": exc.line,
                    "column": exc.column,
                }
            )
            continue
        if not features:
            errors.append(
                {
                    **base,
                    "code": "no_scenarios",
                    "message": "No scenarios found to import.",
                }
            )
            continue
        if source_has_enum_directives(source):
            enum_sources.append(base)
        cases.extend((index, source_name, feature) for feature in features)

    return cases, errors, enum_sources


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

    Legacy body ``{source}`` preserves its shipped response shape. Batch body
    ``{sources: [{name, source}, ...]}`` returns flattened scenario metadata
    with source context plus every source-specific type/parse/content error.
    Both variants perform no writes.
    """
    body = _require_json_object()
    if "sources" not in body:
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

    cases, errors, enum_sources = _split_import_sources(
        _require_import_sources(body)
    )
    scenarios = [
        {
            "source_index": index,
            "source_name": source_name,
            "scenario_name": feature.scenario.name,
            "step_count": len(feature.scenario.steps),
            "feature_tags": list(feature.tags),
            "scenario_tags": list(feature.scenario.tags),
        }
        for index, source_name, feature in cases
    ]
    return jsonify(
        {
            "errors": errors,
            "enum_sources": enum_sources,
            "enums_present": bool(enum_sources),
            "scenarios": scenarios,
        }
    )


@api.post("/files/import")
def post_import():
    """Commit an import: re-split server-side and write one file per scenario.

    Legacy body ``{parent, source, names, project?}`` remains supported. Batch
    body replaces ``source`` with ordered ``sources: [{name, source}, ...]``;
    ``names[i]`` maps to flattened source/scenario order. Both delegate one
    all-or-nothing pre-flight + write to :meth:`Storage.import_feature_cases`.
    """
    body = _require_json_object()

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
    if "sources" not in body:
        source = _require_import_source(body)
        features = split_feature_source(source)  # GherkinParseError on bad input
    else:
        cases, errors, _ = _split_import_sources(_require_import_sources(body))
        if errors:
            raise ImportValidationError(
                reasons=[
                    f"{error['source_name']}: {error['message']}"
                    for error in errors
                ]
            )
        features = [feature for _, _, feature in cases]
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
