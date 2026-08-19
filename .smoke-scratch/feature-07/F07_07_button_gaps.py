# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / approved action scope (BD5)."""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    client = app.test_client()
    chain = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
    for i, name in enumerate(chain, start=1):
        client.post(
            "/api/folders",
            json={"parent": "/".join(chain[: i - 1]), "name": name},
        )
    client.post(
        "/api/files",
        json={
            "parent": "A/B",
            "file_name": "case",
            "scenario_name": "s",
            "description": "x",
        },
    )
    try:
        views = {
            depth: client.get(
                "/ui/folder/" + "/".join(chain[:depth]) if depth else "/ui/folder/"
            ).get_data(as_text=True)
            for depth in (0, 1, 2, 3, 10)
        }
    finally:
        app.extensions["watcher"].stop()

assert "tmsRenameFolder" not in views[0], "BD5: root has no folder rename"
assert "Rename project" in views[1] and "tmsRenameFolder" in views[1]
for depth in (2, 3, 10):
    assert "Rename folder" in views[depth], f"BD5: depth {depth} has folder rename"
    assert "Delete folder" in views[depth], f"BD5: depth {depth} has folder delete"
assert "tmsRenameFile" in views[2], "BD5: module file row owns filename rename"
for html in views.values():
    assert "tmsMoveFolder" not in html, "BD5: folder move remains absent"
    assert "tmsDeleteFile" not in html and "tmsDuplicateFile" not in html

print("PASS  BD5: approved folder/file rename scope; delete/move/duplicate boundaries hold")
