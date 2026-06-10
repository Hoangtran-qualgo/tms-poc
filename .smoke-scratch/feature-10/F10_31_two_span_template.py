"""Smoke j1: run_editor.html rows are filename-only under folder headings.

Updated for tech-02 E2 (specs/tech/02-tech-ui-styling-enhancement-NEW.md):
results are grouped by folder. Each group emits a plain `run-group-head`
heading row carrying the folder, and each result row is filename-only — the
masked folder span (the old two-span shape) is dropped. Static template-source
inspection only.

Five assertions:
1. The server emits a folder heading row: `<tr class="run-group-head"
   ... data-group-folder="{{ folder }}">`.
2. Result rows are filename-only: a `data-role="filename"` span exists and
   NO `data-role="folder"` span remains anywhere in the template.
3. Both the result-row `<template>` and the group-head `<template>` exist
   (clone-path parity with the server path).
4. The full path is preserved on all three preservation surfaces:
   `<tr data-file-path>`, `<td title>`, and `<a hx-get>` use
   `{{ r.file_path }}` verbatim.
5. The test-case `<td>` does not carry `truncate` (ellipsis lives on the
   inner filename span's `truncate min-w-0`).
"""
import pathlib
import re

TPL = pathlib.Path("app/templates/run_editor.html").read_text()

# --- 1. Server emits a folder heading row -----------------------------
assert re.search(
    r'<tr class="run-group-head[^"]*"[^>]*data-group-folder="\{\{\s*folder\s*\}\}"',
    TPL,
), "server must emit a run-group-head row keyed by data-group-folder"
print("PASS  server emits run-group-head folder heading rows")

# --- 2. Filename-only rows: filename span present, folder span gone ---
assert 'data-role="filename"' in TPL, (
    "result rows must contain <span data-role='filename'> for the filename"
)
assert 'data-role="folder"' not in TPL, (
    "E2: the masked folder span must be dropped (folder now lives in the heading)"
)
print("PASS  rows are filename-only; folder span dropped")

# --- 3. Both <template>s exist ----------------------------------------
assert re.search(r'<template\s+id="run-result-row-template">', TPL), (
    "result-row <template> must exist"
)
assert re.search(r'<template\s+id="run-group-head-template">', TPL), (
    "E2: a group-head <template> must exist so JS clones headings without drift"
)
proto = re.search(
    r'<template\s+id="run-result-row-template">(.*?)</template>', TPL, re.S
).group(1)
assert 'data-role="filename"' in proto and 'data-role="folder"' not in proto, (
    "result-row prototype must mirror the filename-only shape"
)
print("PASS  result-row + group-head templates present, prototype filename-only")

# --- 4. Full path preserved on tr/td/a --------------------------------
assert re.search(r'data-file-path="\{\{\s*r\.file_path\s*\}\}"', TPL), (
    "<tr data-file-path='{{ r.file_path }}'> must carry the unmasked full path"
)
assert re.search(r'title="\{\{\s*r\.file_path\s*\}\}"', TPL), (
    "<td title='{{ r.file_path }}'> must carry the unmasked full path for tooltip"
)
assert re.search(r'hx-get="/ui/file/\{\{\s*r\.file_path\s*\}\}"', TPL), (
    "<a hx-get='/ui/file/{{ r.file_path }}'> must carry the unmasked full path"
)
print("PASS  full r.file_path preserved on <tr data-file-path>, <td title>, <a hx-get>")

# --- 5. Test-case <td> does not carry `truncate` ----------------------
td_match = re.search(
    r'<td\s+class="([^"]*)"\s+title="\{\{\s*r\.file_path\s*\}\}"', TPL
)
assert td_match, "could not locate the test-case <td> opening tag"
td_classes = td_match.group(1).split()
assert "truncate" not in td_classes, (
    f"<td> should not carry `truncate`; got {td_classes!r}. "
    "Truncation now lives on the inner filename span."
)
print("PASS  test-case <td> does not carry `truncate` (lives on filename span)")
