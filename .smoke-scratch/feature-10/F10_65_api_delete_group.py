# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / AP10 -- DELETE /api/runs/<p>/groups/<group>.

AP10: deletes an empty group, returning 204. A non-empty group is
     refused (delete_run_group raises ValueError -> HTTP 400), forcing
     explicit run deletion first.
"""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_run_group("Alpha", "empty-grp")
    s.create_run_group("Alpha", "full-grp")
    s.create_run(project="Alpha", group="full-grp", name="Smoke",
                 file_name="smoke", case_paths=[])

    client = app.test_client()

    # --- AP10: non-empty group -> 400 bad_request (refused). ---
    r = client.delete("/api/runs/Alpha/groups/full-grp")
    assert r.status_code == 400, (r.status_code, r.get_data(as_text=True))
    assert r.get_json()["error"]["code"] == "bad_request"
    assert (root / "Alpha" / "test-run" / "full-grp").is_dir()

    # --- AP10: empty group -> 204, folder gone. ---
    r2 = client.delete("/api/runs/Alpha/groups/empty-grp")
    assert r2.status_code == 204, (r2.status_code, r2.get_data(as_text=True))
    assert not (root / "Alpha" / "test-run" / "empty-grp").exists()

print("PASS  AP10: DELETE empty group -> 204; non-empty group refused -> 400")
