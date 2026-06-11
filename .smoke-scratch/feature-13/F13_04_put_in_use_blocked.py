"""S2 smoke — PUT removing an in-use key/kind is blocked (D3).

Asserts:
1. Removing a referenced key → 409 enum_in_use with {kind, key, count,
   sample} details and a message naming the case; file unchanged.
2. Removing the whole referenced kind → 409 (same guard).
3. The blocked write leaves the on-disk vocab untouched.
"""
import pathlib
import tempfile

from app import create_app
from app.storage import Storage


def _setup(root: pathlib.Path) -> Storage:
    """Project P with components: {login, signup}; two cases select login."""
    s = Storage(root)
    s.create_folder(["P"])
    s.write_project_enums("P", {"components": {"login": "Login", "signup": "Sign up"}})
    for name in ("a.feature", "b.feature"):
        s.create_file(["P", name], "desc")
        feat = s.read_feature(["P", name])
        feat.enums["components"] = "login"
        s.write_feature(["P", name], feat)
    return s


# --- 1. Removing the in-use key → 409 + details ---------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    _setup(root)
    target = root / "P" / "enums.yaml"
    before = target.read_bytes()
    c = create_app(data_root=root).test_client()
    r = c.put("/api/enums/P", json={"components": {"signup": "Sign up"}})
    assert r.status_code == 409, (r.status_code, r.get_json())
    err = r.get_json()["error"]
    assert err["code"] == "enum_in_use", err
    assert err["details"]["kind"] == "components", err
    assert err["details"]["key"] == "login", err
    assert err["details"]["count"] == 2, err
    assert len(err["details"]["sample"]) == 2, err
    assert "in use by test case" in err["message"], err
    assert target.read_bytes() == before, "file changed despite 409"
    print("PASS  Removing in-use key → 409 enum_in_use with details; file unchanged")

# --- 2. Removing the whole in-use kind → 409 ------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    _setup(root)
    c = create_app(data_root=root).test_client()
    r = c.put("/api/enums/P", json={})  # drops the components kind entirely
    assert r.status_code == 409, (r.status_code, r.get_json())
    assert r.get_json()["error"]["details"]["key"] == "login"
    print("PASS  Removing whole in-use kind → 409 enum_in_use")
