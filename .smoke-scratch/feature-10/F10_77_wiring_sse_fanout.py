# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / WR1 + WR2 + WR3 -- bottom-of-file wiring.

WR1: the body-level `htmx:afterSwap` handler clears tmsRunEditor.state
     when #run-editor is no longer in the main pane.
WR2: the body-level `sse:change` handler fans out to BOTH
     tmsEditor.onExternalChange() and tmsRunEditor.onExternalChange(),
     each guarded by its controller's non-null state.
WR3: the `beforeunload` handler warns when EITHER editor's state.dirty.

Static JS inspection of app/static/app.js (the wiring block at the
bottom of the file).
"""
import re
import pathlib

JS = pathlib.Path("app/static/app.js").read_text()

# --- WR1: afterSwap clears tmsRunEditor.state when the editor left. ---
after = re.search(r'addEventListener\("htmx:afterSwap".*?\}\);', JS, re.DOTALL).group(0)
assert 'document.getElementById("run-editor")' in after
assert re.search(r'if\s*\(\s*!document\.getElementById\("run-editor"\)\s*\)\s*\{\s*\n\s*tmsRunEditor\.state\s*=\s*null', after)

# --- WR2: sse:change fans out to BOTH editors, each state-guarded. ---
sse = re.search(r'addEventListener\("sse:change".*?\}\);', JS, re.DOTALL).group(0)
assert re.search(r"if\s*\(\s*tmsEditor\.state\s*\)\s*tmsEditor\.onExternalChange\(\)", sse), sse
assert re.search(r"if\s*\(\s*tmsRunEditor\.state\s*\)\s*tmsRunEditor\.onExternalChange\(\)", sse), sse

# --- WR3: beforeunload guards both editors' dirty state. ---
unload = re.search(r'addEventListener\("beforeunload".*?\}\);', JS, re.DOTALL).group(0)
assert "tmsEditor.state && tmsEditor.state.dirty" in unload
assert "tmsRunEditor.state && tmsRunEditor.state.dirty" in unload

print("PASS  WR1+WR2+WR3: afterSwap clears run-editor state; sse:change fans out to both editors; beforeunload guards both")
