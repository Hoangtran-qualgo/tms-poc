# Pattern: see .smoke-scratch/README.md
"""feature-05 / testcase-crud / UI gaps (UG1-UG2).

Two negative invariants:
- UG1: `DELETE /api/files/<p>` has no UI button in v1.
- UG2: `POST /api/files/<p>/duplicate` has no UI button in v1.

Both prongs each test:
(a) the file_editor.html topbar template carries no #btn-delete /
    #btn-duplicate element, AND
(b) app/static/app.js carries no JS code that issues those requests.
"""
import pathlib
import re
import tempfile

from app import create_app


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(_p.read_text() for _p in sorted((REPO_ROOT / "app" / "static").glob("*.js")))
TEMPLATE = (
    REPO_ROOT / "app" / "templates" / "file_editor.html"
).read_text()


# --- UG1(a): file_editor.html has no #btn-delete ---------------------------
assert "btn-delete" not in TEMPLATE, (
    "UG1(a): file_editor.html must NOT carry a #btn-delete element "
    "(v1 has no UI button for folder/file delete)"
)

# --- UG1(b): app.js issues no DELETE request to /api/files/ ----------------
# Match a fetch call whose URL begins with /api/files/ AND whose method is DELETE,
# allowing arbitrary intervening characters (option-object key order varies).
delete_files_re = re.compile(
    r"""fetch\([^)]*?["']/api/files/[^)]*?["']DELETE["']""",
    re.DOTALL | re.IGNORECASE,
)
alt_delete_re = re.compile(
    r"""method\s*:\s*["']DELETE["'][\s\S]{0,400}?/api/files/""",
    re.IGNORECASE,
)
alt_delete2_re = re.compile(
    r"""/api/files/[\s\S]{0,400}?method\s*:\s*["']DELETE["']""",
    re.IGNORECASE,
)
assert not delete_files_re.search(JS), (
    "UG1(b): app/static/app.js must NOT issue fetch(DELETE) to /api/files/"
)
assert not alt_delete_re.search(JS), (
    "UG1(b): app/static/app.js must NOT pair `method: 'DELETE'` with /api/files/"
)
assert not alt_delete2_re.search(JS), (
    "UG1(b): app/static/app.js must NOT pair /api/files/ with `method: 'DELETE'`"
)

# Symbol-level absence (same shape as feature-04 UG1(b)).
for sym in ("tmsDeleteFile",):
    decl_re = re.compile(
        rf"(?:async\s+)?function\s+{re.escape(sym)}\b"
        rf"|\b{re.escape(sym)}\s*=\s*(?:async\s+)?function\b"
        rf"|\b{re.escape(sym)}\s*=\s*(?:async\s+)?\("
    )
    assert not decl_re.search(JS), (
        f"UG1(b): app/static/app.js must NOT define {sym}() (no UI for file delete)"
    )
print("PASS  UG1: no #btn-delete in file_editor.html; no DELETE /api/files/ in app.js; no tmsDeleteFile symbol")


# --- UG2(a): file_editor.html has no #btn-duplicate ------------------------
assert "btn-duplicate" not in TEMPLATE, (
    "UG2(a): file_editor.html must NOT carry a #btn-duplicate element "
    "(v1 has no UI button for file duplicate)"
)

# --- UG2(b): app.js issues no POST to /api/files/<p>/duplicate ------------
dup_files_re = re.compile(
    r"""/api/files/[^"'\s]*?/duplicate""", re.IGNORECASE,
)
assert not dup_files_re.search(JS), (
    "UG2(b): app/static/app.js must NOT reference /api/files/<p>/duplicate "
    "(no UI for file duplicate)"
)

for sym in ("tmsDuplicateFile",):
    decl_re = re.compile(
        rf"(?:async\s+)?function\s+{re.escape(sym)}\b"
        rf"|\b{re.escape(sym)}\s*=\s*(?:async\s+)?function\b"
        rf"|\b{re.escape(sym)}\s*=\s*(?:async\s+)?\("
    )
    assert not decl_re.search(JS), (
        f"UG2(b): app/static/app.js must NOT define {sym}() (no UI for file duplicate)"
    )
print("PASS  UG2: no #btn-duplicate in file_editor.html; no /api/files/.../duplicate in app.js; no tmsDuplicateFile symbol")


# --- Sanity: positive controls -- the FILE-level rename/move/save buttons --
# must still exist (so the negative assertions above aren't false-negatives
# from a truncated file or a stale path).
assert "btn-rename" in TEMPLATE, "UG sanity: #btn-rename must still exist (positive control)"
assert "btn-move" in TEMPLATE, "UG sanity: #btn-move must still exist (positive control)"
assert "btn-save" in TEMPLATE, "UG sanity: #btn-save must still exist (positive control)"

# --- Negative invariant survives a live render of the editor too -----------
# Verify a real /ui/file/<p> response does not contain delete/duplicate UI.
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "scenario_name": "s", "description": "seed"},
    )
    html = client.get("/ui/file/Alpha/Mod/case.feature").get_data(as_text=True)
    assert "btn-delete" not in html, (
        "UG1 live: rendered /ui/file/<p> must NOT contain #btn-delete"
    )
    assert "btn-duplicate" not in html, (
        "UG2 live: rendered /ui/file/<p> must NOT contain #btn-duplicate"
    )
print("PASS  UG sanity + live render: #btn-delete and #btn-duplicate absent from /ui/file/<p>")
