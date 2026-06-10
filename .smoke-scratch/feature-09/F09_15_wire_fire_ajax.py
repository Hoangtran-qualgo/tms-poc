# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / WS4 -- fire() issues the htmx.ajax swap.

Static JS inspection of `tmsWireSearch`'s fire() closure in
app/static/app.js.

WS4: fire() builds a URLSearchParams from the four controls (q, scope,
     match, case) and calls
       htmx.ajax("GET", "/ui/search?...", { target: "#main-pane",
                                            swap: "innerHTML" })
     — the single code path that actually swaps the result partial
     into the main pane. case is serialised as the string
     "true"/"false" from the checkbox state.
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

fire = re.search(r'function fire\(\)\s*\{[\s\S]*?\n  \}', body)
assert fire, "WS4: tmsWireSearch must define a fire() closure"
fire = fire.group(0)

# --- WS4: params built from all four controls. ---
for field, expr in [
    ("q", r'q:\s*q\.value'),
    ("scope", r'scope:\s*scope\.value'),
    ("match", r'match:\s*match\.value'),
]:
    assert re.search(expr, fire), f"WS4: fire() params must include {field} from its control"
assert re.search(r'case:\s*caseChk\.checked\s*\?\s*"true"\s*:\s*"false"', fire), (
    "WS4: fire() must serialise case as the string 'true'/'false' from caseChk.checked"
)

# --- WS4: the htmx.ajax GET /ui/search swap into #main-pane. ---
assert re.search(r'htmx\.ajax\(\s*"GET"\s*,\s*"/ui/search\?"', fire), (
    "WS4: fire() must call htmx.ajax GET on /ui/search with the query string"
)
assert re.search(r'target:\s*"#main-pane"', fire), (
    "WS4: the htmx.ajax swap must target #main-pane"
)
assert re.search(r'swap:\s*"innerHTML"', fire), (
    "WS4: the htmx.ajax swap must use swap: 'innerHTML'"
)

print("PASS  WS4: fire() serialises q/scope/match/case and htmx.ajax-swaps /ui/search into #main-pane")
