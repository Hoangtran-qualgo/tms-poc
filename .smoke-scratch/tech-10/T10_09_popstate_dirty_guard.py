"""T10-09 — in-app Back/Forward dirty guard (tech-10 phase 10c, static).

Under D2 a Back/Forward is a full reload, so the popstate has already moved the
address bar by the time beforeunload fires. The guard wraps htmx's
window.onpopstate: confirm on a dirty editor, re-push the editor URL on cancel
(undo the popstate), and clear dirty on confirm so the reload's beforeunload is
silent (no double prompt). JS runtime isn't available here -> static wiring.
"""
import pathlib
import re

JS = pathlib.Path("app/static/09_bootstrap.js").read_text()

# Reconstructs both editors' /ui URLs.
m = re.search(r"function tmsCurrentEditorUrl\(\)\s*\{[\s\S]*?\n\}", JS)
assert m, "tmsCurrentEditorUrl() not found"
url_fn = m.group(0)
assert "/ui/run/" in url_fn and "/ui/file/" in url_fn, url_fn
assert "tmsRunEditor.state" in url_fn and "tmsEditor.state" in url_fn, url_fn
print("PASS tmsCurrentEditorUrl reconstructs run + file editor URLs")

# Wraps htmx's popstate handler (saves + conditionally delegates).
assert "window.onpopstate = function" in JS, "must wrap window.onpopstate"
assert re.search(r"const\s+tmsHtmxOnPopstate\s*=\s*window\.onpopstate", JS), (
    "must preserve htmx's original onpopstate handler"
)
assert "tmsHtmxOnPopstate.call(this, event)" in JS, (
    "must delegate to htmx's handler for the non-dirty / confirmed path"
)
print("PASS wraps + delegates to htmx's popstate handler")

# Dirty branch: confirm, re-push on cancel, clear dirty on confirm.
assert "window.confirm(" in JS, "must confirm before discarding a dirty editor"
assert re.search(r'history\.pushState\(\s*\{\s*htmx:\s*true\s*\}\s*,\s*"",\s*editorUrl\)', JS), (
    "on cancel must re-push the editor URL to undo the popstate"
)
assert "tmsRunEditor.state.dirty = false" in JS and "tmsEditor.state.dirty = false" in JS, (
    "on confirm must clear dirty so the reload's beforeunload stays silent"
)
print("PASS dirty branch: confirm + re-push on cancel + clear-dirty on confirm")
