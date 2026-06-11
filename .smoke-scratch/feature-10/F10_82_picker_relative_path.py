# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / case-picker shows project-relative paths.

The project is already chosen in the create-run / add-case modal, so the
picker drops the redundant `<project>/` prefix and shows the folder from
the module level down. The stored value (tr.dataset.path) stays the full
data-root path so the run still references the case by its real file_path.

Static JS inspection of app/static/*.js.
"""
import re
import pathlib

JS = "\n".join(_p.read_text() for _p in sorted(pathlib.Path("app/static").glob("*.js")))

# --- tmsFetchProjectFeaturePaths derives the project-relative fields. ---
fetch_fn = re.search(
    r"async function tmsFetchProjectFeaturePaths\(project\)\s*\{.*?\n\}",
    JS, re.DOTALL).group(0)
assert 'const prefix = project + "/";' in fetch_fn, "missing project prefix"
assert "rel_path:" in fetch_fn, "rel_path field not derived"
assert "rel_folder:" in fetch_fn, "rel_folder field not derived"
# Full path/folder are still carried for the stored value + sort.
assert "folder_path," in fetch_fn and "out.sort(" in fetch_fn
print("PASS  tmsFetchProjectFeaturePaths derives rel_path/rel_folder, keeps full path + sort")

# --- The picker DISPLAYS the relative folder, VALUE stays the full path. ---
picker = re.search(r"function tmsBuildCasePicker\(features, opts = \{\}\)\s*\{.*?\n\}",
                   JS, re.DOTALL).group(0)
assert "const relFolder = f.rel_folder" in picker, "picker must prefer rel_folder"
assert "tr.children[1].textContent = relFolder;" in picker, "Folder column must show relFolder"
assert "tr.dataset.path = f.path;" in picker, "stored value must stay the full path"
# The folder display/filter must not fall back to the full data-root folder.
assert "tr.children[1].textContent = f.folder_path" not in picker, (
    "Folder column still shows the full data-root folder_path"
)
print("PASS  picker shows module-level rel_folder; row value stays the full path")
