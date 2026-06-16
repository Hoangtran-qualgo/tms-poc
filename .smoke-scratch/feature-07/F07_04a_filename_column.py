# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Features-table FT1 (File name column).

`File name` shown as-is; click on the row -> `/ui/file/<path>`.
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
        json={"parent": "Alpha/Mod", "file_name": "case", "scenario_name": "s", "description": "seed"},
    )
    html = client.get("/ui/folder/Alpha/Mod").get_data(as_text=True)

# Row carries hx-get to /ui/file/<path> with #main-pane target.
row_pattern = re.search(
    r'<tr[^>]*hx-get="/ui/file/Alpha/Mod/case\.feature"[^>]*'
    r'hx-target="#main-pane"[^>]*hx-swap="innerHTML"',
    html,
)
assert row_pattern, (
    "FT1: features table row must wire hx-get='/ui/file/Alpha/Mod/case.feature' "
    "+ hx-target='#main-pane' + hx-swap='innerHTML' (click opens file editor "
    "in main pane)"
)

# File-name cell shows the leaf as-is.
row = re.search(
    r'<tr[^>]*hx-get="/ui/file/Alpha/Mod/case\.feature"[^>]*>(.*?)</tr>',
    html,
    re.DOTALL,
).group(1)
assert "case.feature" in row, (
    "FT1: features table row must show the file name 'case.feature' as-is in "
    "the File-name cell"
)
print("PASS  FT1: features-table row hx-get -> /ui/file/<path>; file name shown as-is")
