# Pattern: see .smoke-scratch/README.md
"""feature-06 / tree-pane / base.html wiring (WR1-WR3).

Renders the page shell at `/` and asserts the SSE subscription on
`<body>` + the tree-pane aside's HTMX wiring + the tree-pane /
test-run-pane sibling layout inside `#sidebar-panels`.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    html = client.get("/").get_data(as_text=True)

# --- WR1: <body hx-ext="sse" sse-connect="/api/events"> ----------------
body = re.search(r"<body[^>]*>", html)
assert body, "WR1 setup: base.html must render a `<body>` element"
body_tag = body.group(0)
assert 'hx-ext="sse"' in body_tag, (
    f"WR1: <body> must carry hx-ext=\"sse\" (page-wide SSE subscription); "
    f"got {body_tag!r}"
)
assert 'sse-connect="/api/events"' in body_tag, (
    f"WR1: <body> must carry sse-connect=\"/api/events\"; got {body_tag!r}"
)

# --- WR2: <aside id="tree-pane"> with hx-get/hx-trigger/hx-swap. ---------
tree_pane = re.search(r'<aside\s+id="tree-pane"[^>]*>', html)
assert tree_pane, "WR2: <aside id=\"tree-pane\"> element must exist in base.html"
tag = tree_pane.group(0)
for attr in (
    'hx-get="/ui/tree"',
    'hx-trigger="sse:change"',
    'hx-swap="innerHTML"',
):
    assert attr in tag, (
        f"WR2: <aside id=\"tree-pane\"> must carry {attr} "
        f"(SSE-driven full-partial swap); got {tag!r}"
    )

# --- WR3: tree-pane + test-run-pane siblings inside #sidebar-panels. ----
panels_open = html.find('<div id="sidebar-panels"')
assert panels_open != -1, (
    "WR3: <div id=\"sidebar-panels\"> wrapper must exist in the page shell"
)
# Both <aside>s must appear AFTER the wrapper opens and before the
# sidebar resize handle (which closes the sidebar block).
resize_handle = html.find('id="sidebar-resize-handle"', panels_open)
assert resize_handle != -1, (
    "WR3: #sidebar-resize-handle must exist after #sidebar-panels"
)
inner = html[panels_open:resize_handle]
tree_idx = inner.find('<aside id="tree-pane"')
run_idx = inner.find('<aside id="test-run-pane"')
assert tree_idx != -1, (
    "WR3: #sidebar-panels must contain <aside id=\"tree-pane\">"
)
assert run_idx != -1, (
    "WR3: #sidebar-panels must contain <aside id=\"test-run-pane\"> as a sibling"
)
assert tree_idx < run_idx, (
    "WR3: <aside id=\"tree-pane\"> must precede <aside id=\"test-run-pane\"> "
    "inside #sidebar-panels (Directory tab is active-by-default and ordered first)"
)

# WR3: test-run-pane is hidden by default and lazy-mounted
# (no hx-trigger until first activation).
test_run = re.search(r'<aside\s+id="test-run-pane"[^>]*>', inner)
assert test_run, "WR3: <aside id=\"test-run-pane\"> element must exist"
test_run_tag = test_run.group(0)
assert "hidden" in test_run_tag, (
    f"WR3: <aside id=\"test-run-pane\"> must carry the 'hidden' class by "
    f"default (lazy-mount); got {test_run_tag!r}"
)
assert "hx-trigger" not in test_run_tag, (
    f"WR3: <aside id=\"test-run-pane\"> must NOT carry hx-trigger on initial "
    f"render (subscribes only after tab activation); got {test_run_tag!r}"
)
print("PASS  WR1-WR3: <body> SSE subscription; #tree-pane HTMX wiring; sibling #test-run-pane hidden + lazy")
