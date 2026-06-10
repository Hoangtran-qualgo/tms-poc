# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / WS2 + IF3 -- input debounce.

Static JS inspection of `tmsWireSearch` in app/static/app.js.

WS2: an `input` listener on #search-q schedules fire() after a delay
     via scheduleFire(), which clears any prior timer first (so fast
     typing collapses to a single fire).
IF3: the debounce delay is exactly 300 ms and is the only debounce
     (hard-coded, not configurable).
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

# --- WS2: input listener schedules a (debounced) fire. ---
m = re.search(r'q\.addEventListener\(\s*"input"\s*,\s*\(\s*\)\s*=>\s*([^)]*)\)', body)
assert m, "WS2: tmsWireSearch must register an 'input' listener on #search-q"
assert "scheduleFire" in m.group(1), (
    "WS2: the input handler must call scheduleFire() (debounced), not fire() directly"
)

# --- IF3: 300 ms debounce, passed to scheduleFire from the input handler. ---
assert re.search(r'scheduleFire\(\s*300\s*\)', body), (
    "IF3: the input handler must schedule the fire with a 300 ms delay"
)

# --- WS2: scheduleFire clears the prior timer (collapses fast typing). ---
sf = re.search(r'function scheduleFire\([^)]*\)\s*\{[\s\S]*?\}', body).group(0)
assert "clearTimeout" in sf and "setTimeout" in sf, (
    "WS2: scheduleFire must clearTimeout(prev) then setTimeout(fire, delay) "
    "so a fast burst collapses to one fire"
)

# --- IF3: 300 is the ONLY numeric debounce literal in the wiring. ---
delays = re.findall(r'scheduleFire\(\s*(\d+)\s*\)', body)
assert delays == ["300"], (
    f"IF3: 300 ms must be the only debounce delay (not configurable), got {delays}"
)

print("PASS  WS2 + IF3: #search-q input schedules a single debounced fire after exactly 300 ms")
