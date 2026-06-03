"""Flask app factory for TMS.

Performs the startup sequence documented in PLAN.md §2:

1. Resolve and create the data root if missing.
2. Scan the data root for atomic-write orphan temp files and delete them.
3. Construct the :class:`~app.storage.Storage`, the :class:`~app.watcher.EventBus`,
   and the :class:`~app.watcher.Watcher`; start the observer.
4. Register Flask blueprints.    [populated across Do steps 10–14]

Singletons are stashed on ``app.extensions`` so routes (and tests) can fetch
them via ``current_app.extensions['storage'] / ['bus'] / ['watcher']``.
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, render_template

from . import storage as storage_module
from .server import api as api_blueprint, ui as ui_blueprint
from .storage import Storage
from .watcher import EventBus, Watcher


def create_app(data_root: str | os.PathLike[str] | None = None) -> Flask:
    """Build and return the Flask application instance.

    Parameters
    ----------
    data_root:
        Override for the data root. Defaults to ``./project`` resolved against
        the current working directory.
    """

    app = Flask(__name__)

    root = (
        Path(data_root)
        if data_root is not None
        else Path.cwd() / "project"
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)
    app.config["DATA_ROOT"] = root

    storage_module.cleanup_orphan_temp_files(root)

    storage = Storage(root)
    bus = EventBus()
    watcher = Watcher(storage, bus)
    watcher.start()

    # Flask convention: shared singletons live under app.extensions.
    if not hasattr(app, "extensions") or app.extensions is None:
        app.extensions = {}
    app.extensions["storage"] = storage
    app.extensions["bus"] = bus
    app.extensions["watcher"] = watcher

    app.register_blueprint(api_blueprint)
    app.register_blueprint(ui_blueprint)

    @app.route("/")
    def index() -> str:
        # Render the initial tree server-side so the first paint is fully
        # populated; HTMX then handles subsequent refreshes via SSE.
        return render_template(
            "base.html", tree=storage.list_tree()
        )

    return app
