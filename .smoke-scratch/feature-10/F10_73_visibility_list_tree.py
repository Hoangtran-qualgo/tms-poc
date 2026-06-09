# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / SV1 -- list_tree hides the typed area.

SV1: Storage.list_tree() filters `test-run` out of every project's
     children, so the Directory tree sidebar tab never shows the typed
     area as a folder. Ordinary modules still appear.
"""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_run_group("Alpha", "release-1")  # makes Alpha/test-run/

    tree = s.list_tree()
    alpha = next(c for c in tree["children"] if c["name"] == "Alpha")
    child_names = {c["name"] for c in alpha["children"]}

    # --- SV1: real module present, typed area hidden. ---
    assert "Checkout" in child_names, child_names
    assert "test-run" not in child_names, (
        f"list_tree must hide the test-run typed area, got {child_names}"
    )

print("PASS  SV1: list_tree hides test-run from a project's children (ordinary modules still listed)")
