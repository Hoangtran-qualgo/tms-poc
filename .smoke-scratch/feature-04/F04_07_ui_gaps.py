# Pattern: see .smoke-scratch/README.md
"""feature-04 / folder-crud / rename UI (UG1)."""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post("/api/folders", json={"parent": "Alpha/Mod", "name": "Sub"})
    try:
        root_html = client.get("/ui/folder/").get_data(as_text=True)
        project_html = client.get("/ui/folder/Alpha").get_data(as_text=True)
        module_html = client.get("/ui/folder/Alpha/Mod").get_data(as_text=True)
        subfolder_html = client.get(
            "/ui/folder/Alpha/Mod/Sub"
        ).get_data(as_text=True)
    finally:
        app.extensions["watcher"].stop()

assert "tmsRenameFolder" not in root_html, "UG1: root has no folder rename"
assert "Rename project" in project_html, "UG1: project exposes Rename project"
assert "tmsRenameFolder" in project_html
for html, name in ((module_html, "module"), (subfolder_html, "sub-folder")):
    assert "Rename folder" in html, f"UG1: {name} exposes Rename folder"
    assert "tmsRenameFolder" in html

print("PASS  UG1: project/module/sub-folder rename controls render; root has none")
