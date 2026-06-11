"""S4 smoke — POST /api/enums/<project>/clear is blocked while in use (D11).

Clear follows the same block rule as D3: if any case still references the
vocab, it returns 409 with a detailed message and leaves the file unchanged.

Asserts:
1. Clear with an in-use enum → 409 enum_in_use; message names the case and
   instructs clearing it in the test case first; details carry kind/key.
2. The on-disk vocabulary is untouched.
3. Legacy project (no file) → 404.
"""
import pathlib
import tempfile

from app import create_app
from app.storage import Storage


# --- 1 + 2. Clear blocked while in use ------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["P"])
    s.write_project_enums("P", {"components": {"login": "Login"}})
    s.create_file(["P", "a.feature"], "desc")
    feat = s.read_feature(["P", "a.feature"])
    feat.enums["components"] = "login"
    s.write_feature(["P", "a.feature"], feat)
    before = (root / "P" / "enums.yaml").read_bytes()

    c = create_app(data_root=root).test_client()
    r = c.post("/api/enums/P/clear")
    assert r.status_code == 409, (r.status_code, r.get_json())
    err = r.get_json()["error"]
    assert err["code"] == "enum_in_use", err
    assert err["details"]["kind"] == "components" and err["details"]["key"] == "login"
    assert "Cannot clear" in err["message"], err
    assert "clear that enum in the test case" in err["message"], err
    assert (root / "P" / "enums.yaml").read_bytes() == before
    assert s.read_project_enums("P") == {"components": {"login": "Login"}}
    print("PASS  Clear while in use → 409 enum_in_use; file unchanged")

# --- 3. Legacy project → 404 ----------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    (root / "Legacy").mkdir()
    c = create_app(data_root=root).test_client()
    r = c.post("/api/enums/Legacy/clear")
    assert r.status_code == 404, (r.status_code, r.get_json())
    assert r.get_json()["error"]["code"] == "not_found"
    print("PASS  Clear on legacy project → 404 not_found")
