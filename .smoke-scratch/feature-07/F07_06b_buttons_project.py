# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Buttons by depth -- BD2 (project).

Depth 1 (project) -> `+ New module` button wired to
`tmsCreateModule('<project>')`.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    html = client.get("/ui/folder/Alpha").get_data(as_text=True)

# Header `+ New module` button wired to tmsCreateModule('Alpha').
m = re.search(
    r'<button[^>]*onclick="tmsCreateModule\(\'Alpha\'\)"[^>]*>\+ New module</button>',
    html,
)
assert m, (
    "BD2: depth-1 (project) must render a `+ New module` button with "
    "onclick=\"tmsCreateModule('Alpha')\" in the header (project name passed "
    "as the parent argument)"
)
print("PASS  BD2: depth-1 project header carries `+ New module` -> tmsCreateModule('<project>')")
