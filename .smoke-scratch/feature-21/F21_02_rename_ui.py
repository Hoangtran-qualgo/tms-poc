# Pattern: see .smoke-scratch/README.md
"""feature-21 / rename controls live in folder views, not file editor."""

from pathlib import Path
from tempfile import TemporaryDirectory

from app import create_app


with TemporaryDirectory() as td:
    app = create_app(data_root=Path(td))
    storage = app.extensions["storage"]
    storage.create_folder(["project"])
    storage.create_folder(["project", "module"])
    storage.create_folder(["project", "module", "branch"])
    storage.create_file(["project", "module", "case.feature"], scenario_name="case")
    client = app.test_client()
    try:
        project_html = client.get("/ui/folder/project").get_data(as_text=True)
        module_html = client.get("/ui/folder/project/module").get_data(as_text=True)
        branch_html = client.get(
            "/ui/folder/project/module/branch"
        ).get_data(as_text=True)
        editor_html = client.get(
            "/ui/file/project/module/case.feature"
        ).get_data(as_text=True)
    finally:
        app.extensions["watcher"].stop()

assert 'data-folder-path="project"' in project_html
assert "Rename project" in project_html, "TU1: project page exposes Rename project"
assert "Rename folder" in module_html, "TU2: module page exposes Rename folder"
assert "Rename folder" in branch_html, "TU3: branch page exposes Rename folder"
assert 'data-file-path="project/module/case.feature"' in module_html, (
    "TU4: file rename action is in folder detail table"
)
assert 'onclick="tmsRenameFile(this.dataset.filePath, this.dataset.fileName)"' in module_html
assert 'id="btn-rename"' not in editor_html, (
    "TU5: file editor no longer owns rename action"
)
folder_actions = (Path(__file__).resolve().parents[2] / "app" / "static" / "03_folder_actions.js").read_text()
assert "window.location.assign" in folder_actions, "TU6: project rename must fully navigate"
assert "window.history.pushState" in folder_actions, (
    "TU7: nested folder rename must replace the browser URL"
)

print("PASS  TU1-TU7: rename controls render in approved folder locations")
