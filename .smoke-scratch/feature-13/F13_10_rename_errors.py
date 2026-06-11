"""S3 smoke — rename validation / conflict error branches.

Asserts:
1. new_key already exists in the kind → 409 name_conflict; file + features
   unchanged.
2. Unknown old_key → 422 validation_error.
3. Invalid new_key identifier → 422 validation_error.
4. Legacy project (no enums.yaml) → 404 not_found.
"""
import pathlib
import tempfile

from app import create_app
from app.storage import Storage


def _client(root: pathlib.Path):
    return create_app(data_root=root).test_client()


# --- 1. new_key conflict → 409, nothing changes ---------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["P"])
    s.write_project_enums("P", {"components": {"login": "Login", "signin": "Sign in"}})
    s.create_file(["P", "a.feature"], "desc")
    feat = s.read_feature(["P", "a.feature"])
    feat.enums["components"] = "login"
    s.write_feature(["P", "a.feature"], feat)
    enums_before = (root / "P" / "enums.yaml").read_bytes()

    r = _client(root).post("/api/enums/P/rename", json={
        "kind": "components", "old_key": "login", "new_key": "signin",
    })
    assert r.status_code == 409, (r.status_code, r.get_json())
    assert r.get_json()["error"]["code"] == "name_conflict", r.get_json()
    assert (root / "P" / "enums.yaml").read_bytes() == enums_before
    assert s.read_feature(["P", "a.feature"]).enums["components"] == "login"
    print("PASS  rename onto an existing key → 409 name_conflict; unchanged")

# --- 2. Unknown old_key → 422 ---------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["P"])
    s.write_project_enums("P", {"components": {"login": "Login"}})
    r = _client(root).post("/api/enums/P/rename", json={
        "kind": "components", "old_key": "nope", "new_key": "signin",
    })
    assert r.status_code == 422, (r.status_code, r.get_json())
    assert r.get_json()["error"]["code"] == "validation_error", r.get_json()
    print("PASS  rename unknown old_key → 422 validation_error")

# --- 3. Invalid new_key identifier → 422 ----------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["P"])
    s.write_project_enums("P", {"components": {"login": "Login"}})
    r = _client(root).post("/api/enums/P/rename", json={
        "kind": "components", "old_key": "login", "new_key": "bad.key",
    })
    assert r.status_code == 422, (r.status_code, r.get_json())
    assert r.get_json()["error"]["code"] == "validation_error", r.get_json()
    print("PASS  rename to an invalid new_key → 422 validation_error")

# --- 4. Legacy project → 404 ----------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    (root / "Legacy").mkdir()
    r = _client(root).post("/api/enums/Legacy/rename", json={
        "kind": "components", "old_key": "login", "new_key": "signin",
    })
    assert r.status_code == 404, (r.status_code, r.get_json())
    assert r.get_json()["error"]["code"] == "not_found", r.get_json()
    print("PASS  rename on legacy project → 404 not_found")
