"""Smoke j2: tmsRunEditor._createResultRow populates the filename span.

Updated for tech-02 E2 (specs/tech/02-tech-ui-styling-enhancement-NEW.md):
clones are filename-only (the folder is carried by the group heading), so the
function writes ONLY the filename span and no longer touches a folder span.
Static-wiring (function-body grep) only.

Four assertions on the body of `_createResultRow`:
1. The function carves the path via `lastIndexOf("/")` (defensive
   split that handles zero-slash file_paths — parity with the Jinja
   `rsplit('/', 1)` branch in run_editor.html).
2. The function writes textContent into the filename span via
   `querySelector('[data-role="filename"]')` and does NOT write a
   `data-role="folder"` span (E2: folder span dropped).
3. The function still preserves the full path on the link tooltip
   (`linkCell.setAttribute("title", file_path)`).
4. The function still preserves the full path on the navigation
   target (link.setAttribute("hx-get", `/ui/file/${file_path}`)).
"""
import pathlib
import re

APP_JS = "\n".join(_p.read_text() for _p in sorted(pathlib.Path("app/static").glob("*.js")))

# Carve out the `_createResultRow(file_path) { ... }` body via the
# consistent method-indent + `\n  },` closer used by the rest of
# tmsRunEditor.
m = re.search(
    r"_createResultRow\s*\(\s*file_path[^)]*\)\s*\{[\s\S]*?\n  \},",
    APP_JS,
)
assert m, "could not locate _createResultRow function body in app.js"
body = m.group(0)

# --- 1. Defensive split via lastIndexOf("/") --------------------------
assert 'lastIndexOf("/")' in body, (
    "_createResultRow should split file_path via `lastIndexOf(\"/\")` "
    "(defensive — handles zero-slash paths)"
)
print("PASS  _createResultRow splits path via lastIndexOf('/')")

# --- 2. Populates the filename span only (folder span dropped) --------
assert re.search(
    r'querySelector\([\'"]\[data-role="filename"\][\'"]\)\.textContent\s*=',
    body,
), "filename span must get a textContent assignment"
assert 'data-role="folder"' not in body, (
    "E2: _createResultRow must NOT touch a folder span (filename-only rows)"
)
print("PASS  _createResultRow writes the filename span; no folder span")

# --- 3. Tooltip preserved with full path -------------------------------
assert re.search(
    r'linkCell\.setAttribute\(\s*"title"\s*,\s*file_path\s*\)',
    body,
), "tooltip must keep the full file_path via linkCell.setAttribute('title', file_path)"
print("PASS  full file_path preserved on <td title> via setAttribute")

# --- 4. hx-get preserved with full path -------------------------------
assert re.search(
    r'link\.setAttribute\(\s*"hx-get"\s*,\s*`/ui/file/\$\{file_path\}`\s*\)',
    body,
), "hx-get must keep the full file_path via link.setAttribute('hx-get', `/ui/file/${file_path}`)"
print("PASS  full file_path preserved on <a hx-get> via setAttribute")
