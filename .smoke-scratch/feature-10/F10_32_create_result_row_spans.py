"""Smoke j2: tmsRunEditor._createResultRow populates both data-role spans.

Tracks the "Investigate: run editor — mask test-case column to filename only"
Must-have item. Static-wiring (function-body grep) only — the actual
clone & render path is exercised by browser interaction.

Four assertions on the body of `_createResultRow`:
1. The function carves the path via `lastIndexOf("/")` (defensive
   split that handles zero-slash file_paths — parity with the Jinja
   `rsplit('/', 1)` branch in run_editor.html).
2. The function writes textContent into BOTH spans via
   `querySelector('[data-role="folder"]')` and
   `querySelector('[data-role="filename"]')`.
3. The function still preserves the full path on the link tooltip
   (`linkCell.setAttribute("title", file_path)`).
4. The function still preserves the full path on the navigation
   target (link.setAttribute("hx-get", `/ui/file/${file_path}`)).
"""
import pathlib
import re

APP_JS = pathlib.Path("app/static/app.js").read_text()

# Carve out the `_createResultRow(file_path) { ... }` body via the
# consistent method-indent + `\n  },` closer used by the rest of
# tmsRunEditor.
m = re.search(
    r"_createResultRow\s*\(\s*file_path\s*\)\s*\{[\s\S]*?\n  \},",
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

# --- 2. Populates both data-role spans --------------------------------
assert "querySelector('[data-role=\"folder\"]')" in body or \
       'querySelector(\'[data-role="folder"]\')' in body, (
    "_createResultRow should populate the folder span via "
    "querySelector('[data-role=\"folder\"]').textContent"
)
assert "querySelector('[data-role=\"filename\"]')" in body or \
       'querySelector(\'[data-role="filename"]\')' in body, (
    "_createResultRow should populate the filename span via "
    "querySelector('[data-role=\"filename\"]').textContent"
)
# Confirm textContent assignment is wired (not just a query without a write).
assert re.search(
    r'querySelector\([\'"]\[data-role="folder"\][\'"]\)\.textContent\s*=',
    body,
), "folder span must get a textContent assignment"
assert re.search(
    r'querySelector\([\'"]\[data-role="filename"\][\'"]\)\.textContent\s*=',
    body,
), "filename span must get a textContent assignment"
print("PASS  both data-role spans receive textContent assignments")

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
