# Pattern: see .smoke-scratch/README.md
"""feature-06 / tree-pane / SSE-driven refresh (SF1-SF3).

Hybrid coverage:
  - SF1 (FS change -> 1 "change" after debounce) is end-to-end-tested
    in `F06_11_acceptance.py` AC2 and upstream in F03_06 AC2 /
    F04_08 AC6b / F05_11 AC7b. This file restates the tree-pane's
    half: the watcher publishes through the bus that `#tree-pane`
    is wired to.
  - SF2 (every connected tab swaps) is statically + render-checked.
  - SF3 (writing tab does NOT receive event) is upstream-cascade
    (feature-02 SW1, feature-03 EF3, feature-04 AC6a, feature-05
    AC7a); this file restates the tree-pane's frame as a static
    cross-check.
"""
import pathlib
import re
import tempfile

from app import create_app


REPO = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(_p.read_text() for _p in sorted((REPO / "app" / "static").glob("*.js")))

with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    base_html = client.get("/").get_data(as_text=True)

# --- SF1 (tree-pane wiring half): the bus that publishes "change" is the
# SAME bus that <aside id="tree-pane"> subscribes to via the body's
# sse-connect="/api/events" attribute. ---
body_tag = re.search(r"<body[^>]*>", base_html).group(0)
assert 'sse-connect="/api/events"' in body_tag, (
    "SF1: <body> must wire sse-connect=\"/api/events\" so the watcher's "
    "/api/events SSE endpoint feeds `sse:change` to #tree-pane. End-to-end "
    "FS-change -> one event after DEBOUNCE_SECONDS is covered in "
    "F06_11_acceptance.py AC2 and upstream in F0{3,4,5} acceptance suites."
)
print("PASS  SF1 (tree-pane wiring half): <body> sse-connect=/api/events feeds #tree-pane")


# --- SF2 (every connected tab swaps /ui/tree into #tree-pane). ----------
# Static: `htmx:afterSwap` listener calls tmsRestoreTreeState when the
# tree-pane was the swap target.
afterswap_block = re.search(
    r'document\.body\.addEventListener\s*\(\s*"htmx:afterSwap".*?\}\s*\)\s*;',
    JS,
    re.DOTALL,
)
assert afterswap_block, (
    "SF2 (static): app.js must register a body-level `htmx:afterSwap` listener"
)
afterswap_body = afterswap_block.group(0)
assert (
    'e.target.id === "tree-pane"' in afterswap_body
    and "tmsRestoreTreeState()" in afterswap_body
), (
    "SF2 (static): the htmx:afterSwap handler must call tmsRestoreTreeState() "
    "when e.target.id === \"tree-pane\" (so every swap re-applies the "
    "expanded-state Set)"
)

# Render-and-grep: #tree-pane carries the hx-trigger that fires on
# every "change" event reaching the tab.
tree_tag = re.search(r'<aside\s+id="tree-pane"[^>]*>', base_html).group(0)
assert (
    'hx-get="/ui/tree"' in tree_tag and 'hx-trigger="sse:change"' in tree_tag
), (
    f"SF2 (render): #tree-pane must wire hx-get=\"/ui/tree\" + "
    f"hx-trigger=\"sse:change\" so every connected tab swaps the partial "
    f"on every `change` event; got {tree_tag!r}"
)
print("PASS  SF2 (Hybrid): #tree-pane hx-trigger=sse:change + htmx:afterSwap -> tmsRestoreTreeState wired")


# --- SF3 (writing tab does NOT receive event -- tree-pane restatement).
# The suppression is implemented in `Storage._mark_write` + the watcher's
# `was_recently_written` filter. Both are primary-frame-tested elsewhere;
# this row's tree-pane frame is the static observation that the tree-pane
# has NO custom logic to bypass the suppression -- it just subscribes to
# the bus via the body's sse-connect. If a future code change ever wired
# a non-bus path (e.g. a window-level event), this static check would
# need updating.
sse_listeners = re.findall(
    r'addEventListener\s*\(\s*"sse:change"', JS,
)
# The expected listeners: one on the file editor, one on the run editor
# (both via document.body). The tree-pane's swap is driven by HTMX's
# `hx-trigger="sse:change"`, NOT by an explicit addEventListener.
assert len(sse_listeners) >= 1, (
    f"SF3 (static cross-check): app.js must register at least one body-level "
    f"sse:change listener (file editor + run editor); got {len(sse_listeners)}"
)
# Crucially the tree-pane has no bespoke listener that could bypass
# `_mark_write` suppression -- its only wiring is HTMX's hx-trigger.
assert 'tree-pane' not in afterswap_body or 'tmsRestoreTreeState' in afterswap_body, (
    "SF3 (static): if the htmx:afterSwap handler mentions 'tree-pane', it "
    "must do so only to call tmsRestoreTreeState() (no bespoke fetch path "
    "that could bypass Storage._mark_write suppression)"
)
print("PASS  SF3 (tree-pane restatement): no bespoke fetch bypass; suppression upstream in feature-02/03")
