"""Smoke j1: run_editor.html row + template prototype carry the two-span shape.

Tracks the "Investigate: run editor — mask test-case column to filename only"
Must-have item. Static-wiring (template-source) only.

Five assertions:
1. Server-rendered row contains a `data-role="folder"` span.
2. Server-rendered row contains a `data-role="filename"` span.
3. `<template id="run-result-row-template">` prototype contains the
   same two spans (clone-path parity with the server path).
4. The full path is preserved on all three preservation surfaces:
   `<tr data-file-path>`, `<td title>`, and `<a hx-get>` use
   `{{ r.file_path }}` verbatim.
5. The `<td>` wrapping the link no longer carries `truncate` —
   responsibility for ellipsis moved to the inner folder span's
   `truncate min-w-0` flex layout, so a stale outer `truncate` would
   be dead and confusing.
"""
import pathlib
import re

TPL = pathlib.Path("app/templates/run_editor.html").read_text()

# --- 1 + 2. Server row carries both data-role spans -------------------
# Carve out the `{% for r in run.results %}` block once so we don't
# accidentally match the <template> prototype below.
server_block = re.search(
    r"\{%\s*for\s+r\s+in\s+run\.results\s*%\}(.*?)\{%\s*endfor\s*%\}",
    TPL, re.S,
)
assert server_block, "could not locate {% for r in run.results %} block"
server_html = server_block.group(1)
assert 'data-role="folder"' in server_html, (
    "server row should contain <span data-role='folder'> for the masked folder path"
)
assert 'data-role="filename"' in server_html, (
    "server row should contain <span data-role='filename'> for the emphasized filename"
)
print("PASS  server row carries data-role='folder' + data-role='filename' spans")

# --- 3. <template> prototype mirrors the same shape -------------------
proto_block = re.search(
    r'<template\s+id="run-result-row-template">(.*?)</template>',
    TPL, re.S,
)
assert proto_block, "could not locate <template id='run-result-row-template'>"
proto_html = proto_block.group(1)
assert 'data-role="folder"' in proto_html, (
    "prototype must mirror the server row's data-role='folder' span"
)
assert 'data-role="filename"' in proto_html, (
    "prototype must mirror the server row's data-role='filename' span"
)
print("PASS  <template> prototype mirrors the two-span shape")

# --- 4. Full path preserved on tr/td/a ---------------------------------
# Each surface carries the unmasked Jinja expression {{ r.file_path }}.
assert re.search(r'data-file-path="\{\{\s*r\.file_path\s*\}\}"', server_html), (
    "<tr data-file-path='{{ r.file_path }}'> must carry the unmasked full path"
)
assert re.search(r'title="\{\{\s*r\.file_path\s*\}\}"', server_html), (
    "<td title='{{ r.file_path }}'> must carry the unmasked full path for tooltip"
)
assert re.search(r'hx-get="/ui/file/\{\{\s*r\.file_path\s*\}\}"', server_html), (
    "<a hx-get='/ui/file/{{ r.file_path }}'> must carry the unmasked full path for navigation"
)
print("PASS  full r.file_path preserved on <tr data-file-path>, <td title>, <a hx-get>")

# --- 5. Outer <td> no longer carries `truncate` ------------------------
# Match the test-case <td> opening tag (the one with title=).
td_match = re.search(
    r'<td\s+class="([^"]*)"\s+title="\{\{\s*r\.file_path\s*\}\}"',
    server_html,
)
assert td_match, "could not locate the test-case <td> opening tag"
td_classes = td_match.group(1).split()
assert "truncate" not in td_classes, (
    f"<td> should no longer carry `truncate` class; got {td_classes!r}. "
    "Truncation now lives on the inner folder span."
)
print("PASS  outer <td> no longer carries dead `truncate` class")
