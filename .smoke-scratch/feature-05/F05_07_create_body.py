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

    # --- CB1: description required non-empty (API-layer rejection) --------
    # Missing field entirely -> 400 bad_request.
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "a"},
    )
    assert r.status_code == 400, (
        f"CB1: missing description must return 400, got {r.status_code}"
    )
    assert r.get_json()["error"]["code"] == "bad_request"

    # Empty string -> 400.
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "b", "description": ""},
    )
    assert r.status_code == 400, (
        f"CB1: empty description must return 400, got {r.status_code}"
    )
    assert r.get_json()["error"]["code"] == "bad_request"

    # Whitespace-only -> 400 (the API layer strips).
    for ws in ("   ", "\t", "\n", " \t \n "):
        r = client.post(
            "/api/files",
            json={"parent": "Alpha/Mod", "file_name": "ws", "description": ws},
        )
        assert r.status_code == 400, (
            f"CB1: whitespace-only description {ws!r} must return 400, got {r.status_code}"
        )
        assert r.get_json()["error"]["code"] == "bad_request"
        assert not (root / "Alpha" / "Mod" / "ws.feature").exists(), (
            f"CB1: rejected description {ws!r} must NOT create file on disk"
        )

    # Non-string description (number, list, null) -> 400.
    for bad in (123, [], None, True):
        r = client.post(
            "/api/files",
            json={"parent": "Alpha/Mod", "file_name": "nonstr", "description": bad},
        )
        assert r.status_code == 400, (
            f"CB1: non-string description {bad!r} must return 400, got {r.status_code}"
        )

    # Valid description -> 201.
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "ok", "description": "valid desc"},
    )
    assert r.status_code == 201, (
        f"CB1: valid description must succeed, got {r.status_code}"
    )

    # --- CB1: created file shape -- one empty scenario, no extras ----------
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
    assert scenario.get("name") == "", (
        f"CB1: created scenario name must be empty string, got {scenario.get('name')!r}"
    )
    assert scenario.get("steps") == [], (
        f"CB1: created scenario must have no steps, got {scenario.get('steps')!r}"
    )
    assert scenario.get("tags") == [], (
        f"CB1: created scenario must have no tags, got {scenario.get('tags')!r}"
    )
print(
    "PASS  CB1: description required non-empty (whitespace rejected at API); "
    "created file holds Feature(description=…, scenario=Scenario(kind='scenario', name=''))"
)
