# Pattern: see .smoke-scratch/README.md
"""feature-05 / testcase-crud / Create body (CB1)."""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})

    # --- CB1: file_name required; scenario_name + description OPTIONAL ----
    # tech-04 Option B: the API permits an empty scenario name (model V5);
    # the create modal enforces "required" client-side. Hard API enforcement
    # is a separate Must-have ("Require scenario_name at API").
    # Missing file_name -> 400 bad_request.
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "scenario_name": "x", "description": "d"},
    )
    assert r.status_code == 400, (
        f"CB1: missing file_name must return 400, got {r.status_code}"
    )
    assert r.get_json()["error"]["code"] == "bad_request"

    # Non-string scenario_name / description -> 400 (type guard).
    for field, bad in (
        ("scenario_name", 123), ("scenario_name", []),
        ("description", 123), ("description", []),
    ):
        r = client.post(
            "/api/files",
            json={"parent": "Alpha/Mod", "file_name": "bad", field: bad},
        )
        assert r.status_code == 400, (
            f"CB1: non-string {field}={bad!r} must return 400, got {r.status_code}"
        )

    # Both scenario_name and description omitted -> 201 (both optional).
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "bare"},
    )
    assert r.status_code == 201, (
        f"CB1: omitting scenario_name + description must succeed, got {r.status_code}"
    )
    bare = client.get("/api/files/Alpha/Mod/bare.feature").get_json()
    assert bare["description"] == "", f"bare description must be '', got {bare['description']!r}"
    assert bare["scenario"]["name"] == "", (
        f"bare scenario name must be '', got {bare['scenario']['name']!r}"
    )

    # Valid create with both fields -> 201; scenario.name carries identity.
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "ok",
              "scenario_name": "Pay with card", "description": "valid desc"},
    )
    assert r.status_code == 201, (
        f"CB1: valid create must succeed, got {r.status_code}"
    )

    # --- CB1: created file shape -- scenario.name carries the identity -----
    body = client.get("/api/files/Alpha/Mod/ok.feature").get_json()
    assert body["description"] == "valid desc", (
        f"CB1: created file's description must echo the supplied value, "
        f"got {body['description']!r}"
    )
    assert body.get("tags") == [], (
        f"CB1: created file must have no tags, got {body.get('tags')!r}"
    )

    background = body.get("background", {})
    assert background.get("steps") == [], (
        f"CB1: created file must have empty background (no steps), got {background!r}"
    )

    scenario = body.get("scenario", {})
    assert scenario.get("kind") == "scenario", (
        f"CB1: created scenario kind must be 'scenario', got {scenario.get('kind')!r}"
    )
    assert scenario.get("name") == "Pay with card", (
        f"CB1: created scenario name must echo scenario_name, got {scenario.get('name')!r}"
    )
    assert scenario.get("steps") == [], (
        f"CB1: created scenario must have no steps, got {scenario.get('steps')!r}"
    )
    assert scenario.get("tags") == [], (
        f"CB1: created scenario must have no tags, got {scenario.get('tags')!r}"
    )
print(
    "PASS  CB1: file_name required; scenario_name + description optional at API "
    "(non-string rejected); scenario.name carries the identity when provided"
)
