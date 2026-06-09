# Pattern: see .smoke-scratch/README.md
"""feature-05 / testcase-crud / HTTP routes (HR1-HR9).

Drives each /api/files route via Flask test client against an isolated
tmp data root. Per Step-1 sign-off Q2, these HR* assertions also serve
as the route-half of SM1-SM9 (storage-method delegation rows).
"""
import pathlib
import tempfile

from app import create_app


def _make_app():
    td = tempfile.mkdtemp()
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    return app, root


# --- HR1: POST /api/files {file_name, description, parent} -----------------
app, root = _make_app()
client = app.test_client()
client.post("/api/folders", json={"name": "Alpha"})
client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})

r = client.post(
    "/api/files",
    json={"parent": "Alpha/Mod", "file_name": "case", "description": "seed desc"},
)
assert r.status_code == 201, (
    f"HR1: POST /api/files must return 201, got {r.status_code} body={r.get_data(as_text=True)!r}"
)
assert r.get_json() == {"ok": True}, (
    f"HR1: success body must be {{'ok': True}}, got {r.get_json()!r}"
)
assert (root / "Alpha" / "Mod" / "case.feature").is_file(), (
    "HR1: POST must create the .feature file on disk"
)

# Sub-folder parent (depth 3) also accepted (boundary inside 2..10).
client.post("/api/folders", json={"parent": "Alpha/Mod", "name": "Sub"})
r = client.post(
    "/api/files",
    json={"parent": "Alpha/Mod/Sub", "file_name": "deep", "description": "deep desc"},
)
assert r.status_code == 201, "HR1: depth-3 parent must be accepted"
print("PASS  HR1: POST /api/files {file_name, description, parent} -> 201 {ok: true}")


# --- HR2: GET /api/files/<p> -> Feature.to_dict() 200; non-.feature -> 415 ---
r = client.get("/api/files/Alpha/Mod/case.feature")
assert r.status_code == 200, (
    f"HR2: GET /api/files/<p> must return 200, got {r.status_code}"
)
body = r.get_json()
assert isinstance(body, dict), f"HR2: body must be a dict (Feature.to_dict()), got {type(body)}"
for key in ("description", "tags", "background", "scenario"):
    assert key in body, f"HR2: response must carry Feature key {key!r}, missing in {list(body)}"
assert body["description"] == "seed desc", (
    f"HR2: response.description must echo the seed value, got {body['description']!r}"
)

# Non-.feature extension -> 415 unsupported_type.
# Need an actual on-disk file with non-.feature ext; storage rejects this
# via normalisation, so create it directly under root via pathlib.
(root / "Alpha" / "Mod" / "junk.yaml").write_text("hello", encoding="utf-8")
r = client.get("/api/files/Alpha/Mod/junk.yaml")
assert r.status_code == 415, (
    f"HR2: GET non-.feature path must return 415, got {r.status_code}"
)
assert r.get_json()["error"]["code"] == "unsupported_type", (
    f"HR2: non-.feature must carry error.code='unsupported_type', got {r.get_json()!r}"
)
print("PASS  HR2: GET /api/files/<p> -> 200 Feature.to_dict(); non-.feature -> 415 unsupported_type")


# --- HR3: PATCH /api/files/<p> with Feature shape -> validate + serialise + save ---
# Read, mutate description, write back.
existing = client.get("/api/files/Alpha/Mod/case.feature").get_json()
existing["description"] = "edited via patch"
r = client.patch("/api/files/Alpha/Mod/case.feature", json=existing)
assert r.status_code == 200, (
    f"HR3: PATCH /api/files/<p> must return 200, got {r.status_code} body={r.get_data(as_text=True)!r}"
)
assert r.get_json() == {"ok": True}, "HR3: PATCH success body must be {'ok': True}"

# Re-read and confirm the new description landed.
after = client.get("/api/files/Alpha/Mod/case.feature").get_json()
assert after["description"] == "edited via patch", (
    f"HR3: PATCH must persist the description change, got {after['description']!r}"
)
print("PASS  HR3: PATCH /api/files/<p> Feature -> 200; description persisted")


# --- HR5: PATCH /api/files/<p>/rename {file_name} -> same-parent only ------
# Done before HR4 (delete) so we still have a target.
r = client.patch(
    "/api/files/Alpha/Mod/case.feature/rename",
    json={"file_name": "renamed"},
)
assert r.status_code == 200, (
    f"HR5: PATCH rename must return 200, got {r.status_code}"
)
assert r.get_json() == {"ok": True}, "HR5: rename success body must be {'ok': True}"
assert not (root / "Alpha" / "Mod" / "case.feature").exists(), (
    "HR5: source name must be gone after rename"
)
assert (root / "Alpha" / "Mod" / "renamed.feature").is_file(), (
    "HR5: target name must exist after rename (parent preserved by construction)"
)
print("PASS  HR5: PATCH /api/files/<p>/rename {file_name} -> 200; same-parent rename applied")


