"""T10-03 — index() + base.html defaults unchanged.

`/` still renders the shell with #main-pane defaulting to /ui/folder/, the tree
tab active, empty active-path + expand-paths.
"""
import tempfile, pathlib
from app import create_app

with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    h = app.test_client().get("/").get_data(as_text=True)

    assert "<!doctype" in h.lower(), "/ must render the shell"
    assert 'hx-get="/ui/folder/"' in h, "#main-pane default load URL"
    assert 'window.TMS_ACTIVE_TAB = "tree"' in h, h[:0]
    assert 'window.TMS_ACTIVE_PATH = ""' in h
    assert "window.TMS_EXPAND_PATHS = []" in h
    assert 'data-active-tab="tree"' in h
    print("PASS T10-03 / renders shell with tree defaults + empty expand")
