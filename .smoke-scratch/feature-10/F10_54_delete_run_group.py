# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / SM2 -- delete_run_group.

SM2: delete_run_group(project, group) deletes an empty group folder;
     it is idempotent on a missing target and refuses (ValueError) to
     delete a group that still contains runs (forcing explicit
     delete_run first). The typed-area folder test-run/ itself is left
     in place.
"""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_run_group("Alpha", "release-1")
    s.create_run(project="Alpha", group="release-1", name="Smoke",
                 file_name="smoke", case_paths=[])

    # --- SM2: refuses to delete a non-empty group. ---
    try:
        s.delete_run_group("Alpha", "release-1")
        raise AssertionError("non-empty group delete must raise ValueError")
    except ValueError:
        pass
    assert (root / "Alpha" / "test-run" / "release-1").is_dir()

    # --- SM2: after the run is removed, the empty group deletes. ---
    s.delete_run("Alpha", "release-1", "smoke.yaml")
    s.delete_run_group("Alpha", "release-1")
    assert not (root / "Alpha" / "test-run" / "release-1").exists()
    # The typed-area folder itself stays put.
    assert (root / "Alpha" / "test-run").is_dir(), "test-run/ must survive group deletion"

    # --- SM2: idempotent on a now-missing target. ---
    s.delete_run_group("Alpha", "release-1")  # must not raise

print("PASS  SM2: delete_run_group refuses non-empty, deletes empty, idempotent on missing; test-run/ survives")
