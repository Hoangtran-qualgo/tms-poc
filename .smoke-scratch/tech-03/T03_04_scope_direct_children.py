# Pattern: see .smoke-scratch/README.md
"""tech-03 / folder bulk-actions / scope = DIRECT children only.

The toolbar acts on the folder's direct test cases only, never on cases in
sub-folders. Seed Alpha/Mod with a direct case `a` and a sub-folder
Alpha/Mod/Sub holding `b`. The module view's selectable checkboxes must
include `a` and MUST NOT include the sub-folder's `b`.
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
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "a", "description": "x"},
    )
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod/Sub", "file_name": "b", "description": "y"},
    )
    html = client.get("/ui/folder/Alpha/Mod").get_data(as_text=True)

case_paths = set(re.findall(r'data-case-path="([^"]+)"', html))
assert "Alpha/Mod/a.feature" in case_paths, (
    f"the direct case must be selectable; got {case_paths}"
)
assert "Alpha/Mod/Sub/b.feature" not in case_paths, (
    f"sub-folder cases must NOT be selectable from the parent view; got {case_paths}"
)
assert case_paths == {"Alpha/Mod/a.feature"}, (
    f"only direct children should have checkboxes; got {case_paths}"
)
print("PASS  T03_04: bulk selection is scoped to direct children (sub-folder cases excluded)")
