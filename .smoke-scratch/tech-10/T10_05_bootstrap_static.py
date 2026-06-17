"""T10-05 — bootstrap static wiring (09_bootstrap.js).

History config (full-reload Back/Forward), expand-state seeding, tab restore,
and an explicit boot-time tree restore (the server-included tree never fires
htmx:afterSwap at boot). beforeunload dirty guard already existed (D7).
"""
import pathlib
import re

JS = pathlib.Path("app/static/09_bootstrap.js").read_text()

assert "historyCacheSize = 0" in JS, "must disable the history snapshot cache"
assert "refreshOnHistoryMiss = true" in JS, "Back/Forward must be a full reload"

m = re.search(r"function tmsBootShell\(\)\s*\{[\s\S]*?\n\}", JS)
assert m, "tmsBootShell not found"
body = m.group(0)
assert "TMS_EXPAND_PATHS" in body and "tmsExpandedFolders.add" in body, (
    "tmsBootShell must seed the directory-tree expand-state"
)
assert "tmsSwitchSidebarTab(tab)" in body and "window.TMS_ACTIVE_TAB" in body, (
    "tmsBootShell must activate the URL's sidebar tab"
)
assert "tmsRestoreTreeState()" in body, (
    "tmsBootShell must restore tree state at boot (afterSwap doesn't fire for "
    "the server-included tree)"
)
assert 'addEventListener("beforeunload"' in JS, "beforeunload dirty guard (D7)"
print("PASS T10-05 bootstrap: history config + seed + tab + restore + beforeunload")
