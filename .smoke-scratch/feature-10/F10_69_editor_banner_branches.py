# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / RE11 + RE12 -- external-change banner machine.

RE11: onExternalChange() branches three ways:
   1. run removed on disk (GET -> 404) -> red error banner
      "This run was removed on disk." + Discard -> _navigateToGroup()
      (which targets /ui/folder/<p>/test-run/<g>, the group view).
   2. changed AND not dirty -> silent _reloadAndAnnounce("info", ...).
   3. changed AND dirty -> amber warn banner with
      "Reload (discard mine)" + "Keep editing".
RE12: the disk response is projected into the same shape baselineJson
     uses (name/description/results[{file_path,result,remark}]) -- no
     created_at, no missing -- so the equality check is apples-to-apples.

Static JS inspection of app/static/app.js.
"""
import re
import pathlib

JS = "\n".join(_p.read_text() for _p in sorted(pathlib.Path("app/static").glob("*.js")))

m = re.search(r"async onExternalChange\(\)\s*\{.*?\n  \},", JS, re.DOTALL)
assert m, "tmsRunEditor.onExternalChange() must be defined"
fn = m.group(0)

# --- RE12: 404 detection + apples-to-apples projection.
#          E2: the disk shape is projected via _compareJson (same
#          order-insensitive projection the baseline uses). ---
assert re.search(r"r\.status\s*===\s*404", fn), "must detect removal via 404"
assert "this._compareJson({" in fn and "file_path: rr.file_path" in fn, fn
assert "created_at" not in fn.split("this._compareJson({", 1)[1].split("})", 1)[0], (
    "RE12: the disk projection must omit created_at (apples-to-apples with baseline)"
)
assert re.search(r"if\s*\(\s*diskJson\s*===\s*this\.state\.baselineJson\s*\)\s*return", fn)

# --- RE11 branch 1: removed -> error banner + Discard -> group nav. ---
assert 'kind: "error"' in fn and "This run was removed on disk." in fn
assert re.search(r'label:\s*"Discard"[\s\S]*?this\._navigateToGroup\(\)', fn)
nav = re.search(r"_navigateToGroup\(\)\s*\{.*?\n  \},", JS, re.DOTALL).group(0)
assert "/ui/folder/${project}/test-run/${group}" in nav, "Discard must navigate to the group view"

# --- RE11 branch 2: changed & clean -> silent reload + info. ---
assert re.search(r"if\s*\(\s*!this\.state\.dirty\s*\)", fn)
assert 'Run was updated externally; the editor reloaded.' in fn

# --- RE11 branch 3: changed & dirty -> warn banner + two actions. ---
assert 'kind: "warn"' in fn
assert "Run changed externally while you have unsaved changes." in fn
assert 'label: "Reload (discard mine)"' in fn
assert 'label: "Keep editing"' in fn

print("PASS  RE11+RE12: onExternalChange 3-branch banner machine (removed/clean/dirty) + apples-to-apples disk projection")
