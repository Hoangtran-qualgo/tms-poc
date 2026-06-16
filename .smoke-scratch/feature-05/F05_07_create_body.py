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

    # --- CB1: file_name + scenario_name required; description OPTIONAL -----
    # tech-07 (SN-1 = Option A): scenario_name is REQUIRED at the API,
    # matching the create modal's client-side gate (tech-04 RG1) and the
    # import path's server-side enforcement. The model stays permissive (V5);
    # enforcement lives at this entry point.
    # Missing file_name -> 400 bad_request.
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "scenario_name": "x", "description": "d"},
    )
    assert r.status_code == 400, (
        f"CB1: missing file_name must return 400, got {r.status_code}"
    )
    assert r.get_json()["error"]["code"] == "bad_request"

    # Missing scenario_name -> 400 bad_request (tech-07).
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "noscen", "description": "d"},
    )
    assert r.status_code == 400, (
        f"CB1: missing scenario_name must return 400, got {r.status_code}"
    )
    assert r.get_json()["error"]["code"] == "bad_request"
    assert "scenario_name" in r.get_json()["error"]["message"], r.get_json()

    # Whitespace-only scenario_name -> 400 (tech-07 SN-3: stripped == empty).
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "wsname", "scenario_name": "   "},
    )
    assert r.status_code == 400, (
        f"CB1: whitespace-only scenario_name must return 400, got {r.status_code}"
    )

    # Non-string scenario_name -> 400 (type/required guard).
    for bad in (123, []):
        r = client.post(
            "/api/files",
            json={"parent": "Alpha/Mod", "file_name": "bad", "scenario_name": bad},
        )
        assert r.status_code == 400, (
            f"CB1: non-string scenario_name={bad!r} must return 400, got {r.status_code}"
        )

    # Non-string description (with a valid scenario_name) -> 400 (type guard).
    for bad in (123, []):
        r = client.post(
            "/api/files",
            json={"parent": "Alpha/Mod", "file_name": "bad",
                  "scenario_name": "ok", "description": bad},
        )
        assert r.status_code == 400, (
            f"CB1: non-string description={bad!r} must return 400, got {r.status_code}"
        )

    # description omitted (scenario_name present) -> 201 (description optional).
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "bare", "scenario_name": "Pay"},
    )
    assert r.status_code == 201, (
        f"CB1: omitting only description must succeed, got {r.status_code}"
    )
    bare = client.get("/api/files/Alpha/Mod/bare.feature").get_json()
    assert bare["description"] == "", f"bare description must be '', got {bare['description']!r}"
    assert bare["scenario"]["name"] == "Pay", (
        f"bare scenario name must echo scenario_name, got {bare['scenario']['name']!r}"
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
    "PASS  CB1: file_name + scenario_name required at API (missing/blank/"
    "non-string rejected); description optional; scenario.name carries identity"
)
