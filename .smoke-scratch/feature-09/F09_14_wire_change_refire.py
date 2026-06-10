# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / WS3 + IF1 -- scope/match/case change re-fire.

Static JS inspection of `tmsWireSearch` in app/static/app.js.

WS3: scope / match / case each get a `change` listener that fires
     immediately (no debounce) when the query is non-empty.
IF1: the change handlers are guarded by `q.value.trim()` so an empty
     query never fires from a control change (avoids stale empty-state
     flashes); only a non-empty query re-fires.
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

# --- WS3: the change wiring iterates over scope, match and caseChk. ---
loop = re.search(
    r'for\s*\(\s*const\s+\w+\s+of\s*\[\s*([^\]]*)\]\s*\)\s*\{[\s\S]*?\}',
    body,
)
assert loop, "WS3: a for-of loop must wire the scope/match/case change listeners"
targets = {t.strip() for t in loop.group(1).split(",") if t.strip()}
assert targets == {"scope", "match", "caseChk"}, (
    f"WS3: the change loop must cover scope, match and caseChk, got {targets}"
)

# --- WS3: each iteration registers a 'change' listener. ---
assert re.search(r'\.addEventListener\(\s*"change"', loop.group(0)), (
    "WS3: the loop must register a 'change' listener on each control"
)

# --- IF1: the change handler fires only when q.value.trim() is truthy. ---
assert re.search(
    r'if\s*\(\s*q\.value\.trim\(\s*\)\s*\)\s*fire\(\s*\)',
    loop.group(0),
), (
    "IF1: the change handler must guard fire() behind `if (q.value.trim())` "
    "so an empty query never re-fires"
)

print("PASS  WS3 + IF1: scope/match/case change listeners fire immediately, but only when the query is non-empty")
