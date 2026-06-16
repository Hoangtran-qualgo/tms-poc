# Pattern: see .smoke-scratch/README.md
"""tech-07 / require scenario_name at the create API (SN-1 = Option A).

POST /api/files now REQUIRES a non-empty scenario_name (entry-point
enforcement; the model stays permissive per V5). Covers:
- SN-1: missing / empty scenario_name -> 400 bad_request.
- SN-3: whitespace-only scenario_name -> 400 (stripped == empty).
- type guard: non-string scenario_name -> 400.
- happy path: a real scenario_name -> 201 + scenario.name on disk.
- regression: description stays OPTIONAL (tech-04 D1).
"""
import pathlib
import tempfile

from app import create_app


def _expect_400(resp, needle="scenario_name"):
    assert resp.status_code == 400, (resp.status_code, resp.get_data(as_text=True))
    err = resp.get_json()["error"]
    assert err["code"] == "bad_request", err
    assert needle in err["message"], (needle, err["message"])


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})

    # --- SN-1: scenario_name omitted -> 400 -------------------------------
    _expect_400(
        client.post(
            "/api/files",
            json={"parent": "Alpha/Mod", "file_name": "a", "description": "d"},
        )
    )

    # --- SN-1: empty scenario_name -> 400 ---------------------------------
    _expect_400(
        client.post(
            "/api/files",
            json={"parent": "Alpha/Mod", "file_name": "a", "scenario_name": ""},
        )
    )

    # --- SN-3: whitespace-only scenario_name -> 400 -----------------------
    _expect_400(
        client.post(
            "/api/files",
            json={"parent": "Alpha/Mod", "file_name": "a", "scenario_name": "   "},
        )
    )

    # --- type guard: non-string scenario_name -> 400 ----------------------
    _expect_400(
        client.post(
            "/api/files",
            json={"parent": "Alpha/Mod", "file_name": "a", "scenario_name": 123},
        )
    )

    # --- happy path: real scenario_name -> 201 + identity on disk ---------
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "ok",
              "scenario_name": "Pay with card"},
    )
    assert r.status_code == 201, (r.status_code, r.get_data(as_text=True))
    body = client.get("/api/files/Alpha/Mod/ok.feature").get_json()
    assert body["scenario"]["name"] == "Pay with card", body
    # Regression: description omitted is still allowed (tech-04 D1).
    assert body["description"] == "", body

print(
    "PASS  T07_01: POST /api/files requires a non-empty scenario_name "
    "(missing/empty/blank/non-string -> 400; valid -> 201; description optional)"
)
