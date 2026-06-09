# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / FL3 -- no generic folders under the typed area.

FL3: the typed area is exactly two levels (group + run file). The
     generic folder API rejects any folder whose path passes through
     `test-run` at depth 2 -- both a would-be group
     (`<project>/test-run/<group>`) and anything nested below a real
     group (`<project>/test-run/<group>/<sub>`) -> HTTP 409. Groups are
     created only via the dedicated run-group API.

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
    s.create_run_group("Alpha", "release-1")  # real group exists on disk
    client = app.test_client()

    def mkfolder(name, parent):
        return client.post("/api/folders", data=json.dumps({"name": name, "parent": parent}),
                           content_type="application/json")

    # --- FL3: a would-be group via the generic API -> 409. ---
    r = mkfolder("release-2", "Alpha/test-run")
    assert r.status_code == 409, (r.status_code, r.get_data(as_text=True))
    assert r.get_json()["error"]["code"] == "name_conflict"
    assert not (root / "Alpha" / "test-run" / "release-2").exists()

    # --- FL3: nesting below an existing group -> 409. ---
    r2 = mkfolder("sub", "Alpha/test-run/release-1")
    assert r2.status_code == 409, (r2.status_code, r2.get_data(as_text=True))
    assert r2.get_json()["error"]["code"] == "name_conflict"
    assert not (root / "Alpha" / "test-run" / "release-1" / "sub").exists()

print("PASS  FL3: generic folder creates under <project>/test-run/... are rejected (409) -- area is exactly group+run")
