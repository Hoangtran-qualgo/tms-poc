# Pattern: see .smoke-scratch/README.md
"""feature-05 / testcase-crud / Idempotence (ID1)."""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})

    # --- ID1: DELETE /api/files/<p> idempotent on missing target ----------
    # 1. Never-existed file.
    r = client.delete("/api/files/Alpha/Mod/never.feature")
    assert r.status_code == 204, (
        f"ID1: DELETE never-existed file must return 204, got {r.status_code}"
    )
    assert r.get_data(as_text=True) == "", "ID1: 204 body must be empty"

    # 2. Never-existed file under never-existed parent.
    r = client.delete("/api/files/Nope/Missing/ghost.feature")
    assert r.status_code == 204, (
        f"ID1: DELETE missing-everything path must return 204, got {r.status_code}"
    )
    assert r.get_data(as_text=True) == "", "ID1: missing-everything body must be empty"

    # 3. Existed-then-deleted: second DELETE must also be 204.
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "real", "description": "x"},
    )
    real_path = root / "Alpha" / "Mod" / "real.feature"
    assert real_path.is_file(), "ID1 setup: file must exist before first DELETE"

    r1 = client.delete("/api/files/Alpha/Mod/real.feature")
    assert r1.status_code == 204, f"ID1 setup: first DELETE must return 204, got {r1.status_code}"
    assert not real_path.exists(), "ID1 setup: first DELETE must remove the file"

    r2 = client.delete("/api/files/Alpha/Mod/real.feature")
    assert r2.status_code == 204, (
        f"ID1: second DELETE of same path must return 204 (idempotent), got {r2.status_code}"
    )
    assert r2.get_data(as_text=True) == "", "ID1: idempotent second-DELETE body must be empty"
print(
    "PASS  ID1: DELETE /api/files/<p> returns 204 on missing target "
    "(never-existed, missing-everything, already-deleted)"
)
