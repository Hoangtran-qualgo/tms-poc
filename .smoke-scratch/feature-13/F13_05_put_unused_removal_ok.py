"""S2 smoke — PUT removing an UNused key succeeds (D3 boundary).

The in-use guard must only block keys a feature actually references; a key
no case selects can be removed freely.

Asserts:
1. With components: {login, signup} and one case using `login`, a PUT that
   drops `signup` (unused) → 200; the vocab ends with only `login`.
2. The still-referenced `login` survives and the case still resolves.
"""
import pathlib
import tempfile

from app import create_app
from app.storage import Storage


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["P"])
    s.write_project_enums("P", {"components": {"login": "Login", "signup": "Sign up"}})
    s.create_file(["P", "a.feature"], "desc")
    feat = s.read_feature(["P", "a.feature"])
    feat.enums["components"] = "login"
    s.write_feature(["P", "a.feature"], feat)

    c = create_app(data_root=root).test_client()
    r = c.put("/api/enums/P", json={"components": {"login": "Login"}})
    assert r.status_code == 200, (r.status_code, r.get_json())
    assert r.get_json() == {"components": {"login": "Login"}}, r.get_json()
    print("PASS  Removing an unused key → 200; in-use key survives")

    # The referencing case still resolves against the surviving key.
    again = create_app(data_root=root).test_client()
    assert again.get("/api/enums/P").get_json() == {"components": {"login": "Login"}}
    print("PASS  Surviving vocab still resolves the referencing case")