# --- HR6: PATCH /api/files/<p>/move {parent} -> dest depth 2..10 -----------
# Need a second module for the move target.
client.post("/api/folders", json={"parent": "Alpha", "name": "Mod2"})
r = client.patch(
    "/api/files/Alpha/Mod/renamed.feature/move",
    json={"parent": "Alpha/Mod2"},
)
assert r.status_code == 200, (
    f"HR6: PATCH move must return 200, got {r.status_code}"
)
assert r.get_json() == {"ok": True}
assert not (root / "Alpha" / "Mod" / "renamed.feature").exists(), (
    "HR6: source must be gone after move"
)
assert (root / "Alpha" / "Mod2" / "renamed.feature").is_file(), (
    "HR6: leaf name preserved at destination parent"
)

# Same-parent move -> 400 bad_request.
r = client.patch(
    "/api/files/Alpha/Mod2/renamed.feature/move",
    json={"parent": "Alpha/Mod2"},
)
assert r.status_code == 400, (
    f"HR6: same-parent move must return 400, got {r.status_code}"
)
assert r.get_json()["error"]["code"] == "bad_request", (
    "HR6: same-parent move must carry error.code='bad_request'"
)
print("PASS  HR6: PATCH /api/files/<p>/move {parent} -> 200 cross-parent; 400 same-parent")


# --- HR7: POST /api/files/<p>/duplicate {file_name} -> same-parent copy ---
r = client.post(
    "/api/files/Alpha/Mod2/renamed.feature/duplicate",
    json={"file_name": "copy"},
)
assert r.status_code == 201, (
    f"HR7: POST duplicate must return 201, got {r.status_code}"
)
assert r.get_json() == {"ok": True}, "HR7: duplicate success body must be {'ok': True}"
assert (root / "Alpha" / "Mod2" / "renamed.feature").is_file(), (
    "HR7: source file must remain after duplicate"
)
assert (root / "Alpha" / "Mod2" / "copy.feature").is_file(), (
    "HR7: duplicate must land in same parent with .feature auto-appended"
)
print("PASS  HR7: POST /api/files/<p>/duplicate {file_name} -> 201; copy in same parent")


# --- HR8: GET /api/files/<p>/raw -> text/plain source --------------------
r = client.get("/api/files/Alpha/Mod2/renamed.feature/raw")
assert r.status_code == 200, (
    f"HR8: GET raw must return 200, got {r.status_code}"
)
ctype = r.headers.get("Content-Type", "")
assert ctype.startswith("text/plain"), (
    f"HR8: GET raw Content-Type must start with 'text/plain', got {ctype!r}"
)
assert "charset=utf-8" in ctype.lower(), (
    f"HR8: GET raw Content-Type must declare charset=utf-8, got {ctype!r}"
)
text = r.get_data(as_text=True)
assert "Feature:" in text, (
    f"HR8: raw body must contain the 'Feature:' header, got first 80 chars: {text[:80]!r}"
)

# Non-.feature path -> 415.
r = client.get("/api/files/Alpha/Mod/junk.yaml/raw")
assert r.status_code == 415, f"HR8: GET non-.feature raw must return 415, got {r.status_code}"
print("PASS  HR8: GET /api/files/<p>/raw -> 200 text/plain;charset=utf-8; non-.feature -> 415")


# --- HR9: PUT /api/files/<p>/raw -> parse + validate + re-serialise + save ---
new_raw = (
    "Feature: rewritten via raw put\n"
    "\n"
    "  Scenario: replaced\n"
    "    Given a step\n"
)
r = client.put(
    "/api/files/Alpha/Mod2/renamed.feature/raw",
    data=new_raw.encode("utf-8"),
    headers={"Content-Type": "text/plain; charset=utf-8"},
)
assert r.status_code == 200, (
    f"HR9: PUT raw must return 200, got {r.status_code} body={r.get_data(as_text=True)!r}"
)
assert r.get_json() == {"ok": True}, "HR9: PUT raw success body must be {'ok': True}"

after_text = (root / "Alpha" / "Mod2" / "renamed.feature").read_text(encoding="utf-8")
assert "rewritten via raw put" in after_text, (
    f"HR9: PUT raw must persist the new description, on-disk text: {after_text[:160]!r}"
)
print("PASS  HR9: PUT /api/files/<p>/raw text -> 200; parsed + canonicalised + written")


# --- HR4: DELETE /api/files/<p> -> 204 idempotent --------------------------
# Done last so the prior routes had targets to operate on.
r = client.delete("/api/files/Alpha/Mod2/renamed.feature")
assert r.status_code == 204, (
    f"HR4: DELETE existing file must return 204, got {r.status_code}"
)
assert r.get_data(as_text=True) == "", "HR4: 204 body must be empty"
assert not (root / "Alpha" / "Mod2" / "renamed.feature").exists(), (
    "HR4: target must be gone after delete"
)

# Second DELETE -> still 204 (idempotent).
r = client.delete("/api/files/Alpha/Mod2/renamed.feature")
assert r.status_code == 204, "HR4: idempotent DELETE must still return 204"
assert r.get_data(as_text=True) == "", "HR4: idempotent DELETE body must be empty"
print("PASS  HR4: DELETE /api/files/<p> -> 204 (idempotent on missing target)")
