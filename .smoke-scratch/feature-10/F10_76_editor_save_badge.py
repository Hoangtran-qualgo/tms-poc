# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / RE2 + RE4 + RE6 -- dirty / save / saved badge.

RE2: _refreshDirty() stringify-compares the live snapshot against
     baselineJson and _setDirty() toggles #run-dirty-indicator + the
     Save button's disabled attribute (set-and-forget).
RE4: save() PATCHes /api/runs/<p>/<g>/<file>; on success it updates
     baselineJson, clears dirty, and flashSaved(); on failure it
     alert()s and stays dirty (re-refreshes).
RE6: flashSaved() shows #run-saved-indicator for 1500 ms; any dirty
     edit clears it immediately (_setDirty -> _hideSavedBadge).

Static JS inspection of app/static/app.js.
"""
import re
import pathlib

JS = "\n".join(_p.read_text() for _p in sorted(pathlib.Path("app/static").glob("*.js")))


def body(method_re):
    m = re.search(method_re + r".*?\n  \},", JS, re.DOTALL)
    assert m, f"could not find {method_re!r}"
    return m.group(0)


# --- RE2: _setDirty toggles the indicator + Save disabled; hides badge when dirty. ---
set_dirty = body(r"_setDirty\(d\)\s*\{")
assert 'getElementById("run-dirty-indicator")' in set_dirty
assert 'getElementById("btn-run-save")' in set_dirty
assert re.search(r'dirtyEl\.classList\.toggle\("hidden",\s*!this\.state\.dirty\)', set_dirty)
assert re.search(r'saveBtn\.disabled\s*=\s*!this\.state\.dirty', set_dirty)
assert re.search(r"if\s*\(\s*this\.state\.dirty\s*\)\s*this\._hideSavedBadge\(\)", set_dirty)

# --- RE2: _refreshDirty compares the live snapshot vs the baseline.
#         E2: comparison is order-insensitive via _compareJson. ---
refresh = body(r"_refreshDirty\(\)\s*\{")
assert "this._compareJson(this._readCurrent())" in refresh
assert "this.state.baselineJson" in refresh and "this._setDirty(dirty)" in refresh

# --- RE4: save() PATCH + success/failure branches. ---
save = body(r"async save\(\)\s*\{")
assert re.search(r"if\s*\(\s*!this\.state\s*\|\|\s*!this\.state\.dirty\s*\)\s*return", save)
assert '`/api/runs/${project}/${group}/${file_name}`' in save
assert 'method: "PATCH"' in save
# success path
assert "this.state.baselineJson = this._compareJson(current)" in save
assert "this._setDirty(false)" in save and "this.flashSaved()" in save
# failure path
assert re.search(r"alert\(", save) and "this._refreshDirty()" in save

# --- RE6: flashSaved 1500ms + clear-on-dirty already asserted via _setDirty. ---
flash = body(r"flashSaved\(\)\s*\{")
assert 'getElementById("run-saved-indicator")' in flash
assert 'el.classList.remove("hidden")' in flash
assert re.search(r"setTimeout\([^,]+,\s*1500\)", flash), "saved badge must auto-hide after 1500ms"

print("PASS  RE2+RE4+RE6: dirty toggles indicator/Save; save() PATCH success/failure branches; saved badge 1.5s + clear-on-edit")
