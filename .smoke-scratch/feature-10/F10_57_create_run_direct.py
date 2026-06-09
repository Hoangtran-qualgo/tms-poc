# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / SM5 + SM16 -- create_run storage behaviour.

SM5: create_run stamps created_at server-side, writes the YAML, and
     turns each case_path into a RunResult with result="PENDING" and an
     empty remark.
SM16: an empty results list is legal -- a run can be created with no
     cases (the editor then shows its empty-state row).

DRIFT (SM5 / FL6 'auto-create group'): the spec says create_run
'auto-creates the group folder if missing' / 'calls create_run_group
implicitly when needed'. The as-shipped storage does NOT -- create_run
raises FileNotFoundError when the group folder is absent (the create
modal POSTs the group first, then the run). Pinned below so the drift
is caught if the implicit-create is ever added.
"""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])

    # --- SM5 DRIFT: create_run requires the group to already exist. ---
    try:
        s.create_run(project="Alpha", group="ghost", name="X",
                     file_name="x", case_paths=[])
        raise AssertionError("create_run must raise when the group is missing "
                             "(spec's 'auto-create' is a drift)")
    except FileNotFoundError:
        pass

    s.create_run_group("Alpha", "release-1")

    # --- SM5: case_paths -> PENDING rows with empty remark + stamped created_at. ---
    s.create_run(project="Alpha", group="release-1", name="Sprint 1",
                 file_name="sprint-1",
                 case_paths=["Alpha/m/a.feature", "Alpha/m/b.feature"])
    run = s.read_run("Alpha", "release-1", "sprint-1.yaml")
    assert run.created_at, "created_at must be stamped on create"
    assert [(r.result, r.remark) for r in run.results] == [
        ("PENDING", ""), ("PENDING", "")], [(r.result, r.remark) for r in run.results]

    # --- SM16: empty results list is legal. ---
    s.create_run(project="Alpha", group="release-1", name="Empty",
                 file_name="empty", case_paths=[])
    assert s.read_run("Alpha", "release-1", "empty.yaml").results == []

print("PASS  SM5+SM16: create_run stamps created_at + PENDING rows; empty results legal; group must pre-exist (drift pinned)")
