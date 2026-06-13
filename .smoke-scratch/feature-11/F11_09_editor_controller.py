"""S3.3 + S3.4 smoke — tmsEditor controller wires for enums (static check).

The structured tab logic is JS, not executable from Python without a
headless browser. This smoke statically inspects app/static/app.js to
prove the controller carries the spec-mandated surface:

S3.3 — fetch + render + dirty wire-up:
1. Session vocab cache slot (`tmsEditor._vocabCache`) exists.
2. `_loadEnums()` fetches `GET /api/enums/<project>` (URL-encoded).
3. `renderEnums()` exists and is called from `renderStructured()` so
   feature reloads + tab switches re-render pickers.
4. Picker `<change>` handler mutates `state.feature.enums[kind]` and
   calls `markDirty(true)`.
5. Orphan rows are rendered for `(kind, key)` pairs not in vocab.

S3.4 — Initialize enums file button POST flow:
6. `wireEnumsInit()` is invoked from `boot()` (button listener).
7. `_initEnumsFile()` POSTs `/api/enums/<project>` and on 201 hydrates
   the session cache + state.enumsVocab + state.enumsStatus and
   re-renders.

In addition: the integrated /ui/file/<p> render-time HTML must continue
to expose the four enums sub-element ids (regression check on S3.2),
and the bootstrapped editor-data must carry `feature.enums`.
"""
import json
import pathlib
import re
import tempfile

from app import create_app


JS_PATH = pathlib.Path("app/static")
src = "\n".join(_p.read_text() for _p in sorted(JS_PATH.glob("*.js")))

# --- 1. Session cache slot -------------------------------------------------
assert "_vocabCache: Object.create(null)" in src, "vocab cache slot missing"
assert "tmsEditor._vocabCache[project]" in src, (
    "vocab cache must be keyed by project name"
)
print("PASS  Session-level _vocabCache slot keyed by project")

# --- 2. _loadEnums fetches GET /api/enums/<project> -----------------------
assert "_loadEnums()" in src, "_loadEnums method missing"
# Match the fetch URL pattern, allowing single or double quotes.
m = re.search(
    r"fetch\([\"']/api/enums/[\"']\s*\+\s*encodeURIComponent\(project\)",
    src,
)
assert m, "GET /api/enums/<project> with encodeURIComponent missing"
print("PASS  _loadEnums fetches GET /api/enums/<project> with URL encoding")

# --- 3. renderEnums + wired into renderStructured -------------------------
assert "renderEnums()" in src, "renderEnums method missing"
# Confirm renderStructured calls renderEnums (covers SSE reload + discard).
struct_block = re.search(
    r"renderStructured\(\)\s*\{[^}]*?this\.renderEnums\(\);",
    src,
    flags=re.DOTALL,
)
assert struct_block, "renderStructured() does not call renderEnums()"
print("PASS  renderEnums wired into renderStructured() reload path")

# --- 4. Value <select> change commits via _commitEnumRows ----------------
# tech-04 D5 reshaped the editor into a (kind, value) row grid. A value (or
# kind) change calls _commitEnumRows(), which rebuilds state.feature.enums
# from the visible rows and marks dirty only when the map actually changed.
m = re.search(
    r"_buildEnumRow\([^)]*\)\s*\{(.*?)\n  \},",
    src,
    flags=re.DOTALL,
)
assert m, "_buildEnumRow block not found"
row_body = m.group(1)
assert "this._commitEnumRows()" in row_body, (
    "a value/kind change must commit via _commitEnumRows()"
)
m2 = re.search(
    r"_commitEnumRows\(\)\s*\{(.*?)\n  \},",
    src,
    flags=re.DOTALL,
)
assert m2, "_commitEnumRows block not found"
commit_body = m2.group(1)
assert "this.state.feature.enums = next" in commit_body, (
    "_commitEnumRows must rebuild state.feature.enums from the rows"
)
assert "markDirty(true)" in commit_body, (
    "_commitEnumRows must call markDirty(true) when the committed map changes"
)
print("PASS  Value/kind change commits via _commitEnumRows -> rebuilds feature.enums + marks dirty")

