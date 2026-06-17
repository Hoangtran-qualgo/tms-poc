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

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    render_template,
    request,
)

from ..models import RUN_RESULTS
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


def tree_ancestors(folder_path: str) -> list[str]:
    """Inclusive ancestor prefixes of a data-root-relative folder path.

    ``'Alpha/Mod/Sub'`` -> ``['Alpha', 'Alpha/Mod', 'Alpha/Mod/Sub']``. Used to
    seed the Directory-tree auto-expand (tech-10 10a). Typed-tree ancestors
    (test-run / reports) don't follow this prefix scheme — their folder nodes
    are ``<project>`` and ``<project>/test-run/<group>`` — so callers build
    those lists explicitly (10b).
    """
    segs = [s for s in folder_path.split("/") if s]
    return ["/".join(segs[: i + 1]) for i in range(len(segs))]


def maybe_shell(
    active_tab: str = "tree", expand_paths: list[str] | None = None
) -> str | None:
    """Content-negotiation for deep-linkable item routes (tech-10).

    A top-level (non-HTMX) GET to an item URL — cold load, refresh, direct
    link, bookmark, or a Back/Forward full reload (``historyCacheSize=0`` +
    ``refreshOnHistoryMiss``) — must return the whole ``base.html`` shell so the
    sidebar + tabs rehydrate. An ordinary HTMX request gets the bare fragment
    exactly as before.

    Returns the rendered shell (a ``str``) for a top-level GET, or ``None`` when
    the caller should render its fragment.

    ``active_tab`` selects the sidebar tab to activate on boot. ``expand_paths``
    are the ``data-path`` folder nodes of *that tab's* tree to auto-expand to
    the open item (directory ancestors for ``tree``; ``<project>`` +
    ``<project>/test-run/<group>`` for the typed tabs); emitted as
    ``window.TMS_EXPAND_PATHS``.

    Negotiation signal: the shell is returned ONLY for a genuine browser
    **navigation** (typed URL, refresh, bookmark, Back/Forward full reload),
    which browsers mark with ``Sec-Fetch-Mode: navigate``. HTMX swaps send
    ``HX-Request`` and programmatic/test clients send neither — both keep
    getting the bare fragment, so ``/ui/*`` stays a fragment endpoint for
    everything except a human navigating there.
    """
    if request.headers.get("HX-Request"):
        return None
    if request.headers.get("Sec-Fetch-Mode") != "navigate":
        return None

    # Mirror the URL the client used so the #main-pane load-trigger re-fetches
    # the same route (full_path tacks on a lone '?' when there's no query).
    url = request.full_path
    if url.endswith("?"):
        url = url[:-1]

    return render_template(
        "base.html",
        tree=_storage().list_tree(),
        run_results=list(RUN_RESULTS),
        initial_main_url=url,
        active_tab=active_tab,
        expand_paths=expand_paths or [],
    )
