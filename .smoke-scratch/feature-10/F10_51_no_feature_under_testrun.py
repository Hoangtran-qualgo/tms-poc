# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / FL4 -- no .feature files under the typed area.

FL4: creating a `.feature` file anywhere under `<project>/test-run/`
     via the generic file API is rejected -> HTTP 409 (the reserved
     typed-area guard fires on `segments[1] == "test-run"` before any
     extension handling).

Exercised end-to-end through POST /api/files.
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
    s.create_run_group("Alpha", "release-1")
    client = app.test_client()

    def mkfile(name, parent):
        return client.post("/api/files", data=json.dumps(
            {"file_name": name, "parent": parent, "description": "d"}),
            content_type="application/json")

    # --- FL4: .feature inside a real group -> 409 name_conflict. ---
    r = mkfile("case.feature", "Alpha/test-run/release-1")
    assert r.status_code == 409, (r.status_code, r.get_data(as_text=True))
    assert r.get_json()["error"]["code"] == "name_conflict"
    assert not (root / "Alpha" / "test-run" / "release-1" / "case.feature").exists()

    # --- FL4: .feature directly under test-run/ -> 409 too. ---
    r2 = mkfile("case.feature", "Alpha/test-run")
    assert r2.status_code == 409, (r2.status_code, r2.get_data(as_text=True))
    assert r2.get_json()["error"]["code"] == "name_conflict"

print("PASS  FL4: .feature creation anywhere under <project>/test-run/ is rejected (409)")
