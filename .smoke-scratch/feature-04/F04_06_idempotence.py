# Pattern: see .smoke-scratch/README.md
"""feature-04 / folder-crud / Idempotence (ID1)."""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()

    # --- ID1: DELETE /api/folders/<p> returns 204 even on missing target ---
    # 1. Never-existed depth-1 path.
    r = client.delete("/api/folders/never_existed")
    assert r.status_code == 204, (
        f"ID1: DELETE never-existed depth-1 path must return 204, got {r.status_code}"
    )
    assert r.get_data(as_text=True) == "", "ID1: 204 body must be empty"

    # 2. Never-existed deep path (parent chain also missing).
    r = client.delete("/api/folders/a/b/c/d/e")
    assert r.status_code == 204, (
        f"ID1: DELETE never-existed deep path must return 204, got {r.status_code}"
    )
    assert r.get_data(as_text=True) == "", "ID1: deep-path 204 body must be empty"

    # 3. Existed-then-deleted: second DELETE must also be 204 (true idempotence).
    client.post("/api/folders", json={"name": "Alpha"})
    r1 = client.delete("/api/folders/Alpha")
    assert r1.status_code == 204, (
        f"ID1 setup: first DELETE must return 204, got {r1.status_code}"
    )
    assert not (root / "Alpha").exists(), "ID1 setup: first DELETE must remove the folder"

    r2 = client.delete("/api/folders/Alpha")
    assert r2.status_code == 204, (
        f"ID1: second DELETE of same path must return 204 (idempotent), got {r2.status_code}"
    )
    assert r2.get_data(as_text=True) == "", "ID1: idempotent second-DELETE body must be empty"

    # 4. Sibling missing-and-present in the same parent: missing -> 204,
    #    present -> 204; behaviour is the same on the wire either way.
    client.post("/api/folders", json={"name": "Beta"})
    client.post("/api/folders", json={"parent": "Beta", "name": "real"})
    r_real = client.delete("/api/folders/Beta/real")
    r_fake = client.delete("/api/folders/Beta/fake")
    assert r_real.status_code == 204, "ID1: existing-target DELETE returns 204"
    assert r_fake.status_code == 204, "ID1: missing-target DELETE returns 204 (same wire)"
print(
    "PASS  ID1: DELETE /api/folders/<p> returns 204 on missing target "
    "(idempotent across never-existed, deep, and already-deleted paths)"
)
