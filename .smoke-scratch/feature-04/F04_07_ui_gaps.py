# Pattern: see .smoke-scratch/README.md
"""feature-04 / folder-crud / UI gaps (UG1).

Two-pronged negative-invariant test per Step-1 sign-off note 3:
(a) rendered HTML at every folder-view depth must NOT contain folder
    rename/delete UI affordances, AND
(b) `app/static/app.js` must NOT define `tmsRenameFolder` /
    `tmsDeleteFolder` symbols.

Phrasing chosen carefully: existing FILE-level rename/delete UI
(`tmsRenameFile`, the editor's `rename()` action, etc.) is OUT of
scope and must NOT register as a false positive.
"""
import pathlib
import re
import tempfile

from app import create_app


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(_p.read_text() for _p in sorted((REPO_ROOT / "app" / "static").glob("*.js")))


# --- UG1(b): app.js must not define folder rename/delete symbols -----------
# Function-declaration forms only -- a reference inside a comment or a
# string would not cause a UI surface to appear.
banned_symbols = ["tmsRenameFolder", "tmsDeleteFolder"]
for sym in banned_symbols:
    decl_re = re.compile(
        rf"(?:async\s+)?function\s+{re.escape(sym)}\b"
        rf"|\b{re.escape(sym)}\s*=\s*(?:async\s+)?function\b"
        rf"|\b{re.escape(sym)}\s*=\s*(?:async\s+)?\("
    )
    assert not decl_re.search(JS), (
        f"UG1(b): app/static/app.js must NOT define {sym}() "
        f"(v1 has no UI button for folder rename/delete)"
    )

# Confirm the FILE-level symbols still exist (sanity: we're not just
# missing the entire JS file or grepping the wrong path).
for sym in ["tmsCreateProject", "tmsCreateModule", "tmsCreateSubfolder"]:
    assert re.search(rf"function\s+{re.escape(sym)}\b", JS), (
        f"UG1(b) sanity: file-level {sym}() must exist in app.js "
        "(test would be a false negative if the JS file were truncated)"
    )
print("PASS  UG1(b): app/static/app.js defines no tmsRenameFolder / tmsDeleteFolder symbols")


# --- UG1(a): rendered folder views must not expose rename/delete UI -------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()

    # Seed: project (depth 1), module (depth 2), sub-folder (depth 3).
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post("/api/folders", json={"parent": "Alpha/Mod", "name": "Sub"})

    views = [
        ("/ui/folder/",           "root"),
        ("/ui/folder/Alpha",      "project"),
        ("/ui/folder/Alpha/Mod",  "module"),
        ("/ui/folder/Alpha/Mod/Sub", "subfolder"),
    ]

    # Banned literal labels (case-insensitive).
    banned_labels = ["rename folder", "delete folder"]
    # Banned HTMX / fetch handler shapes that would imply a UI affordance
    # firing the folder rename/delete API.
    banned_handler_patterns = [
        re.compile(r"""hx-(?:patch|delete)\s*=\s*["'][^"']*?/api/folders/""", re.IGNORECASE),
        re.compile(r"""tmsRenameFolder\s*\(""", re.IGNORECASE),
        re.compile(r"""tmsDeleteFolder\s*\(""", re.IGNORECASE),
    ]

    for url, depth_name in views:
        r = client.get(url)
        assert r.status_code == 200, (
            f"UG1(a) setup: GET {url} ({depth_name}) must render 200, got {r.status_code}"
        )
        html = r.get_data(as_text=True)
        html_lower = html.lower()
        for label in banned_labels:
            assert label not in html_lower, (
                f"UG1(a): {depth_name} view ({url}) must NOT contain UI label "
                f"{label!r} (v1 has no folder rename/delete buttons)"
            )
        for pat in banned_handler_patterns:
            assert not pat.search(html), (
                f"UG1(a): {depth_name} view ({url}) must NOT wire a folder "
                f"rename/delete handler matching /{pat.pattern}/"
            )
print(
    "PASS  UG1(a): folder views at root/project/module/subfolder depths "
    "expose no rename/delete folder UI"
)
