# Pattern: see .smoke-scratch/README.md
"""feature-13 / enums — enum entry KEYS may contain a dash (e.g. knowledge-base).

Enum *kinds* stay strict identifiers (`ENUM_IDENTIFIER_RE`); only entry
*keys* are relaxed to `ENUM_KEY_RE` (`^[A-Za-z_][A-Za-z0-9_-]*$`). This pins
the relaxation end-to-end across every layer a dashed key must survive:

  1. PUT /api/enums accepts a dashed key; GET round-trips it.
  2. A feature selecting a dashed key validates + serialise→parse round-trips
     (the on-disk `# enum.<kind>: <key>` directive carries the dash).
  3. rename cascade works dashed→dashed across referencing features.
  4. client manager validates entry keys with ENUM_KEY_RE (not ENUM_ID_RE).
"""
import pathlib
import tempfile

from app import create_app
from app.gherkin_io import parse_feature, serialize_feature
from app.models import Feature, Scenario, Step, validate_feature
from app.storage import Storage


# --- 1. PUT accepts a dashed key; GET round-trips. ------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    Storage(root).create_folder(["P"])
    c = create_app(data_root=root).test_client()
    r = c.put("/api/enums/P", json={"components": {"knowledge-base": "Knowledge base"}})
    assert r.status_code == 200, (r.status_code, r.get_json())
    got = c.get("/api/enums/P").get_json()
    assert got == {"components": {"knowledge-base": "Knowledge base"}}, got
    print("PASS  PUT/GET round-trips a dashed enum key")

# --- 2. Feature with a dashed key validates + serialise→parse round-trips -
feat = Feature(
    description="Smoke",
    scenario=Scenario(kind="scenario", name="s", steps=[Step(keyword="Given", text="x")]),
    enums={"component": "knowledge-base"},
)
validate_feature(feat)  # must not raise
reparsed = parse_feature(serialize_feature(feat))
assert reparsed.enums == {"component": "knowledge-base"}, reparsed.enums
print("PASS  dashed key survives validate + serialise/parse round-trip")

# --- 3. rename cascade dashed→dashed across referencing features. ---------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["P"])
    s.write_project_enums("P", {"components": {"knowledge-base": "Knowledge base"}})
    for name in ("a.feature", "b.feature"):
        s.create_file(["P", name], "desc")
        f = s.read_feature(["P", name])
        f.enums["components"] = "knowledge-base"
        s.write_feature(["P", name], f)

    c = create_app(data_root=root).test_client()
    r = c.post("/api/enums/P/rename", json={
        "kind": "components", "old_key": "knowledge-base", "new_key": "knowledge-store",
    })
    assert r.status_code == 200, (r.status_code, r.get_json())
    assert r.get_json() == {"renamed": 2}, r.get_json()
    assert s.read_project_enums("P") == {"components": {"knowledge-store": "Knowledge base"}}
    assert s.read_feature(["P", "a.feature"]).enums["components"] == "knowledge-store"
    assert s.read_feature(["P", "b.feature"]).enums["components"] == "knowledge-store"
    print("PASS  rename cascades dashed→dashed across referencing features")

# --- 4. client manager validates entry keys with ENUM_KEY_RE. -------------
JS = pathlib.Path("app/static/08_enums_manager.js").read_text()
assert "const ENUM_KEY_RE = /^[A-Za-z_][A-Za-z0-9_-]*$/;" in JS, "client ENUM_KEY_RE missing"
assert "if (!ENUM_KEY_RE.test(key))" in JS, "_addEntry must validate keys with ENUM_KEY_RE"
assert "if (!ENUM_ID_RE.test(name))" in JS, "_addKind must keep ENUM_ID_RE for kinds"
print("PASS  client manager uses ENUM_KEY_RE for entry keys, ENUM_ID_RE for kinds")
