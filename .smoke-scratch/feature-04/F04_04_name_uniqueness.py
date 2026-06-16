# Pattern: see .smoke-scratch/README.md
"""feature-04 / folder-crud / Name uniqueness (NU1-NU2).

Route-layer assertions; the storage-half of NU1 lives in feature-02's
F02_04_name_uniqueness.py.
"""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()

    # --- NU1: duplicate folder in same parent -> 409 name_conflict ---------
    # Depth-1 duplicate.
    r = client.post("/api/folders", json={"name": "Alpha"})
    assert r.status_code == 201, "NU1 setup: first create must succeed"
    r = client.post("/api/folders", json={"name": "Alpha"})
    assert r.status_code == 409, (
        f"NU1: duplicate depth-1 POST must return 409, got {r.status_code}"
    )
    body = r.get_json()
    assert body and body.get("error", {}).get("code") == "name_conflict", (
        f"NU1: duplicate must carry error.code='name_conflict', got {body!r}"
    )
    assert body["error"].get("details", {}).get("path") == "Alpha", (
        f"NU1: error.details.path must echo the conflicting key, got {body['error']!r}"
    )

    # Depth-2 duplicate (module under project).
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    r = client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    assert r.status_code == 409, (
        f"NU1: duplicate depth-2 POST must return 409, got {r.status_code}"
    )
    assert r.get_json()["error"]["code"] == "name_conflict", (
        "NU1: depth-2 duplicate must carry error.code='name_conflict'"
    )

    # PATCH-rename into a taken slot -> 409 too (rename collision).
    client.post("/api/folders", json={"name": "Beta"})
    r = client.patch("/api/folders/Beta", json={"name": "Alpha"})
    assert r.status_code == 409, (
        f"NU1: rename into taken slot must return 409, got {r.status_code}"
    )
    assert r.get_json()["error"]["code"] == "name_conflict", (
        "NU1: rename collision must carry error.code='name_conflict'"
    )

    # Different parent, same name -> NOT a conflict (uniqueness is parent-scoped).
    client.post("/api/folders", json={"parent": "Beta", "name": "Mod"})
    assert (root / "Alpha" / "Mod").is_dir() and (root / "Beta" / "Mod").is_dir(), (
        "NU1: same-name folders under different parents must coexist (parent-scoped uniqueness)"
    )
print("PASS  NU1: duplicate folder in same parent -> 409 with error.code='name_conflict'")


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()

    # --- NU2: folder "X" and file "X.feature" coexist (different leaf names) ---
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})

    # File first: POST /api/files with file_name="X" -> auto-appends .feature.
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "X",
              "scenario_name": "seed", "description": "seed"},
    )
    assert r.status_code == 201, (
        f"NU2 setup: create file Alpha/Mod/X.feature must return 201, got {r.status_code}"
    )
    file_path = root / "Alpha" / "Mod" / "X.feature"
    assert file_path.is_file(), "NU2 setup: file Alpha/Mod/X.feature must exist on disk"

    # Folder with the same logical leaf "X" (no .feature suffix) -> coexists.
    r = client.post("/api/folders", json={"parent": "Alpha/Mod", "name": "X"})
    assert r.status_code == 201, (
        f"NU2: folder 'X' must coexist with file 'X.feature' in same parent; "
        f"POST returned {r.status_code} body={r.get_data(as_text=True)!r}"
    )
    folder_path = root / "Alpha" / "Mod" / "X"
    assert folder_path.is_dir(), "NU2: folder Alpha/Mod/X must exist after coexistence POST"
    assert file_path.is_file(), "NU2: pre-existing file Alpha/Mod/X.feature must still exist"

    # Reverse order also works: folder first, then file.
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod2"})
    r = client.post("/api/folders", json={"parent": "Alpha/Mod2", "name": "Y"})
    assert r.status_code == 201, "NU2 setup: folder Y must be created"
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod2", "file_name": "Y",
              "scenario_name": "seed", "description": "seed"},
    )
    assert r.status_code == 201, (
        f"NU2: file 'Y.feature' must coexist with pre-existing folder 'Y'; "
        f"POST returned {r.status_code}"
    )
    assert (root / "Alpha" / "Mod2" / "Y").is_dir()
    assert (root / "Alpha" / "Mod2" / "Y.feature").is_file()
print("PASS  NU2: folder 'X' and file 'X.feature' coexist (resolved paths differ via extension)")
