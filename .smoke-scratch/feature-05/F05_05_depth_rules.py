# Pattern: see .smoke-scratch/README.md
"""feature-05 / testcase-crud / Depth rules (DR1-DR3)."""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()

    # Build a depth-10 chain so we have parents at every depth 1..10.
    segments: list[str] = []
    for i in range(1, 11):
        client.post("/api/folders", json={"parent": "/".join(segments), "name": f"d{i}"})
        segments.append(f"d{i}")

    # --- DR1: file CREATE parent depth 2..10 -------------------------------
    # Depth 0 (root) -> 400.
    r = client.post(
        "/api/files",
        json={"parent": "", "file_name": "f", "scenario_name": "s", "description": "x"},
    )
    assert r.status_code == 400, (
        f"DR1: file create at root (depth 0) must return 400, got {r.status_code}"
    )
    assert r.get_json()["error"]["code"] == "bad_request"

    # Depth 1 (project) -> 400.
    r = client.post(
        "/api/files",
        json={"parent": "d1", "file_name": "f", "scenario_name": "s", "description": "x"},
    )
    assert r.status_code == 400, (
        f"DR1: file create at project (depth 1) must return 400, got {r.status_code}"
    )

    # Depth 2 (module) -> 201.
    r = client.post(
        "/api/files",
        json={"parent": "d1/d2", "file_name": "f_at_2", "scenario_name": "s", "description": "x"},
    )
    assert r.status_code == 201, (
        f"DR1: file create at depth 2 (module) must succeed, got {r.status_code}"
    )

    # Depth 10 (deep sub-folder) -> 201.
    parent_10 = "/".join(segments)  # d1/d2/.../d10
    r = client.post(
        "/api/files",
        json={"parent": parent_10, "file_name": "f_at_10", "scenario_name": "s", "description": "x"},
    )
    assert r.status_code == 201, (
        f"DR1: file create at depth 10 must succeed, got {r.status_code}"
    )

    # Depth 11 -> 400 (rejected by server.post_file).
    r = client.post(
        "/api/files",
        json={"parent": parent_10 + "/d11", "file_name": "f", "scenario_name": "s", "description": "x"},
    )
    assert r.status_code == 400, (
        f"DR1: file create at depth 11 must return 400, got {r.status_code}"
    )
print("PASS  DR1: file create parent depth must be 2..10; 0/1/11+ -> 400 bad_request")


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()

    # Build source at depth 2; dest variants at depth 1 / 2 / 10 / 11.
    client.post("/api/folders", json={"name": "Src"})
    client.post("/api/folders", json={"parent": "Src", "name": "ModA"})
    client.post("/api/folders", json={"parent": "Src", "name": "ModB"})  # depth 2 dest
    client.post(
        "/api/files",
        json={"parent": "Src/ModA", "file_name": "case", "scenario_name": "s", "description": "seed"},
    )
    # Depth-10 dest chain.
    deep_segments = ["Src", "ModA"]
    for i in range(3, 11):
        client.post(
            "/api/folders",
            json={"parent": "/".join(deep_segments), "name": f"s{i}"},
        )
        deep_segments.append(f"s{i}")
    parent_10 = "/".join(deep_segments)  # depth 10

    # --- DR2: MOVE destination parent depth 2..10 --------------------------
    # Depth 1 dest -> 400.
    r = client.patch(
        "/api/files/Src/ModA/case.feature/move",
        json={"parent": "Src"},
    )
    assert r.status_code == 400, (
        f"DR2: move dest depth 1 must return 400, got {r.status_code}"
    )

    # Depth 11 dest -> 400.
    r = client.patch(
        "/api/files/Src/ModA/case.feature/move",
        json={"parent": parent_10 + "/s11"},
    )
    assert r.status_code == 400, (
        f"DR2: move dest depth 11 must return 400, got {r.status_code}"
    )

    # Depth 2 (sibling module) -> 200.
    r = client.patch(
        "/api/files/Src/ModA/case.feature/move",
        json={"parent": "Src/ModB"},
    )
    assert r.status_code == 200, (
        f"DR2: move dest depth 2 must succeed, got {r.status_code}"
    )
    assert (root / "Src" / "ModB" / "case.feature").is_file()
print("PASS  DR2: move destination parent depth must be 2..10; 1/11+ -> 400")


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()

    # --- DR3: rename / duplicate inherit source parent depth ---------------
    # Build a file at depth 2 and a file at depth 10 to exercise both ends.
    client.post("/api/folders", json={"name": "Top"})
    client.post("/api/folders", json={"parent": "Top", "name": "Mod"})  # depth 2
    client.post(
        "/api/files",
        json={"parent": "Top/Mod", "file_name": "shallow", "scenario_name": "s", "description": "x"},
    )

    deep_segments = ["Top", "Mod"]
    for i in range(3, 11):
        client.post(
            "/api/folders",
            json={"parent": "/".join(deep_segments), "name": f"s{i}"},
        )
        deep_segments.append(f"s{i}")
    parent_10 = "/".join(deep_segments)
    client.post(
        "/api/files",
        json={"parent": parent_10, "file_name": "deep", "scenario_name": "s", "description": "x"},
    )

    # Rename at depth 2 -> 200.
    r = client.patch(
        "/api/files/Top/Mod/shallow.feature/rename",
        json={"file_name": "shallow_r"},
    )
    assert r.status_code == 200, (
        f"DR3: rename at source-depth 2 must succeed, got {r.status_code}"
    )

    # Rename at depth 10 (the deepest valid) -> 200.
    r = client.patch(
        f"/api/files/{parent_10}/deep.feature/rename",
        json={"file_name": "deep_r"},
    )
    assert r.status_code == 200, (
        f"DR3: rename at source-depth 10 must succeed, got {r.status_code}"
    )

    # Duplicate at depth 2 -> 201.
    r = client.post(
        "/api/files/Top/Mod/shallow_r.feature/duplicate",
        json={"file_name": "shallow_d"},
    )
    assert r.status_code == 201, (
        f"DR3: duplicate at source-depth 2 must succeed, got {r.status_code}"
    )

    # Duplicate at depth 10 -> 201.
    r = client.post(
        f"/api/files/{parent_10}/deep_r.feature/duplicate",
        json={"file_name": "deep_d"},
    )
    assert r.status_code == 201, (
        f"DR3: duplicate at source-depth 10 must succeed, got {r.status_code}"
    )
print("PASS  DR3: rename / duplicate inherit source parent depth (2 and 10 both succeed)")
