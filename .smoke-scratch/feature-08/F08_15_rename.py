# Pattern: see .smoke-scratch/README.md
"""feature-08 / filename rename now belongs in the folder-detail UI."""
import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EDITOR_JS = (REPO_ROOT / "app" / "static" / "08_file_editor.js").read_text()
FOLDER_JS = (REPO_ROOT / "app" / "static" / "03_folder_actions.js").read_text()
TEMPLATE = (REPO_ROOT / "app" / "templates" / "file_editor.html").read_text()


assert "async rename()" not in EDITOR_JS, "RN1: editor must not own rename()"
assert 'id="btn-rename"' not in TEMPLATE, "RN2: editor must not render Rename"
assert "function tmsRenameFile(filePath, currentName)" in FOLDER_JS
assert "tmsOpenModal" in FOLDER_JS
assert '"/api/files/" + tmsEncodePath(filePath) + "/rename"' in FOLDER_JS
assert "tmsRefreshFolder" in FOLDER_JS and "tmsRefreshTreePane" in FOLDER_JS

print("PASS  RN1-RN3: folder detail owns modal file rename; editor has none")
