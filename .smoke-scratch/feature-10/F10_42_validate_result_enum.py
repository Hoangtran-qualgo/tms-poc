# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / DM3 + SM14 + SM7 -- validate_run result enum.

DM3: every RunResult.result must be one of RUN_RESULTS; an invalid value
     is rejected at write with ValidationError -> HTTP 422.
SM14: validate_run runs before every write and reports a path-style
     locator (`results[<i>].result`) in the error envelope's
     details.field.
SM7: write_run validates *first* / writes atomically -- a rejected
     PATCH must leave the on-disk YAML byte-for-byte unchanged.

Exercised end-to-end through PATCH /api/runs/... (the editor Save path,
which routes through write_run -> _serialize_run -> validate_run).
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

    yaml_path = root / "Alpha" / "test-run" / "release-1" / "smoke.yaml"
    before = yaml_path.read_bytes()

    client = app.test_client()
    payload = {
        "name": "Smoke",
        "created_at": s.read_run("Alpha", "release-1", "smoke.yaml").created_at,
        "description": "",
        "results": [
            {"file_path": "Alpha/Checkout/a.feature", "result": "BOGUS", "remark": ""},
        ],
    }
    r = client.patch("/api/runs/Alpha/release-1/smoke.yaml",
                     data=json.dumps(payload), content_type="application/json")

    # --- DM3 + SM14: invalid result -> 422 validation_error w/ path locator ---
    assert r.status_code == 422, (r.status_code, r.get_data(as_text=True))
    env = r.get_json()["error"]
    assert env["code"] == "validation_error", env
    assert env["details"]["field"] == "results[0].result", env["details"]
    assert "BOGUS" in env["message"], env["message"]

    # --- SM7: the rejected write left the file unchanged (validate-first). ---
    assert yaml_path.read_bytes() == before, (
        "a rejected PATCH must not mutate the on-disk run (validate before write)"
    )

print("PASS  DM3+SM14+SM7: invalid result -> 422 validation_error @ results[0].result; on-disk run unchanged")
