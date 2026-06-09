# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / AP8 + SM11 -- PATCH .../cases/<path>.

AP8/SM11: PATCH /api/runs/<p>/<g>/<file>/cases/<case_path> applies a
     partial update -- `result` and `remark` are independently optional
     and only the supplied field changes.
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
    url = "/api/runs/Alpha/release-1/smoke.yaml/cases/Alpha/m/a.feature"

    def patch(payload):
        return client.patch(url, data=json.dumps(payload),
                            content_type="application/json")

    # --- SM11: result-only update leaves remark untouched. ---
    assert patch({"result": "PASSED"}).status_code == 200
    row = s.read_run("Alpha", "release-1", "smoke.yaml").results[0]
    assert row.result == "PASSED" and row.remark == "", row

    # --- SM11: remark-only update leaves result untouched. ---
    assert patch({"remark": "looks good"}).status_code == 200
    row = s.read_run("Alpha", "release-1", "smoke.yaml").results[0]
    assert row.result == "PASSED" and row.remark == "looks good", row

    # --- AP8: an invalid result value still flows through validate_run -> 422. ---
    r = patch({"result": "NOPE"})
    assert r.status_code == 422, (r.status_code, r.get_data(as_text=True))
    assert r.get_json()["error"]["code"] == "validation_error"

print("PASS  AP8+SM11: PATCH case applies partial result/remark updates; invalid result -> 422")
