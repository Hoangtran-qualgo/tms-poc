# Pattern: see .smoke-scratch/README.md
"""tech-03 / folder bulk-actions / per-row checkbox + no-navigate (U2).

Every feature row gets a leading checkbox cell. The cell AND the input
carry `onclick="event.stopPropagation()"` so toggling selection never
fires the row's HTMX `hx-get` navigation (same event-bubbling technique
proven in tree.html). The input carries the canonical selection key in
`data-case-path` (= the data-root-relative path, identical to the row's
hx-get suffix). The `<tr>` itself MUST still carry hx-get unchanged so the
feature-07 contract holds.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "description": "x"},
    )
    html = client.get("/ui/folder/Alpha/Mod").get_data(as_text=True)

# The row still navigates via hx-get on the <tr> (feature-07 contract).
row_m = re.search(
    r'<tr[^>]*hx-get="/ui/file/Alpha/Mod/case\.feature"[^>]*>(.*?)</tr>',
    html,
    re.DOTALL,
)
assert row_m, "row must still carry hx-get on the <tr> (navigation preserved)"
row = row_m.group(1)

# The row's checkbox carries the canonical key and stops propagation.
box = re.search(
    r'<input[^>]*data-role="select"[^>]*data-case-path="Alpha/Mod/case\.feature"[^>]*>',
    row,
)
assert box, (
    "each row must carry a select checkbox with "
    "data-case-path='Alpha/Mod/case.feature' (canonical selection key)"
)
assert "event.stopPropagation()" in box.group(0), (
    "U2: the row checkbox input must stopPropagation so it does not trigger "
    "the row's hx-get navigation"
)

# The checkbox CELL also stops propagation (covers clicks in the cell padding).
cell = re.search(
    r'<td[^>]*onclick="event\.stopPropagation\(\)"[^>]*>\s*<input[^>]*data-role="select"',
    row,
    re.DOTALL,
)
assert cell, (
    "U2: the checkbox <td> must carry onclick='event.stopPropagation()' so "
    "clicks anywhere in the cell never navigate"
)
print("PASS  T03_03: per-row checkbox carries canonical key + double stopPropagation; <tr> hx-get intact")
