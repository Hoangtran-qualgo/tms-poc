"""S2 smoke — PUT /api/enums/<project> whole-document replace.

Asserts:
1. PUT replaces the document (add kinds + entries) → 200 with parsed body;
   subsequent GET returns the same.
2. PUT can edit a label and remove an (unused) kind → 200.
3. PUT on a legacy project (no enums.yaml) → 404 not_found.
4. PUT with a schema-invalid payload (bad key identifier) → 422
   enums_parse_error, file unchanged.
"""
import pathlib
import tempfile

from app import create_app
from app.storage import Storage


def _client(td: pathlib.Path):
    return create_app(data_root=td).test_client()


# --- 1. PUT replaces, GET round-trips -------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    Storage(root).create_folder(["P"])  # auto-init {components: {}}
    c = _client(root)
    payload = {
        "components": {"login": "Login", "signup": "Sign up"},
        "priorities": {"p0": "Blocker"},
    }
    r = c.put("/api/enums/P", json=payload)
    assert r.status_code == 200, (r.status_code, r.get_json())
    assert r.get_json() == payload, r.get_json()
    assert c.get("/api/enums/P").get_json() == payload
    print("PASS  PUT replaces document; GET returns the same")

# --- 2. PUT edits a label + removes an unused kind ------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    Storage(root).create_folder(["P"])
    c = _client(root)
    c.put("/api/enums/P", json={
        "components": {"login": "Login"},
        "priorities": {"p0": "Blocker"},
    })
    r = c.put("/api/enums/P", json={"components": {"login": "Login by credential"}})
    assert r.status_code == 200, (r.status_code, r.get_json())
    assert r.get_json() == {"components": {"login": "Login by credential"}}, r.get_json()
    print("PASS  PUT edits label + drops an unused kind → 200")

# --- 3. PUT on a legacy project → 404 -------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    (root / "Legacy").mkdir()  # no auto-init
    c = _client(root)
    r = c.put("/api/enums/Legacy", json={"components": {}})
    assert r.status_code == 404, (r.status_code, r.get_json())
    assert r.get_json()["error"]["code"] == "not_found"
    print("PASS  PUT on legacy project (no file) → 404 not_found")

# --- 4. PUT schema-invalid payload → 422, file unchanged ------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    Storage(root).create_folder(["P"])
    target = root / "P" / "enums.yaml"
    before = target.read_bytes()
    c = _client(root)
    r = c.put("/api/enums/P", json={"components": {"bad.key": "Bad"}})
    assert r.status_code == 422, (r.status_code, r.get_json())
    assert r.get_json()["error"]["code"] == "enums_parse_error"
    assert target.read_bytes() == before, "file changed despite 422"
    print("PASS  PUT schema-invalid → 422 enums_parse_error, file unchanged")
