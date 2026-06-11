"""S4 smoke — Clear succeeds (resets to seed) once nothing references the vocab.

Asserts:
1. With no case using any enum, POST .../clear → 200 {cleared: true}.
2. The file is reset to the default seed (`components:\n`) — not deleted (D8).
3. After clearing a case's enum, a previously-blocked clear now succeeds.
"""
import pathlib
import tempfile

from app import create_app
from app.storage import Storage
from app.storage._core import _ENUMS_DEFAULT_BYTES


# --- 1 + 2. Clear with nothing in use → reset to seed ---------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["P"])
    s.write_project_enums("P", {
        "components": {"login": "Login"},
        "priorities": {"p0": "Blocker"},
    })
    c = create_app(data_root=root).test_client()

    r = c.post("/api/enums/P/clear")
    assert r.status_code == 200, (r.status_code, r.get_json())
    assert r.get_json() == {"cleared": True}, r.get_json()
    assert (root / "P" / "enums.yaml").read_bytes() == _ENUMS_DEFAULT_BYTES
    assert s.read_project_enums("P") == {"components": {}}
    print("PASS  Clear with nothing in use → 200, file reset to seed (not deleted)")

# --- 3. Clearing the case's enum unblocks the clear -----------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["P"])
    s.write_project_enums("P", {"components": {"login": "Login"}})
    s.create_file(["P", "a.feature"], "desc")
    feat = s.read_feature(["P", "a.feature"])
    feat.enums["components"] = "login"
    s.write_feature(["P", "a.feature"], feat)
    c = create_app(data_root=root).test_client()

    assert c.post("/api/enums/P/clear").status_code == 409  # blocked first
    # Clear the enum on the case (set back to unset), then save.
    feat = s.read_feature(["P", "a.feature"])
    feat.enums["components"] = ""
    s.write_feature(["P", "a.feature"], feat)

    r = c.post("/api/enums/P/clear")
    assert r.status_code == 200, (r.status_code, r.get_json())
    assert (root / "P" / "enums.yaml").read_bytes() == _ENUMS_DEFAULT_BYTES
    print("PASS  clearing the case's enum unblocks Clear → 200, reset to seed")
