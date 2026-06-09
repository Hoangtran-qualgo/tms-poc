# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Buttons by depth -- BD4 (sub-folder).

Depth 3..10 (sub-folder) -> BOTH `+ Sub-folder` and `+ Create test case`
buttons (same as BD3). Tested at extremes depth=3 and depth=10.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    chain = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]  # depth 1..10
    for i in range(1, len(chain) + 1):
        client.post(
            "/api/folders",
            json={"parent": "/".join(chain[: i - 1]), "name": chain[i - 1]},
        )

    for depth in (3, 10):  # extremes of the 3..10 range
        path = "/".join(chain[:depth])
        html = client.get(f"/ui/folder/{path}").get_data(as_text=True)
        sub_btn = re.search(
            rf'<button[^>]*onclick="tmsCreateSubfolder\(\'{re.escape(path)}\'\)"'
            rf'[^>]*>\+ Sub-folder</button>',
            html,
        )
        assert sub_btn, (
            f"BD4 (depth {depth}): folder_subfolder.html must render a "
            f"`+ Sub-folder` header button with "
            f"onclick=\"tmsCreateSubfolder('{path}')\""
        )
        file_btn = re.search(
            rf'<button[^>]*onclick="tmsCreateFile\(\'{re.escape(path)}\'\)"'
            rf'[^>]*>\+ Create test case</button>',
            html,
        )
        assert file_btn, (
            f"BD4 (depth {depth}): folder_subfolder.html must render a "
            f"`+ Create test case` header button with "
            f"onclick=\"tmsCreateFile('{path}')\""
        )
print("PASS  BD4: depth-3 and depth-10 sub-folders carry BOTH `+ Sub-folder` and `+ Create test case` header buttons")
