"""HTTP API + UI routes (Flask blueprints), package split of the former
``server.py``.

The two blueprints (:data:`api`, :data:`ui`) live in :mod:`._shared`; the
route handlers are decentralised into per-area ``routes_*`` modules and the
blueprint-wide error handlers into :mod:`.errors`. Importing this package
imports every route module **for its registration side effects** — if a
module were omitted here its routes would silently disappear (R3), so the
import block below is load-bearing.

All routes return JSON unless documented otherwise and follow the uniform
error envelope from PLAN.md §16.9::

    { "error": { "code": "<code>", "message": "...", "details": {...?} } }

The public surface is preserved verbatim: ``from app.server import api``,
``ui``, and ``_folder_crumbs`` all resolve as before.
"""

from __future__ import annotations

from ._shared import api, ui, _folder_crumbs

# Side-effect imports: each module attaches its handlers to `api` / `ui`.
# Do NOT remove — dropping one silently unregisters that area's routes.
from . import (  # noqa: F401  (imported for registration side effects)
    routes_tree,
    routes_folders,
    routes_files,
    routes_runs,
    routes_reports,
    routes_search,
    routes_enums,
    routes_ui,
    errors,
)

__all__ = ["api", "ui", "_folder_crumbs"]
