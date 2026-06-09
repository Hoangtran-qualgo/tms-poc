# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / DM5 -- duplicate file_path rejected at write.

DM5: the same case cannot appear twice in one run; validate_run rejects
     duplicate file_path entries with ValidationError -> HTTP 422, with
     the path locator pointing at the *second* (duplicate) row.

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

    client = app.test_client()
    payload = {
        "name": "Smoke",
        "created_at": s.read_run("Alpha", "release-1", "smoke.yaml").created_at,
        "description": "",
        "results": [
            {"file_path": "Alpha/Checkout/a.feature", "result": "PASSED", "remark": ""},
            {"file_path": "Alpha/Checkout/a.feature", "result": "FAILED", "remark": ""},
        ],
    }
    r = client.patch("/api/runs/Alpha/release-1/smoke.yaml",
                     data=json.dumps(payload), content_type="application/json")

    assert r.status_code == 422, (r.status_code, r.get_data(as_text=True))
    env = r.get_json()["error"]
    assert env["code"] == "validation_error", env
    # The duplicate is the second row, so the locator points at results[1].
    assert env["details"]["field"] == "results[1].file_path", env["details"]
    assert "Duplicate" in env["message"], env["message"]

print("PASS  DM5: duplicate file_path -> 422 validation_error @ results[1].file_path")
