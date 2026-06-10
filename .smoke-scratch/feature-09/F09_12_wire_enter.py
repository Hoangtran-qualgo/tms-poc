# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / WS1 + IF2 -- Enter fires immediately.

Static JS inspection of `tmsWireSearch` in app/static/app.js.

WS1: a `keydown` listener on #search-q fires on Enter — it cancels any
     pending debounce timer and calls fire() immediately.
IF2: Enter cancels the pending debounce (clearTimeout + null) before
     firing, so a queued debounce can't double-fire afterwards.
"""
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(_p.read_text() for _p in sorted((REPO_ROOT / "app" / "static").glob("*.js")))


def _wire_body() -> str:
    m = re.search(r"function tmsWireSearch\(\)\s*\{", JS)
    assert m, "tmsWireSearch must be defined in app.js"
    i = m.end()
    depth = 1
    while i < len(JS) and depth > 0:
        c = JS[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return JS[m.start():i]


body = _wire_body()

# --- WS1: keydown listener on the query input, branching on Enter. ---
assert re.search(r'q\.addEventListener\(\s*"keydown"', body), (
    "WS1: tmsWireSearch must register a 'keydown' listener on #search-q"
)
m = re.search(r'q\.addEventListener\(\s*"keydown"[\s\S]*?\}\s*\)\s*;', body)
keydown = m.group(0)
assert re.search(r'e\.key\s*===?\s*"Enter"', keydown), (
    "WS1: the keydown handler must branch on `e.key === 'Enter'`"
)

# --- IF2: Enter cancels the pending debounce before firing. ---
assert re.search(
    r'e\.key\s*===?\s*"Enter"[\s\S]*?clearTimeout\(\s*debounceTimer\s*\)[\s\S]*?debounceTimer\s*=\s*null[\s\S]*?fire\(\s*\)',
    keydown,
), (
    "IF2: on Enter the handler must clearTimeout(debounceTimer), null it, "
    "then call fire() immediately"
)

print("PASS  WS1 + IF2: #search-q keydown on Enter cancels the pending debounce timer and fires immediately")
