# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / AP6 + SM9 -- POST .../cases.

AP6/SM9: POST /api/runs/<p>/<g>/<file>/cases with {file_path} appends a
     fresh RunResult (PENDING, empty remark) and returns 201. A
     duplicate file_path is rejected with NameConflictError -> 409.
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
                 file_name="smoke", case_paths=["Alpha/m/a.feature"])

    client = app.test_client()

    # --- AP6 + SM9: append a new case -> 201, PENDING + empty remark. ---
    r = client.post("/api/runs/Alpha/release-1/smoke.yaml/cases",
                    data=json.dumps({"file_path": "Alpha/m/b.feature"}),
                    content_type="application/json")
    assert r.status_code == 201, (r.status_code, r.get_data(as_text=True))
    run = s.read_run("Alpha", "release-1", "smoke.yaml")
    appended = run.results[-1]
    assert appended.file_path == "Alpha/m/b.feature"
    assert appended.result == "PENDING" and appended.remark == ""

    # --- SM9: duplicate case -> 409 name_conflict. ---
    r2 = client.post("/api/runs/Alpha/release-1/smoke.yaml/cases",
                     data=json.dumps({"file_path": "Alpha/m/a.feature"}),
                     content_type="application/json")
    assert r2.status_code == 409, (r2.status_code, r2.get_data(as_text=True))
    assert r2.get_json()["error"]["code"] == "name_conflict"

print("PASS  AP6+SM9: POST cases appends PENDING row (201); duplicate case -> 409")
