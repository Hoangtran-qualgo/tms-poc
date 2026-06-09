# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / W1 + W2 -- wiring.

Static JS inspection of the two body-level event listeners that wire
the editor controller to global page events.

W1: `htmx:afterSwap` on `#main-pane` clears `tmsEditor.state` when the
    main pane swaps to anything OTHER than the editor (the partial
    swap drops #file-editor).

W2: `sse:change` on document.body calls `tmsEditor.onExternalChange()`
    when `tmsEditor.state` is non-null.
"""
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = (REPO_ROOT / "app" / "static" / "app.js").read_text()


def _extract_listener(event: str) -> str:
    pat = re.compile(
        rf'document\.body\.addEventListener\(\s*"{re.escape(event)}"\s*,\s*',
    )
    m = pat.search(JS)
    assert m, f"wiring: document.body must register a {event!r} listener"
    # Walk to the closing `)` of the addEventListener call.
    i = m.end()
    # Skip whitespace, then expect `(` of the arrow function.
    while i < len(JS) and JS[i].isspace():
        i += 1
    # Find matching `)` for addEventListener.
    depth = 1  # we are inside the addEventListener( ... )
    start = m.start()
    j = m.end()
    while j < len(JS) and depth > 0:
        c = JS[j]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        j += 1
    return JS[start:j]


# --- W1: htmx:afterSwap on body, main-pane branch clears tmsEditor.state ---
w1 = _extract_listener("htmx:afterSwap")
# Must check that the swap target was #main-pane.
assert re.search(r'e\.target\.id\s*===?\s*"main-pane"', w1), (
    "W1: htmx:afterSwap listener must branch on `e.target.id === 'main-pane'`"
)
# In the main-pane branch, must clear tmsEditor.state when #file-editor
# is NOT present in the DOM.
assert re.search(
    r'!\s*document\.getElementById\(\s*"file-editor"\s*\)[\s\S]{0,200}?tmsEditor\.state\s*=\s*null',
    w1,
), (
    "W1: htmx:afterSwap on #main-pane must clear `tmsEditor.state = null` "
    "when #file-editor is no longer in the DOM"
)


# --- W2: sse:change on body calls tmsEditor.onExternalChange when state set
w2 = _extract_listener("sse:change")
assert re.search(
    r'if\s*\(\s*tmsEditor\.state\s*\)\s*tmsEditor\.onExternalChange\(\s*\)',
    w2,
), (
    "W2: sse:change listener must call `tmsEditor.onExternalChange()` "
    "guarded by `if (tmsEditor.state)`"
)

print("PASS  W1 + W2: body-level htmx:afterSwap clears tmsEditor.state off-editor; sse:change calls onExternalChange when state is set")
