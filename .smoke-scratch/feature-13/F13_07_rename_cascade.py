"""S3 smoke — POST /api/enums/<project>/rename cascades across features (D4).

Asserts:
1. rename returns {renamed: N} = the number of referencing features.
2. The vocab ends with only new_key, taking old_key's slot (order + label
   preserved); other kinds untouched.
3. Every referencing feature now selects new_key.
4. A feature referencing a *different* kind/key is left untouched.
"""
import pathlib
import tempfile

from app import create_app
from app.storage import Storage


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["P"])
    s.write_project_enums("P", {
        "components": {"login": "Login by credential", "signup": "Sign up"},
        "priorities": {"p0": "Blocker"},
    })
    # a, b reference components=login; c references a different kind/key.
    for name in ("a.feature", "b.feature"):
        s.create_file(["P", name], "desc")
        feat = s.read_feature(["P", name])
        feat.enums["components"] = "login"
        s.write_feature(["P", name], feat)
    s.create_file(["P", "c.feature"], "desc")
    cfeat = s.read_feature(["P", "c.feature"])
    cfeat.enums["priorities"] = "p0"
    s.write_feature(["P", "c.feature"], cfeat)

    c = create_app(data_root=root).test_client()
    r = c.post("/api/enums/P/rename", json={
        "kind": "components", "old_key": "login", "new_key": "signin",
    })
    assert r.status_code == 200, (r.status_code, r.get_json())
    assert r.get_json() == {"renamed": 2}, r.get_json()
    print("PASS  rename returns {renamed: 2}")

    vocab = s.read_project_enums("P")
    assert vocab == {
        "components": {"signin": "Login by credential", "signup": "Sign up"},
        "priorities": {"p0": "Blocker"},
    }, vocab
    # new_key takes old_key's slot (first), order + label preserved.
    assert list(vocab["components"].keys()) == ["signin", "signup"], vocab
    assert list(vocab.keys()) == ["components", "priorities"], vocab
    print("PASS  vocab: signin replaces login in place; other kinds untouched")

    assert s.read_feature(["P", "a.feature"]).enums["components"] == "signin"
    assert s.read_feature(["P", "b.feature"]).enums["components"] == "signin"
    assert s.read_feature(["P", "c.feature"]).enums == {"priorities": "p0"}
    print("PASS  referencing features rewritten; unrelated feature untouched")
