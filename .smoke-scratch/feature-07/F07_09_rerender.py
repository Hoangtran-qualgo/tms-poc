# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Re-render trigger (RR1).

The main pane is NOT SSE-wired in v1; only the tree pane is. Folder
views update only when (a) the user navigates via HTMX click, (b)
`tmsRefreshFolder(folderPath)` is called by JS after a CRUD operation,
or (c) the user clicks the tree refresh and then re-navigates.

Tested as a Hybrid: render-and-grep on `/` for the `<main id="main-pane">`
attributes + static inspection of `app/static/app.js` for the
`tmsRefreshFolder` function body and the absence of any sse:change
handler that would refetch `#main-pane`.
"""
import pathlib
import re
import tempfile

from app import create_app


REPO = pathlib.Path(__file__).resolve().parents[2]
JS = (REPO / "app" / "static" / "app.js").read_text()


# --- RR1 (a): <main id="main-pane"> does NOT subscribe to sse:change. ---
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    html = app.test_client().get("/").get_data(as_text=True)

main_tag = re.search(r'<main[^>]*id="main-pane"[^>]*>', html)
assert main_tag, "RR1 setup: <main id=\"main-pane\"> must exist on first paint"
tag = main_tag.group(0)
assert 'hx-trigger="sse:change"' not in tag, (
    f"RR1: <main id=\"main-pane\"> must NOT carry hx-trigger=\"sse:change\" "
    f"(only #tree-pane is SSE-wired per spec); got {tag!r}"
)
assert "sse-swap" not in tag, (
    f"RR1: <main id=\"main-pane\"> must NOT carry sse-swap (no per-event "
    f"swap from SSE); got {tag!r}"
)

# --- RR1 (b): tmsRefreshFolder exists and issues GET /ui/folder/<path>. -
assert re.search(
    r"function\s+tmsRefreshFolder\s*\(\s*folderPath\s*\)",
    JS,
), (
    "RR1: app.js must define `function tmsRefreshFolder(folderPath)` so JS "
    "CRUD callers can request a folder-view re-render"
)
# Extract tmsRefreshFolder's body and assert it builds a /ui/folder/<path>
# URL + issues htmx.ajax("GET", <url>, ...). Don't pin the exact URL-build
# syntax (`const url = "/ui/folder/" + (folderPath || "");` vs an inline
# concatenation) -- pin only the semantic shape.
m = re.search(
    r"function\s+tmsRefreshFolder\s*\(\s*folderPath\s*\)\s*\{([^}]*)\}",
    JS,
)
assert m, "RR1 setup: tmsRefreshFolder body must be extractable"
body = m.group(1)
assert '"/ui/folder/"' in body, (
    f"RR1: tmsRefreshFolder body must build a URL starting with '/ui/folder/'; "
    f"got body {body!r}"
)
assert "folderPath" in body, (
    f"RR1: tmsRefreshFolder body must reference the `folderPath` parameter "
    f"when building the URL; got body {body!r}"
)
assert re.search(r'htmx\.ajax\s*\(\s*"GET"', body), (
    f"RR1: tmsRefreshFolder must issue an htmx.ajax(\"GET\", ...) call "
    f"(this is the canonical re-render path); got body {body!r}"
)
assert re.search(
    r'target\s*:\s*"#main-pane"',
    JS,
), (
    "RR1: tmsRefreshFolder's htmx.ajax call must target `#main-pane` "
    "(the folder view's swap container)"
)

# --- RR1 (c): the body-level sse:change listener does NOT swap #main-pane.
sse_block = re.search(
    r'document\.body\.addEventListener\s*\(\s*"sse:change".*?\}\s*\)\s*;',
    JS,
    re.DOTALL,
)
assert sse_block, "RR1 setup: app.js must register a sse:change body listener"
handler_body = sse_block.group(0)
assert "main-pane" not in handler_body, (
    f"RR1: the body-level sse:change handler must NOT touch #main-pane "
    f"(folder views update only via explicit navigation or "
    f"tmsRefreshFolder); got handler body {handler_body!r}"
)
assert 'tmsRefreshFolder' not in handler_body, (
    f"RR1: the body-level sse:change handler must NOT call tmsRefreshFolder "
    f"(would silently SSE-wire the main pane); got handler body "
    f"{handler_body!r}"
)
print("PASS  RR1: <main id=main-pane> not SSE-wired; tmsRefreshFolder exists + targets #main-pane; sse:change handler does not touch main pane")
