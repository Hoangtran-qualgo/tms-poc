# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / DM4 -- file_path non-empty, NOT disk-validated.

DM4: validate_run requires every file_path to be non-empty (empty ->
     422), but it does NOT check the path against disk -- a non-empty
     path that points at a file which does not exist is accepted at
     write time (tombstone rendering is a UI concern, per spec).

Exercised end-to-end through PATCH /api/runs/... .
"""
import json
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
                 file_name="smoke", case_paths=["Alpha/Checkout/a.feature"])
    created_at = s.read_run("Alpha", "release-1", "smoke.yaml").created_at
    client = app.test_client()

    def patch(results):
        return client.patch(
            "/api/runs/Alpha/release-1/smoke.yaml",
            data=json.dumps({"name": "Smoke", "created_at": created_at,
                             "description": "", "results": results}),
            content_type="application/json",
        )

    # --- DM4: empty file_path -> 422. ---
    r = patch([{"file_path": "", "result": "PENDING", "remark": ""}])
    assert r.status_code == 422, (r.status_code, r.get_data(as_text=True))
    env = r.get_json()["error"]
    assert env["code"] == "validation_error", env
    assert env["details"]["field"] == "results[0].file_path", env["details"]

    # --- DM4: a non-existent (but non-empty) path is ACCEPTED at write. ---
    ghost = "Alpha/Checkout/does-not-exist.feature"
    assert not (root / ghost).exists(), "precondition: ghost path absent on disk"
    r2 = patch([{"file_path": ghost, "result": "PENDING", "remark": ""}])
    assert r2.status_code == 200, (r2.status_code, r2.get_data(as_text=True))
    stored = s.read_run("Alpha", "release-1", "smoke.yaml")
    assert [x.file_path for x in stored.results] == [ghost], (
        "a non-empty path must persist even though it does not exist on disk"
    )

print("PASS  DM4: empty file_path -> 422; non-existent-but-non-empty path persists (no disk validation at write)")
