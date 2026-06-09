# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Sub-folder-table column (ST1).

One column `Sub-folder` with a folder icon (`&#128193;` -> 📁). Click
on a row navigates to `/ui/folder/<path>`.
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
    client.post("/api/folders", json={"parent": "Alpha/Mod", "name": "Sub"})
    html = client.get("/ui/folder/Alpha/Mod").get_data(as_text=True)

# ST1: one column header named "Sub-folder".
header_match = re.search(
    r'<th[^>]*>Sub-folder</th>',
    html,
)
assert header_match, (
    "ST1: folder_module.html must render exactly one `<th>Sub-folder</th>` "
    "header for the sub-folder table"
)

# ST1: row hx-get -> /ui/folder/<path>.
row_match = re.search(
    r'<tr[^>]*hx-get="/ui/folder/Alpha/Mod/Sub"[^>]*'
    r'hx-target="#main-pane"[^>]*hx-swap="innerHTML"',
    html,
)
assert row_match, (
    "ST1: sub-folder row must carry hx-get='/ui/folder/Alpha/Mod/Sub' + "
    "hx-target='#main-pane' + hx-swap='innerHTML' (click navigates to the "
    "sub-folder's view)"
)

# ST1: row body carries the folder icon entity + the folder name.
row_body = re.search(
    r'<tr[^>]*hx-get="/ui/folder/Alpha/Mod/Sub"[^>]*>(.*?)</tr>',
    html,
    re.DOTALL,
).group(1)
assert "&#128193;" in row_body, (
    f"ST1: sub-folder row must render the folder icon HTML entity "
    f"`&#128193;` (📁); got {row_body!r}"
)
assert "Sub" in row_body, (
    f"ST1: sub-folder row must render the folder name 'Sub'; got {row_body!r}"
)
print("PASS  ST1: sub-folder table has one 'Sub-folder' column with 📁 icon; row hx-get -> /ui/folder/<path>")
