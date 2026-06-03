"""HTTP API routes (Flask blueprint).

Do step 10 adds the tree, events (SSE), folder, and search routes. Step 11
adds the file-CRUD routes. All routes return JSON unless documented
otherwise and follow the uniform error envelope from PLAN.md §16.9::

    { "error": { "code": "<code>", "message": "...", "details": {...?} } }

Exception → HTTP code mapping (PLAN.md §8.5):

- :class:`ValueError`                 → ``400 bad_request``
- :class:`FileNotFoundError`          → ``404 not_found``
- :class:`~app.errors.NameConflictError` → ``409 name_conflict``
- :class:`~app.errors.ValidationError`   → ``422 validation_error``
- :class:`~app.errors.GherkinParseError` → ``422 parse_error``
- anything else                        → ``500 internal_error``
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, current_app, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from .errors import GherkinParseError, NameConflictError, ValidationError
from .models import Feature
from .sse import sse_response
from .storage import MAX_FOLDER_DEPTH, Storage
from .watcher import EventBus

api = Blueprint("api", __name__, url_prefix="/api")

#: UI blueprint owns the HTML partials swapped into the page by HTMX.
#: JSON / REST lives on :data:`api`; the two are kept separate so the
#: JSON API can evolve independently of the rendered HTML.
ui = Blueprint("ui", __name__, url_prefix="/ui")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _storage() -> Storage:
    return current_app.extensions["storage"]


def _bus() -> EventBus:
    return current_app.extensions["bus"]


def _error(
    code: str,
    message: str,
    http_status: int,
    details: dict[str, Any] | None = None,
) -> tuple[Response, int]:
    """Build a Flask response with the uniform error envelope."""
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), http_status


def _require_json_object() -> dict[str, Any]:
    """Return the JSON body as a dict, raising :class:`ValueError` if not one."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValueError("Request body must be a JSON object.")
    return body


def _parent_to_segments(parent: str) -> list[str]:
    """Split a 'parent' path string ('' for root) into segments."""
    if not isinstance(parent, str):
        raise ValueError("Body field 'parent' must be a string.")
    return [p for p in parent.split("/") if p]


def _require_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Body field {field!r} must be a non-empty string.")
    return value


def _leaf_name(p: str) -> str:
    """Return the last path segment of a logical-path string."""
    return p.rsplit("/", 1)[-1]


def _is_feature_path(p: str) -> bool:
    """Case-insensitive ``.feature`` extension check on the leaf segment."""
    return _leaf_name(p).lower().endswith(".feature")


# ---------------------------------------------------------------------------
# Tree & events
# ---------------------------------------------------------------------------


@api.get("/tree")
def get_tree() -> Response:
    return jsonify(_storage().list_tree())


@api.get("/events")
def get_events() -> Response:
    return sse_response(_bus())


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


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


