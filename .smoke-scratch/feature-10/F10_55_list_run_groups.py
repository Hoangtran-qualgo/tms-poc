# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / SM3 -- list_run_groups.

SM3: list_run_groups(project) returns the group folder names under
     `<project>/test-run/`, or `[]` when the project has no test-run/
     folder yet (lazy creation).
"""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])

    # --- SM3: no test-run/ yet -> []. ---
    assert s.list_run_groups("Alpha") == [], "absent typed area must list as []"

    # --- SM3: lists every created group. ---
    s.create_run_group("Alpha", "release-1")
    s.create_run_group("Alpha", "nightly")
    assert sorted(s.list_run_groups("Alpha")) == ["nightly", "release-1"]

print("PASS  SM3: list_run_groups returns [] without a typed area, else the group names")
