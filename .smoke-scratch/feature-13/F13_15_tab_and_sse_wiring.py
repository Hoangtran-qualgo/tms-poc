"""S4 smoke — Enums tab + manager + editor SSE wiring (static touch-points).

Asserts the front-end wiring exists and is consistent:
1. base.html has the 4th Enums tab button + #enums-pane + the manager script.
2. 02_sidebar.js toggles the enums pane and lazy-mounts tmsActivateEnumsPane
   against /ui/enums-tree with an sse:change trigger.
3. 08_enums_manager.js exposes the tmsEnumsManager controller with PUT /
   rename / clear calls.
4. 08_file_editor.js refreshes the vocab cache on external change (D6) and
   exposes the openEnumsManager deep-link.
"""
import pathlib

ROOT = pathlib.Path("app")


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# --- 1. base.html shell ---------------------------------------------------
base = _read("templates/base.html")
assert 'data-sidebar-tab="enums"' in base, "missing Enums tab button"
assert "tmsSwitchSidebarTab('enums')" in base, "tab button not wired"
assert 'id="enums-pane"' in base, "missing #enums-pane"
assert "08_enums_manager.js" in base, "manager script not loaded"
# Bootstrap must still load last — compare the actual <script> tag positions
# (filename='...'), not the comment that also names 09_bootstrap.js.
assert (
    base.index("filename='08_enums_manager.js'")
    < base.index("filename='09_bootstrap.js'")
), "manager script must load before bootstrap"
print("PASS  base.html: Enums tab + pane + manager script (before bootstrap)")

# --- 2. 02_sidebar.js -----------------------------------------------------
sidebar = _read("static/02_sidebar.js")
assert "tmsActivateEnumsPane" in sidebar, "missing tmsActivateEnumsPane"
assert 'target !== "enums"' in sidebar, "enums pane not toggled in switcher"
assert "/ui/enums-tree" in sidebar, "enums tree not lazy-mounted"
assert 'if (target === "enums") tmsActivateEnumsPane();' in sidebar
print("PASS  02_sidebar.js: enums pane toggle + lazy mount + sse:change")

# --- 3. 08_enums_manager.js ----------------------------------------------
mgr = _read("static/08_enums_manager.js")
assert "tmsEnumsManager" in mgr, "missing controller"
assert '"PUT"' in mgr, "manager Save (PUT) missing"
assert "/rename" in mgr, "manager rename call missing"
assert "/clear" in mgr, "manager clear call missing"
# Single-entry remove validates usage up-front (block at click, not at Save).
assert "async _removeEntry" in mgr, "remove must be async (usage check)"
assert "/usage" in mgr, "remove must query the /usage endpoint"
print("PASS  08_enums_manager.js: controller with PUT/rename/clear + remove usage-check")

# --- 4. 08_file_editor.js D6 wiring --------------------------------------
editor = _read("static/08_file_editor.js")
assert "_refreshEnumsFromDisk" in editor, "missing D6 refresh method"
assert "this._refreshEnumsFromDisk();" in editor, "refresh not called on sse:change"
assert "delete tmsEditor._vocabCache[project]" in editor, "cache not invalidated"
assert "openEnumsManager" in editor, "missing editor deep-link"
print("PASS  08_file_editor.js: D6 vocab-cache refresh + openEnumsManager link")
