# Pattern: see .smoke-scratch/README.md
"""feature-04 / folder-crud / HTTP routes (HR1-HR3)."""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()

    # --- HR1: POST /api/folders with parent default + explicit -------------
    # Parent omitted entirely -> defaults to "" (root).
    r = client.post("/api/folders", json={"name": "Alpha"})
    assert r.status_code == 201, (
        f"HR1: POST /api/folders without parent must return 201, got {r.status_code} body={r.get_data(as_text=True)!r}"
    )
    assert r.get_json() == {"ok": True}, (
        f"HR1: POST /api/folders success body must be {{'ok': True}}, got {r.get_json()!r}"
    )
    assert (root / "Alpha").is_dir(), "HR1: parent='' default must create folder at the data root"

    # Parent provided as empty string -> still root.
    r = client.post("/api/folders", json={"parent": "", "name": "Beta"})
    assert r.status_code == 201, f"HR1: POST with parent='' must return 201, got {r.status_code}"
    assert (root / "Beta").is_dir(), "HR1: parent='' explicit must create folder at the data root"

    # Parent provided -> creates parent + [name].
    r = client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    assert r.status_code == 201, f"HR1: POST with parent='Alpha' must return 201, got {r.status_code}"
    assert r.get_json() == {"ok": True}, "HR1: POST success body must be {'ok': True}"
    assert (root / "Alpha" / "Mod").is_dir(), (
        "HR1: POST with parent='Alpha' name='Mod' must create Alpha/Mod"
    )
print("PASS  HR1: POST /api/folders {name, parent?} -> 201 {ok: true}; parent defaults to '' (root)")


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})

    # --- HR2: PATCH /api/folders/<path:p> {name} -> rename within parent ---
    # Depth-1 rename (project).
    r = client.patch("/api/folders/Alpha", json={"name": "Gamma"})
    assert r.status_code == 200, (
        f"HR2: PATCH /api/folders/Alpha must return 200, got {r.status_code} body={r.get_data(as_text=True)!r}"
    )
    assert r.get_json() == {"ok": True}, (
        f"HR2: rename success body must be {{'ok': True}}, got {r.get_json()!r}"
    )
    assert not (root / "Alpha").exists(), "HR2: source folder must be gone after rename"
    assert (root / "Gamma").is_dir(), "HR2: target folder must exist after rename"
    # Children must follow the rename (same-parent rename = directory move).
    assert (root / "Gamma" / "Mod").is_dir(), "HR2: child folder must follow the parent rename"

    # Depth-2 rename (module under project) -- same-parent only by construction.
    r = client.patch("/api/folders/Gamma/Mod", json={"name": "Renamed"})
    assert r.status_code == 200, f"HR2: depth-2 PATCH must return 200, got {r.status_code}"
    assert (root / "Gamma" / "Renamed").is_dir(), (
        "HR2: depth-2 rename must occupy <parent of p>/<name>"
    )
    assert not (root / "Gamma" / "Mod").exists(), "HR2: depth-2 source must be gone after rename"
print("PASS  HR2: PATCH /api/folders/<p> {name} -> 200 {ok: true}; renames within same parent")


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    (root / "Alpha" / "Mod" / "leaf").mkdir()

    # --- HR3: DELETE /api/folders/<path:p> -> 204 "" (recursive, idempotent) ---
    # Existing folder with descendants.
    r = client.delete("/api/folders/Alpha")
    assert r.status_code == 204, (
        f"HR3: DELETE existing folder must return 204, got {r.status_code} body={r.get_data(as_text=True)!r}"
    )
    assert r.get_data(as_text=True) == "", (
        f"HR3: DELETE success body must be '', got {r.get_data(as_text=True)!r}"
    )
    assert not (root / "Alpha").exists(), "HR3: target folder must be gone after delete"

    # Idempotent on missing target.
    r = client.delete("/api/folders/Alpha")
    assert r.status_code == 204, (
        f"HR3: DELETE missing folder must still return 204 (idempotent), got {r.status_code}"
    )
    assert r.get_data(as_text=True) == "", "HR3: idempotent DELETE body must be ''"

    # Never-existed nested path also 204.
    r = client.delete("/api/folders/never/seen/before")
    assert r.status_code == 204, (
        f"HR3: DELETE never-existed nested path must return 204, got {r.status_code}"
    )
print("PASS  HR3: DELETE /api/folders/<p> -> 204 '' (recursive; idempotent on missing target)")
