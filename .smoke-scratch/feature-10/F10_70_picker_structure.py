# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / CP1 + CP2 + CP4 -- picker table structure.

CP1: the case list is sorted by folder_path ASC then file_name ASC.
     (The sort lives in tmsFetchProjectFeaturePaths, which feeds the
     picker; the picker renders rows in that order.)
CP2: the picker has a sticky table header inside a max-h-72 scroll box.
CP4: clicking anywhere on a row (not just the checkbox) toggles it.

Static JS inspection of app/static/app.js.
"""
import re
import pathlib

JS = "\n".join(_p.read_text() for _p in sorted(pathlib.Path("app/static").glob("*.js")))

# --- CP1: folder-then-file ASC sort in tmsFetchProjectFeaturePaths. ---
fetch_fn = re.search(
    r"async function tmsFetchProjectFeaturePaths\(project\)\s*\{.*?\n\}",
    JS, re.DOTALL).group(0)
assert "out.sort(" in fetch_fn, "feature list must be sorted before rendering"
assert "a.folder_path !== b.folder_path" in fetch_fn
assert "a.folder_path < b.folder_path ? -1 : 1" in fetch_fn
assert re.search(r"a\.file_name < b\.file_name \? -1 : a\.file_name > b\.file_name \? 1 : 0", fetch_fn)

# Scope the rest to the picker body.
picker = re.search(r"function tmsBuildCasePicker\(features, opts = \{\}\)\s*\{.*?\n\}",
                   JS, re.DOTALL).group(0)

# --- CP2: sticky header inside a max-h-72 scroll container. ---
assert "max-h-72 overflow-auto" in picker, "scroll container must cap height at max-h-72"
assert "sticky top-0" in picker, "table header must be sticky"

# --- CP4: click-row-to-toggle (skip when the click is on the checkbox itself). ---
click = re.search(r'tbody\.addEventListener\("click",.*?\}\);', picker, re.DOTALL).group(0)
assert 'e.target.tagName === "INPUT"' in click, "raw checkbox clicks must not double-toggle"
assert "box.checked = !box.checked" in click, "row click must flip the checkbox"

print("PASS  CP1+CP2+CP4: folder/file ASC sort feeds picker; sticky header in max-h-72 scroll; click-row-to-toggle")