@api.post("/files")
def post_file():
    body = _require_json_object()
    file_name = _require_non_empty_string(body.get("file_name"), "file_name")
    description = body.get("description", "")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("Body field 'description' must be a non-empty string.")

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

    _storage().create_file(parent_segments + [file_name], description)
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


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@api.get("/search")
def search():
    q = request.args.get("q", "")
    scope = request.args.get("scope", "all")
    match = request.args.get("match", "text")
    case_sensitive = request.args.get("case", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    hits = _storage().search(
        q, scope=scope, match=match, case_sensitive=case_sensitive
    )
    return jsonify({"hits": hits})


# ---------------------------------------------------------------------------
# Blueprint-wide error handlers
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


@api.errorhandler(Exception)
def _handle_unexpected(e: Exception):
    # Let Werkzeug HTTPExceptions (404, 405, etc.) flow through the default
    # handlers; they already produce sensible responses.
    if isinstance(e, HTTPException):
        return e
    current_app.logger.exception("Unexpected error in API handler")
    return _error("internal_error", "An unexpected error occurred.", 500)


# ---------------------------------------------------------------------------
# UI partials (Do step 12+)
# ---------------------------------------------------------------------------


@ui.get("/tree")
def ui_tree() -> str:
    """Render the tree pane as a fresh HTML partial.

    Called by HTMX on initial page load (server-side include) and on every
    ``sse:change`` event so the tree stays in sync with disk.
    """
    return render_template("tree.html", tree=_storage().list_tree())


@ui.get("/folder/")
@ui.get("/folder/<path:p>")
def ui_folder(p: str = ""):
    """Render the main-pane view for a folder.

    Variants per :meth:`Storage.list_folder` (see PLAN.md §9.3):

    - Empty / root path → ``folder_root.html``: project listing.
    - Depth-1 (project) → ``folder_project.html``: module table.
    - Depth-2 (module) → ``folder_module.html``: features + sub-folders.
    - Depth-3..MAX (sub-folder) → ``folder_subfolder.html``: sub-folders
      + features; the entry point for arbitrarily nested test cases (see
      IN-PROGRESS.md "Increase folder nesting depth to 10 levels").

    Beyond MAX_FOLDER_DEPTH a 400 ``bad_request`` surfaces via the
    blueprint-wide ``ValueError`` handler (raised from `list_folder`).
    """
    s = _storage()
    segments = [x for x in p.split("/") if x] if p else []

    if len(segments) == 0:
        listing = s.list_folder("")
        return render_template(
            "folder_root.html", projects=listing["projects"]
        )

    if len(segments) == 1:
        listing = s.list_folder(segments)
        return render_template(
            "folder_project.html",
            project=segments[0],
            modules=listing["modules"],
        )

    listing = s.list_folder(segments)
    folder_path = "/".join(segments)
    if len(segments) == 2:
        return render_template(
            "folder_module.html",
            project=segments[0],
            module=segments[1],
            module_path=folder_path,
            folders=listing.get("folders", []),
            features=listing["features"],
        )

    # Depth 3..MAX — generic sub-folder view. Render a breadcrumb of
    # ancestors so the user can navigate back up at any level.
    return render_template(
        "folder_subfolder.html",
        segments=segments,
        crumbs=_folder_crumbs(segments),
        folder_path=folder_path,
        folder_name=segments[-1],
        folders=listing["folders"],
        features=listing["features"],
    )


def _folder_crumbs(segments: list[str]) -> list[dict[str, str]]:
    """Build a list of ``{label, path}`` for the ancestor folders of
    ``segments`` (excluding the leaf). Used by the deep sub-folder view
    and the file editor breadcrumb so both can render N levels uniformly.
    """
    crumbs: list[dict[str, str]] = []
    for i in range(1, len(segments)):
        crumbs.append({
            "label": segments[i - 1],
            "path": "/".join(segments[:i]),
        })
    return crumbs


@ui.get("/file/<path:p>")
def ui_file(p: str):
    """Render the main-pane view for a file.

    Non-``.feature`` files render :file:`unsupported.html` per PLAN.md §9.7.
    ``.feature`` files render the structured-plus-raw editor with the parsed
    :class:`~app.models.Feature` and the raw on-disk text embedded as JSON
    for the client editor controller to bootstrap from.

    If the file is present but unparseable, the parse error propagates as a
    422 envelope via the blueprint error handler — the user is expected to
    repair the file externally or via the raw tab in a sibling file.
    """
    if not _is_feature_path(p):
        return render_template("unsupported.html", file_path=p)
    s = _storage()
    feature = s.read_feature(p)  # raises FileNotFoundError / GherkinParseError
    raw = s.read_raw(p)
    segments = p.split("/")
    file_name = segments[-1]
    # `crumbs` covers every ancestor folder of the file (project, module,
    # any sub-folders). The file editor template iterates over it to
    # render an N-segment breadcrumb, which is what enables files to live
    # at any depth from 2 (under a module) to MAX_FOLDER_DEPTH.
    crumbs = _folder_crumbs(segments[:-1] + [file_name])
    return render_template(
        "file_editor.html",
        file_path=p,
        crumbs=crumbs,
        file_name=file_name,
        feature=feature.to_dict(),
        raw=raw,
    )


@ui.get("/search")
def ui_search():
    """Render the search results main-pane partial.

    Accepts the same query params as ``/api/search`` and delegates to
    :meth:`Storage.search`. Always returns HTML; the partial is responsible
    for rendering the three UX variants documented in PLAN.md §9.6:

    - 0 hits → "No matches"
    - 1 hit  → inline ``<script>`` that auto-navigates to the file editor
    - ≥2 hits → list view with file_path + first-line description + badge
    """
    q = request.args.get("q", "").strip()
    scope = request.args.get("scope", "all")
    match = request.args.get("match", "text")
    case_sensitive = request.args.get("case", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    if not q:
        return render_template(
            "search_results.html", hits=[], query="", show_empty_state=True
        )
    hits = _storage().search(
        q, scope=scope, match=match, case_sensitive=case_sensitive
    )
    return render_template(
        "search_results.html", hits=hits, query=q, show_empty_state=False
    )


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
