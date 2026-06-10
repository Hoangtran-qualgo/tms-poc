"""Shared blueprints + request/response helpers for the server package.

The two blueprints (:data:`api`, :data:`ui`) are defined here so every
``routes_*`` module can attach handlers to them without importing the
package ``__init__`` (which would risk a partial-import cycle). All the
small cross-route helpers live here too; each route module imports only
what it needs from this module.

Pure plumbing — no route handlers and no error handlers live here.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request

from ..storage import Storage
from ..watcher import EventBus

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


def _require_list_of_str(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(x, str) for x in value
    ):
        raise ValueError(
            f"Body field {field!r} must be a list of strings."
        )
    return list(value)


def _require_optional_str(value: Any, field: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"Body field {field!r} must be a string if present.")
    return value


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
