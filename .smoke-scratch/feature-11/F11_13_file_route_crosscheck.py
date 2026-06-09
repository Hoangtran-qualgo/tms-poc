# Pattern: see .smoke-scratch/README.md
"""feature-11 / enums / HT9 -- enum cross-check via the file routes.

HT9: the storage enum cross-check fires through the HTTP file-write
     routes (not just direct `write_feature`):
       - `PATCH /api/files/<p>` with a Feature dict carrying a bad enum
         key → 422 `validation_error`, field `enums[<kind>]`;
       - `PUT /api/files/<p>/raw` with a `# enum.<kind>: <bad>` header →
         422 `validation_error`;
     and a rejected write leaves the on-disk file unchanged.
"""
import json
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])           # auto-inits an (empty) enums.yaml
    s.create_folder(["Alpha", "M"])
    s.create_file(["Alpha", "M", "a.feature"], "desc")
    # Give the project a real components vocabulary.
    (root / "Alpha" / "enums.yaml").write_text(
        "components:\n  - login: Login by credential\n", encoding="utf-8")

    client = app.test_client()
    p = "/api/files/Alpha/M/a.feature"
    feat = client.get(p).get_json()
    raw_before = client.get(p + "/raw").get_data(as_text=True)

    # --- HT9: PATCH with a known-good enum key → 200. ---
    good = dict(feat, enums={"components": "login"})
    assert client.patch(p, data=json.dumps(good),
                        content_type="application/json").status_code == 200

    # --- HT9: PATCH with an unknown key → 422 validation_error @ enums[components]. ---
    bad = dict(feat, enums={"components": "bogus"})
    r = client.patch(p, data=json.dumps(bad), content_type="application/json")
    assert r.status_code == 422, (r.status_code, r.get_data(as_text=True))
    env = r.get_json()["error"]
    assert env["code"] == "validation_error", env
    assert env["details"]["field"] == "enums[components]", env["details"]

    # --- HT9: PUT raw with a bad header → 422, file unchanged. ---
    # (reset the file to the clean baseline first so we measure the raw PUT alone)
    client.patch(p, data=json.dumps(dict(feat, enums={})),
                 content_type="application/json")
    clean_raw = client.get(p + "/raw").get_data(as_text=True)
    bad_raw = "# enum.components: bogus\n" + clean_raw
    r2 = client.put(p + "/raw", data=bad_raw, content_type="text/plain")
    assert r2.status_code == 422, (r2.status_code, r2.get_data(as_text=True))
    assert r2.get_json()["error"]["code"] == "validation_error"
    assert client.get(p + "/raw").get_data(as_text=True) == clean_raw, (
        "a rejected raw write must leave the on-disk file unchanged"
    )

print("PASS  HT9: enum cross-check rejects bad keys via PATCH /api/files + PUT .../raw (422); file unchanged")
