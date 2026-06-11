"""S3 smoke — rename dry-run aborts (no writes) on an unparseable feature.

The dry-run parses every feature BEFORE any write; if one cannot be parsed
the whole rename aborts with no side effects.

Asserts:
1. rename → 422 parse_error when a feature in the project is malformed.
2. enums.yaml is byte-for-byte unchanged.
3. The valid referencing feature still selects old_key (not rewritten).
"""
import pathlib
import tempfile

from app import create_app
from app.storage import Storage


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["P"])
    s.write_project_enums("P", {"components": {"login": "Login"}})
    s.create_file(["P", "a.feature"], "desc")
    feat = s.read_feature(["P", "a.feature"])
    feat.enums["components"] = "login"
    s.write_feature(["P", "a.feature"], feat)
    # A malformed .feature (no Feature header) written straight to disk.
    (root / "P" / "bad.feature").write_text(
        "Scenario: orphan\n  Given a step\n", encoding="utf-8"
    )

    enums_before = (root / "P" / "enums.yaml").read_bytes()
    a_before = (root / "P" / "a.feature").read_bytes()

    c = create_app(data_root=root).test_client()
    r = c.post("/api/enums/P/rename", json={
        "kind": "components", "old_key": "login", "new_key": "signin",
    })
    assert r.status_code == 422, (r.status_code, r.get_json())
    assert r.get_json()["error"]["code"] == "parse_error", r.get_json()
    print("PASS  rename with an unparseable feature → 422 parse_error")

    assert (root / "P" / "enums.yaml").read_bytes() == enums_before
    assert (root / "P" / "a.feature").read_bytes() == a_before
    assert s.read_feature(["P", "a.feature"]).enums["components"] == "login"
    print("PASS  dry-run abort leaves enums.yaml + the valid feature unchanged")
