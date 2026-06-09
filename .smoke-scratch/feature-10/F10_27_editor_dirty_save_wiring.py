"""3.D — Wiring smoke for the run editor controller.

Pure-JS interactions (typing → dirty → Save → flash Saved) need a
browser per the Phase-2 lock-in. This smoke verifies every static
artefact the controller depends on is present:

  - run_editor.html exposes data-created-at and calls tmsBootRunEditor().
  - app.js defines tmsRunEditor + tmsBootRunEditor.
  - htmx:afterSwap handler clears tmsRunEditor.state when #run-editor
    is no longer in the DOM.
  - beforeunload handler considers tmsRunEditor.state.dirty.
  - PATCH endpoint URL pattern matches the server route.
"""
import pathlib

APP_JS = pathlib.Path("app/static/app.js").read_text()
TPL = pathlib.Path("app/templates/run_editor.html").read_text()

# --- Template artefacts -------------------------------------------------
assert 'data-created-at="{{ run.created_at }}"' in TPL, "data-created-at missing on #run-editor"
assert "tmsBootRunEditor()" in TPL, "tail <script> must call tmsBootRunEditor()"
print("PASS 3.D run_editor.html exposes created_at + tail boot script")

# --- Controller symbols -------------------------------------------------
for sym in [
    "const tmsRunEditor",
    "function tmsBootRunEditor(",
    " save() {",
    " reload() {",
    " flashSaved() {",
    "_refreshDirty()",
]:
    assert sym in APP_JS, f"missing JS symbol: {sym}"
print("PASS 3.D tmsRunEditor controller symbols present")

# --- htmx:afterSwap cleans up tmsRunEditor.state ------------------------
assert (
    'if (!document.getElementById("run-editor"))' in APP_JS
), "afterSwap should drop tmsRunEditor.state when editor is gone"
assert "tmsRunEditor.state = null" in APP_JS, "state must be cleared after swap"
print("PASS 3.D htmx:afterSwap cleans up run editor state")

# --- beforeunload considers run-editor dirty ----------------------------
assert (
    "tmsRunEditor.state && tmsRunEditor.state.dirty" in APP_JS
), "beforeunload must consider tmsRunEditor.state.dirty"
print("PASS 3.D beforeunload guards run editor dirty state")

# --- PATCH URL pattern matches the server route -------------------------
assert "/api/runs/${project}/${group}/${file_name}" in APP_JS, "PATCH URL pattern wrong"
print("PASS 3.D PATCH URL pattern matches server route")
