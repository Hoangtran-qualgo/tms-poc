# Pattern: see .smoke-scratch/README.md
"""feature-04 / folder-crud / Depth invariants (DR1-DR2).

Route-layer assertions only; the storage-half of DR1 (depth limit on
`Storage.create_folder`) lives in feature-02's F02_02_depth_rules.py.
"""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()

    # --- DR1: POST /api/folders accepts 1 <= depth <= 10 -------------------
    # Build depth 1 (project) through depth 10 (sub-folder) sequentially.
    segments: list[str] = []
    for i in range(1, 11):
        name = f"d{i}"
        parent = "/".join(segments)
        r = client.post("/api/folders", json={"parent": parent, "name": name})
        assert r.status_code == 201, (
            f"DR1: POST at depth {i} must return 201, got {r.status_code} "
            f"body={r.get_data(as_text=True)!r}"
        )
        segments.append(name)
        target = root.joinpath(*segments)
        assert target.is_dir(), f"DR1: depth-{i} folder must exist on disk after POST"

    # Depth 11 must be rejected as bad_request.
    parent = "/".join(segments)  # currently depth 10
    r = client.post("/api/folders", json={"parent": parent, "name": "d11"})
    assert r.status_code == 400, (
        f"DR1: POST at depth 11 must return 400, got {r.status_code}"
    )
    body = r.get_json()
    assert body and body.get("error", {}).get("code") == "bad_request", (
        f"DR1: depth-11 rejection must carry error.code='bad_request', got {body!r}"
    )
    assert not root.joinpath(*segments, "d11").exists(), (
        "DR1: depth-11 folder must NOT be created on disk"
    )
print("PASS  DR1: POST /api/folders accepts depth 1..10; depth 11 -> 400 bad_request")


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()

    # --- DR2: PATCH and DELETE accept any depth >= 1 -----------------------
    # Seed a depth-5 chain via POST (DR1-compliant).
    segments: list[str] = []
    for i in range(1, 6):
        name = f"d{i}"
        client.post("/api/folders", json={"parent": "/".join(segments), "name": name})
        segments.append(name)

    # Names chosen to avoid case-only collisions on case-insensitive
    # filesystems (macOS HFS+/APFS default treats `d1` and `D1` as
    # the same path -> NameConflictError 409). Each rename target is
    # a distinct token, not a case-fold of the source.
    # PATCH at depth 1 (project).
    r = client.patch("/api/folders/d1", json={"name": "proj"})
    assert r.status_code == 200, (
        f"DR2: PATCH at depth 1 must return 200, got {r.status_code}"
    )
    assert (root / "proj" / "d2" / "d3" / "d4" / "d5").is_dir(), (
        "DR2: depth-1 rename must move the whole subtree intact"
    )

    # PATCH at depth 5 (deep leaf) -- the spec says rename accepts ANY depth.
    r = client.patch("/api/folders/proj/d2/d3/d4/d5", json={"name": "leaf"})
    assert r.status_code == 200, (
        f"DR2: PATCH at depth 5 must return 200, got {r.status_code}"
    )
    assert (root / "proj" / "d2" / "d3" / "d4" / "leaf").is_dir(), (
        "DR2: depth-5 rename must move only the leaf"
    )

    # PATCH at depth 3 (mid).
    r = client.patch("/api/folders/proj/d2/d3", json={"name": "mid"})
    assert r.status_code == 200, (
        f"DR2: PATCH at depth 3 must return 200, got {r.status_code}"
    )

    # DELETE at depth 5 (leaf).
    r = client.delete("/api/folders/proj/d2/mid/d4/leaf")
    assert r.status_code == 204, (
        f"DR2: DELETE at depth 5 must return 204, got {r.status_code}"
    )
    assert not (root / "proj" / "d2" / "mid" / "d4" / "leaf").exists(), (
        "DR2: depth-5 delete must remove the leaf"
    )

    # DELETE at depth 1 (project) -- recursive on remaining mid + descendants.
    r = client.delete("/api/folders/proj")
    assert r.status_code == 204, (
        f"DR2: DELETE at depth 1 must return 204, got {r.status_code}"
    )
    assert not (root / "proj").exists(), "DR2: depth-1 delete must remove the project"
print("PASS  DR2: PATCH and DELETE /api/folders/<p> accept any depth >= 1")
