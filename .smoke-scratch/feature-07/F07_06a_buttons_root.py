# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Buttons by depth -- BD1 (root).

Depth 0 (root) -> `+ New project` button wired to `tmsCreateProject()`.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    html = app.test_client().get("/ui/folder/").get_data(as_text=True)

# Header `+ New project` button wired to tmsCreateProject().
m = re.search(
    r'<button[^>]*onclick="tmsCreateProject\(\)"[^>]*>\+ New project</button>',
    html,
)
assert m, (
    "BD1: depth-0 (root) must render a `+ New project` button with "
    "onclick=\"tmsCreateProject()\" in the header. Folder views are pure UI; "
    "they don't mutate -- the button just invokes the JS helper from "
    "feature-04."
)
print("PASS  BD1: depth-0 root header carries `+ New project` -> tmsCreateProject()")
