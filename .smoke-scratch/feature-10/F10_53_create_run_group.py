# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / SM1 -- create_run_group.

SM1: create_run_group(project, group) validates the segments and
     creates `<project>/test-run/<group>/`, lazily creating
     `<project>/test-run/` along the way. Raises FileNotFoundError if
     the project is missing and NameConflictError if the group already
     exists.
"""
import tempfile, pathlib
from app import create_app
from app.storage import Storage
from app.errors import NameConflictError

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])

    # Precondition: the typed area does not exist before the first group.
    assert not (root / "Alpha" / "test-run").exists()

    # --- SM1: creates the group + lazily materialises test-run/. ---
    s.create_run_group("Alpha", "release-1")
    assert (root / "Alpha" / "test-run").is_dir(), "test-run/ must be lazily created"
    assert (root / "Alpha" / "test-run" / "release-1").is_dir()
    assert s.list_run_groups("Alpha") == ["release-1"]

    # --- SM1: duplicate group -> NameConflictError. ---
    try:
        s.create_run_group("Alpha", "release-1")
        raise AssertionError("duplicate group must raise NameConflictError")
    except NameConflictError:
        pass

    # --- SM1: missing project -> FileNotFoundError. ---
    try:
        s.create_run_group("Ghost", "g")
        raise AssertionError("missing project must raise FileNotFoundError")
    except FileNotFoundError:
        pass

print("PASS  SM1: create_run_group lazily makes test-run/, rejects duplicate (409) + missing project (404)")
