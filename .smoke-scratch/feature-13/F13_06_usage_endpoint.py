"""S2 smoke — GET /api/enums/<project>/usage?kind=&key=.

Asserts:
1. Count + sample reflect the referencing cases (and only those).
2. A key no case uses → count 0, empty sample.
3. Missing kind/key query param → 400 bad_request.
4. Legacy project (no enums.yaml) → 404 not_found.
"""
import pathlib
import tempfile

from app import create_app
from app.storage import Storage


def _setup(root: pathlib.Path) -> None:
    """components: {login, signup}; a+b use login, c uses nothing."""
    s = Storage(root)
    s.create_folder(["P"])
    s.write_project_enums("P", {"components": {"login": "Login", "signup": "Sign up"}})
    for name in ("a.feature", "b.feature"):
        s.create_file(["P", name], "desc")
        feat = s.read_feature(["P", name])
        feat.enums["components"] = "login"
        s.write_feature(["P", name], feat)
    s.create_file(["P", "c.feature"], "desc")  # no enum set


# --- 1. Count + sample for a referenced key -------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    _setup(root)
    c = create_app(data_root=root).test_client()
    r = c.get("/api/enums/P/usage?kind=components&key=login")
    assert r.status_code == 200, (r.status_code, r.get_json())
    body = r.get_json()
    assert body["count"] == 2, body
    assert len(body["sample"]) == 2, body
    assert all(p.endswith(".feature") for p in body["sample"]), body
    print("PASS  usage for referenced key → count 2 + 2 sample paths")

# --- 2. Unused key → count 0 ----------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    _setup(root)
    c = create_app(data_root=root).test_client()
    r = c.get("/api/enums/P/usage?kind=components&key=signup")
    assert r.status_code == 200, r.status_code
    assert r.get_json() == {"count": 0, "sample": []}, r.get_json()
    print("PASS  usage for unused key → count 0, empty sample")

# --- 3. Missing query param → 400 -----------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    _setup(root)
    c = create_app(data_root=root).test_client()
    r = c.get("/api/enums/P/usage?kind=components")
    assert r.status_code == 400, (r.status_code, r.get_json())
    assert r.get_json()["error"]["code"] == "bad_request"
    print("PASS  usage missing key param → 400 bad_request")

# --- 4. Legacy project → 404 ----------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    (root / "Legacy").mkdir()  # no auto-init
    c = create_app(data_root=root).test_client()
    r = c.get("/api/enums/Legacy/usage?kind=components&key=login")
    assert r.status_code == 404, (r.status_code, r.get_json())
    assert r.get_json()["error"]["code"] == "not_found"
    print("PASS  usage on legacy project → 404 not_found")
