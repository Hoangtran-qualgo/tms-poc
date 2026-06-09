# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / SM13 -- list_projects.

SM13: list_projects() returns every depth-0 directory name, sorted
     case-insensitively. Backs GET /api/run-groups so the create
     modal can target bare projects (those without a test-run/ folder).
"""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    # Deliberately mixed case + non-alphabetical creation order.
    for name in ["Charlie", "alpha", "Bravo"]:
        s.create_folder([name])

    got = s.list_projects()

    # --- SM13: case-insensitive sort (alpha, Bravo, Charlie). ---
    assert got == ["alpha", "Bravo", "Charlie"], got
    # Sanity: the sort is case-insensitive, not plain ASCII (which would
    # put the capitals 'Bravo'/'Charlie' before lowercase 'alpha').
    assert got != sorted(got), "plain ASCII sort would differ -> proves case-insensitive"

print("PASS  SM13: list_projects returns every depth-0 dir, case-insensitively sorted")
