# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / FL5 -- no .yaml via the generic file API.

FL5: `.yaml` is never written outside `<project>/test-run/<group>/`.
     The generic file API only accepts `.feature` leaves
     (`_normalize_filename` rejects any other extension), so a `.yaml`
     create attempt in an ordinary module is rejected -> HTTP 400
     bad_request. The run-write path is therefore the *only* `.yaml`
     writer and cannot collide with the `.feature` writers.

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
    s.create_folder(["Alpha", "Checkout"])
    client = app.test_client()

    # --- FL5: a .yaml leaf via the generic file API -> 400 bad_request. ---
    r = client.post("/api/files", data=json.dumps(
        {"file_name": "rogue.yaml", "parent": "Alpha/Checkout", "description": "d"}),
        content_type="application/json")
    assert r.status_code == 400, (r.status_code, r.get_data(as_text=True))
    env = r.get_json()["error"]
    assert env["code"] == "bad_request", env
    assert ".feature" in env["message"], env["message"]
    assert not (root / "Alpha" / "Checkout" / "rogue.yaml").exists()

print("PASS  FL5: .yaml cannot be created via the generic file API (400) -- run-write path is the only .yaml writer")
