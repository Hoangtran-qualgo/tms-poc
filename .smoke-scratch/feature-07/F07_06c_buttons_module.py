# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Buttons by depth -- BD3 (module).

Depth 2 (module) -> BOTH `+ Sub-folder` and `+ Create test case` buttons
in the header, wired to `tmsCreateSubfolder('<parent>')` and
`tmsCreateFile('<parent>')` respectively.
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
    html = client.get("/ui/folder/Alpha/Mod").get_data(as_text=True)

# `+ Sub-folder` button wired to tmsCreateSubfolder with the module path.
sub_btn = re.search(
    r'<button[^>]*onclick="tmsCreateSubfolder\(\'Alpha/Mod\'\)"[^>]*>\+ Sub-folder</button>',
    html,
)
assert sub_btn, (
    "BD3: depth-2 module must render a `+ Sub-folder` header button with "
    "onclick=\"tmsCreateSubfolder('Alpha/Mod')\" (parent path passed verbatim)"
)

# `+ Create test case` button wired to tmsCreateFile with the module path.
file_btn = re.search(
    r'<button[^>]*onclick="tmsCreateFile\(\'Alpha/Mod\'\)"[^>]*>\+ Create test case</button>',
    html,
)
assert file_btn, (
    "BD3: depth-2 module must render a `+ Create test case` header button "
    "with onclick=\"tmsCreateFile('Alpha/Mod')\" (parent path passed verbatim)"
)
print("PASS  BD3: depth-2 module header carries BOTH `+ Sub-folder` -> tmsCreateSubfolder + `+ Create test case` -> tmsCreateFile")
