"""S3.1 smoke — GET/POST /api/enums/<project> HTTP routes.

Asserts each status branch from the spec's HTTP surface section:

GET:
1. Legacy project (no enums.yaml)         → 404 not_found
2. Auto-initialised project (default file) → 200 with {"components": {}}
3. Project with hand-written multi-kind YAML → 200 with parsed dict
4. Malformed YAML                          → 422 enums_parse_error
                                             with details.line

POST:
5. Legacy project (no file)                → 201 with {"components": {}}
                                             body; bytes on disk match.
6. Already-initialised project             → 409 name_conflict
7. Missing project folder                  → 404 not_found
8. POST → subsequent GET returns same body (round-trip)
"""
import os
import pathlib
import tempfile

from app import create_app
from app.storage import Storage


def _client(td: pathlib.Path):
    app = create_app(data_root=td)
    return app, app.test_client()


# --- 1. GET on legacy project (no enums.yaml) ----------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    (root / "Legacy").mkdir()  # manual mkdir → no auto-init
    _, c = _client(root)
    r = c.get("/api/enums/Legacy")
    assert r.status_code == 404, (r.status_code, r.get_json())
    body = r.get_json()
    assert body["error"]["code"] == "not_found", body
    print("PASS  GET legacy project (no file) → 404 not_found")

# --- 2. GET on auto-initialised project ----------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["Alpha"])  # auto-init writes default
    _, c = _client(root)
    r = c.get("/api/enums/Alpha")
    assert r.status_code == 200, (r.status_code, r.get_json())
    assert r.get_json() == {"components": {}}, r.get_json()
    print("PASS  GET auto-initialised project → 200 {'components': {}}")

# --- 3. GET on hand-written multi-kind YAML ------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["Alpha"])
    (root / "Alpha" / "enums.yaml").write_bytes(
        b"components:\n"
        b"  - login: Login by credential\n"
        b"  - login_by_SSO: Login by SSO\n"
        b"priorities:\n"
        b"  - p0: Blocker\n"
    )
    _, c = _client(root)
    r = c.get("/api/enums/Alpha")
    assert r.status_code == 200, r.status_code
    assert r.get_json() == {
        "components": {
            "login": "Login by credential",
            "login_by_SSO": "Login by SSO",
        },
        "priorities": {"p0": "Blocker"},
    }, r.get_json()
    print("PASS  GET hand-written multi-kind YAML → 200 parsed dict")

# --- 4. GET on malformed YAML --------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["Alpha"])
    (root / "Alpha" / "enums.yaml").write_bytes(b"components: [unterminated\n")
    _, c = _client(root)
    r = c.get("/api/enums/Alpha")
    assert r.status_code == 422, r.status_code
    body = r.get_json()
    assert body["error"]["code"] == "enums_parse_error", body
    assert body["error"]["details"]["line"] >= 1, body
    print("PASS  GET malformed YAML → 422 enums_parse_error with line")

# --- 5. POST on legacy project -------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    (root / "Legacy").mkdir()
    _, c = _client(root)
    r = c.post("/api/enums/Legacy")
    assert r.status_code == 201, (r.status_code, r.get_json())
    assert r.get_json() == {"components": {}}, r.get_json()
    assert (root / "Legacy" / "enums.yaml").read_bytes() == b"components:\n"
    print("PASS  POST legacy project → 201, default bytes on disk")

# --- 6. POST on already-initialised project ------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["Alpha"])  # already has enums.yaml
    _, c = _client(root)
    r = c.post("/api/enums/Alpha")
    assert r.status_code == 409, (r.status_code, r.get_json())
    body = r.get_json()
    assert body["error"]["code"] == "name_conflict", body
    assert "enums.yaml" in body["error"]["message"], body
    print("PASS  POST already-initialised project → 409 name_conflict")

# --- 7. POST on missing project folder -----------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    _, c = _client(root)
    r = c.post("/api/enums/Nope")
    assert r.status_code == 404, (r.status_code, r.get_json())
    body = r.get_json()
    assert body["error"]["code"] == "not_found", body
    print("PASS  POST missing project folder → 404 not_found")

# --- 8. POST → GET round-trip -------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    (root / "Legacy").mkdir()
    _, c = _client(root)
    init_body = c.post("/api/enums/Legacy").get_json()
    get_body = c.get("/api/enums/Legacy").get_json()
    assert init_body == get_body == {"components": {}}, (init_body, get_body)
    print("PASS  POST → GET round-trip returns identical body")
