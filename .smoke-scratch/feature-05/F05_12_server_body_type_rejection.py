# Pattern: see .smoke-scratch/README.md
"""feature-05 / testcase-crud / server body type-rejection (condition-coverage gap-closer).

Cross-cutting: exercises the shared `app/server/_shared.py` request-validation
helpers used by the file, folder, and run routes. The existing suite
drives the *empty/whitespace* legs of these guards but never the
`not isinstance(...)` legs, so the type-checks below were untested
(decision + condition coverage gap "Pattern A"). Each wrong-typed body
must surface a `400 bad_request` (`ValueError` → `_handle_value_error`).
Validation runs before any storage call, so no on-disk setup is needed.

Cross-credit: the run-route cases (`/api/runs*`) primary-frame
feature-10; they live here because they share the same server helpers.
"""
import tempfile, pathlib
from app import create_app


def _expect_400(resp, needle):
    assert resp.status_code == 400, (resp.status_code, resp.get_data(as_text=True))
    err = resp.get_json()["error"]
    assert err["code"] == "bad_request", err
    assert needle in err["message"], (needle, err["message"])


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    c = app.test_client()

    # --- POST /api/files: `_require_non_empty_string` isinstance leg. ---
    _expect_400(c.post("/api/files", json={"file_name": 123}), "file_name")

    # --- POST /api/files: description isinstance leg (line ~180). ---
    # tech-07: scenario_name is now required at the API and is checked before
    # description/parent, so supply a valid one to reach those guards.
    _expect_400(
        c.post("/api/files", json={"file_name": "a.feature", "scenario_name": "s", "description": 123}),
        "description",
    )

    # --- POST /api/files: `_parent_to_segments` isinstance leg. ---
    _expect_400(
        c.post(
            "/api/files",
            json={"file_name": "a.feature", "scenario_name": "s", "description": "d", "parent": 123},
        ),
        "'parent' must be a string",
    )

    # --- PATCH /api/files/<p>/move: both legs of the parent guard. ---
    _expect_400(c.patch("/api/files/x.feature/move", json={}), "'parent' must be a string")
    _expect_400(c.patch("/api/files/x.feature/move", json={"parent": 123}), "'parent' must be a string")

    # --- POST /api/runs: `_require_list_of_str` both legs (non-list; list w/ non-str). ---
    base = {"project": "P", "group": "G", "name": "N", "file_name": "f"}
    _expect_400(c.post("/api/runs", json={**base, "case_paths": "x"}), "list of strings")
    _expect_400(c.post("/api/runs", json={**base, "case_paths": ["ok", 123]}), "list of strings")

    # --- POST /api/runs: `_require_optional_str` isinstance leg. ---
    _expect_400(
        c.post("/api/runs", json={**base, "case_paths": [], "description": 123}),
        "'description' must be a string if present",
    )

    # --- PATCH /api/runs/.../cases/<case>: result / remark isinstance legs. ---
    _expect_400(
        c.patch("/api/runs/P/G/f/cases/c", json={"result": 123}),
        "'result' must be a string if present",
    )
    _expect_400(
        c.patch("/api/runs/P/G/f/cases/c", json={"remark": 123}),
        "'remark' must be a string if present",
    )

print("PASS  Pattern A: server body type-guards reject non-str/non-list inputs with 400 bad_request")
