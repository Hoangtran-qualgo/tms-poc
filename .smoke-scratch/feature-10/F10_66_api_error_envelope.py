# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / AP12 -- standard error envelope.

AP12: all run-API errors use the `{error: {code, message, details}}`
     envelope. This checks the three mappings the run surface relies on:
       - NameConflictError -> 409 name_conflict, details.path
       - ValidationError   -> 422 validation_error, details.field
       - ValueError        -> 400 bad_request
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
    client = app.test_client()

    def assert_envelope(resp, status, code):
        assert resp.status_code == status, (resp.status_code, resp.get_data(as_text=True))
        body = resp.get_json()
        assert set(body) == {"error"}, body
        err = body["error"]
        # code + message are always present; details is included only when
        # the error carries a locator (path / field), so it is optional.
        assert {"code", "message"} <= set(err) <= {"code", "message", "details"}, err
        assert err["code"] == code, err
        assert isinstance(err["message"], str) and err["message"], err
        return err

    # --- 409 name_conflict (+ details.path): duplicate group. ---
    err = assert_envelope(client.post("/api/runs/Alpha/groups",
                          data=json.dumps({"name": "release-1"}),
                          content_type="application/json"), 409, "name_conflict")
    assert "path" in err["details"], err["details"]

    # --- 422 validation_error (+ details.field): empty run name on create. ---
    s.create_run(project="Alpha", group="release-1", name="Smoke",
                 file_name="smoke", case_paths=[])
    created_at = s.read_run("Alpha", "release-1", "smoke.yaml").created_at
    err = assert_envelope(client.patch("/api/runs/Alpha/release-1/smoke.yaml",
                          data=json.dumps({"name": "  ", "created_at": created_at,
                                           "description": "", "results": []}),
                          content_type="application/json"), 422, "validation_error")
    assert "field" in err["details"], err["details"]

    # --- 400 bad_request: missing required field on create. ---
    assert_envelope(client.post("/api/runs",
                    data=json.dumps({"group": "release-1"}),
                    content_type="application/json"), 400, "bad_request")

print("PASS  AP12: run-API errors use {error:{code,message,details}} (409/422/400 mappings verified)")