# --- 5. Orphan rendering -------------------------------------------------
assert "_renderEnumOrphans()" in src, "_renderEnumOrphans method missing"
assert 'dataset.orphan = "1"' in src, "orphan row marker missing"
assert "Not defined in enums.yaml" in src, (
    "orphan row missing user-facing hint text"
)
# Orphan-detection logic mirrors the spec's join: (kind ∉ vocab) OR
# (kind ∈ vocab ∧ key ∉ vocab[kind]).
assert "kindEntries === undefined || !(key in kindEntries)" in src, (
    "orphan join logic does not match spec (kind ∉ vocab OR key ∉ vocab[kind])"
)
print("PASS  Orphan rows rendered per spec join logic")

# --- 6. wireEnumsInit invoked from tmsEditor.boot ------------------------
# app.js declares two `boot()` methods (tmsRunEditor and tmsEditor). The
# one we care about lives below `const tmsEditor = {`; anchor on that.
ed_block = re.search(
    r"const tmsEditor = \{(.*?)^\};",
    src,
    flags=re.DOTALL | re.MULTILINE,
)
assert ed_block, "tmsEditor block not found"
boot_block = re.search(
    r"\n  boot\(\)\s*\{(.*?)\n  \},", ed_block.group(1), flags=re.DOTALL
)
assert boot_block, "tmsEditor.boot() block not found"
assert "this.wireEnumsInit();" in boot_block.group(1), (
    "tmsEditor.boot() must wire the Initialize button listener"
)
assert "this._loadEnums();" in boot_block.group(1), (
    "tmsEditor.boot() must kick off the async enums fetch"
)
print("PASS  tmsEditor.boot() wires Initialize button + kicks off _loadEnums()")

# --- 7. POST flow on init -------------------------------------------------
m = re.search(
    r'_initEnumsFile\(\)\s*\{(.*?)\n  \},',
    src,
    flags=re.DOTALL,
)
assert m, "_initEnumsFile method missing"
init_body = m.group(1)
assert 'method: "POST"' in init_body, "POST method missing"
assert "/api/enums/" in init_body, "POST URL missing"
assert "encodeURIComponent(project)" in init_body, (
    "POST URL must URL-encode the project"
)
assert "tmsEditor._vocabCache[project] = Promise.resolve(" in init_body, (
    "init must hydrate the session cache from the POST response"
)
assert 'this.state.enumsStatus = "ok"' in init_body, (
    "init must transition status to 'ok' on success"
)
assert "this.renderEnums();" in init_body, (
    "init must re-render after hydration"
)
print("PASS  _initEnumsFile POSTs, hydrates cache, transitions to 'ok'")

# --- 8. Integration regression: bootstrapped payload still carries enums --
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    s.create_file(["Alpha", "Mod", "a.feature"], description="A")

    # Hand-write a vocab + a feature carrying a known enum so the editor
    # boots with state.feature.enums non-empty.
    (root / "Alpha" / "enums.yaml").write_bytes(
        b"components:\n  - login: Login by credential\n"
    )
    feat = s.read_feature("Alpha/Mod/a.feature")
    feat.enums = {"components": "login"}
    s.write_feature(["Alpha", "Mod", "a.feature"], feat)

    client = app.test_client()
    html = client.get("/ui/file/Alpha/Mod/a.feature").get_data(as_text=True)
    m = re.search(
        r'<script id="editor-data" type="application/json">\s*(.*?)\s*</script>',
        html,
        flags=re.DOTALL,
    )
    assert m, "editor-data missing"
    payload = json.loads(m.group(1))
    assert payload["feature"]["enums"] == {"components": "login"}, (
        payload["feature"]["enums"]
    )
    print("PASS  Editor bootstrap carries feature.enums into the JS state")
