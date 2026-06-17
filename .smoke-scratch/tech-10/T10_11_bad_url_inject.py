"""T10-11 — main-pane error injection wiring (tech-10 phase 10c, static).

htmx doesn't swap 4xx/5xx by default, so a failing #main-pane fetch (e.g. a
deep-linked / pasted URL to a missing item) would leave the pane stuck on
"Loading…". A scoped htmx:responseError listener injects the server's error
snippet into #main-pane and drops stale editor state. JS runtime isn't
available here -> static wiring.
"""
import pathlib
import re

JS = pathlib.Path("app/static/09_bootstrap.js").read_text()

m = re.search(
    r'addEventListener\("htmx:responseError"[\s\S]*?\n\}\);',
    JS,
)
assert m, "must register an htmx:responseError listener"
body = m.group(0)

# Scoped to #main-pane only (must not change error handling elsewhere).
assert 'target.id === "main-pane"' in body, "listener must be scoped to #main-pane"
# Injects the server response body into the pane.
assert "innerHTML = d.xhr.responseText" in body, (
    "must inject the server error snippet (xhr.responseText) into the pane"
)
# Drops stale editor state (the editor DOM was just replaced by the snippet).
assert "tmsEditor.state = null" in body and "tmsRunEditor.state = null" in body, (
    "must clear stale editor state after replacing the editor with an error"
)
print("PASS T10-11 htmx:responseError injects error into #main-pane (scoped)")
