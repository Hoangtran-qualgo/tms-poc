# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / FL1 + FL2 -- depth-2 reservation.

FL1: creating a depth-2 folder named `test-run` via the generic folder
     API is rejected with NameConflictError -> HTTP 409. The typed area
     can only be materialised via the dedicated run/group methods.
FL2: the reservation applies at depth 2 ONLY -- `test-run` is a legal
     name deeper in the tree (e.g. Alpha/Checkout/test-run succeeds and
     carries no special meaning).

Exercised end-to-end through POST /api/folders.
"""
import json
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    client = app.test_client()

    def mkfolder(name, parent):
        return client.post("/api/folders", data=json.dumps({"name": name, "parent": parent}),
                           content_type="application/json")

    # --- FL1: depth-2 test-run via the generic API -> 409 name_conflict. ---
    r = mkfolder("test-run", "Alpha")
    assert r.status_code == 409, (r.status_code, r.get_data(as_text=True))
    env = r.get_json()["error"]
    assert env["code"] == "name_conflict", env
    assert not (root / "Alpha" / "test-run").exists(), (
        "the rejected create must not have made the reserved folder"
    )

    # --- FL2: test-run at depth 3 is allowed. ---
    r2 = mkfolder("test-run", "Alpha/Checkout")
    assert r2.status_code == 201, (r2.status_code, r2.get_data(as_text=True))
    assert (root / "Alpha" / "Checkout" / "test-run").is_dir(), (
        "test-run must be a legal ordinary folder name below depth 2"
    )

print("PASS  FL1+FL2: depth-2 'test-run' rejected (409); 'test-run' at depth 3 allowed")
