# Pattern: see .smoke-scratch/README.md
"""feature-06 / tree-pane / Server-side initial render (SR1).

`base.html` does `{% include "tree.html" %}` so the first paint is
fully populated server-side; HTMX is NOT on the critical path for
first render. `#tree-pane`'s `hx-get` fires only on subsequent
`sse:change` events. Verifiable from the `GET /` response body
already containing the tree contents.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "ModA"})
    client.post("/api/folders", json={"name": "Beta"})

    # The very first request: GET /. No prior /ui/tree fetch.
    r = client.get("/")
    assert r.status_code == 200, (
        f"SR1 setup: GET / must return 200, got {r.status_code}"
    )
    html = r.get_data(as_text=True)

# --- SR1 (a): tree contents are inside #tree-pane on first paint. -------
tree_pane = re.search(
    r'<aside\s+id="tree-pane"[^>]*>(.*?)</aside>',
    html,
    re.DOTALL,
)
assert tree_pane, "SR1: <aside id=\"tree-pane\"> must exist on first paint"
inner = tree_pane.group(1)
# Tree contents from tree.html must be inlined directly (via Jinja include),
# not stubbed out with a loading placeholder waiting for HTMX.
for needle in ("Alpha", "ModA", "Beta"):
    assert needle in inner, (
        f"SR1: #tree-pane's innerHTML on first paint must include "
        f"{needle!r} (tree.html included server-side, not deferred to HTMX). "
        f"Inner: {inner[:200]!r}..."
    )
# Must NOT carry the empty-state placeholder when data exists.
assert "No projects yet" not in inner, (
    "SR1 cross-check: with seeded data, #tree-pane must NOT show the "
    "'No projects yet.' empty-state placeholder on first paint"
)

# --- SR1 (b): #tree-pane still wires hx-get for SUBSEQUENT sse:change. --
tag = re.search(r'<aside\s+id="tree-pane"[^>]*>', html).group(0)
assert 'hx-get="/ui/tree"' in tag, (
    "SR1: #tree-pane must still declare hx-get=\"/ui/tree\" for subsequent "
    "SSE-driven refreshes (only the FIRST paint comes from the include)"
)
assert 'hx-trigger="sse:change"' in tag, (
    "SR1: #tree-pane must still declare hx-trigger=\"sse:change\" so the "
    "second-and-later refreshes go through HTMX"
)

# --- SR1 (c): empty-FS variant -- placeholder is part of the include. ---
with tempfile.TemporaryDirectory() as td:
    app2 = create_app(data_root=pathlib.Path(td).resolve())
    html2 = app2.test_client().get("/").get_data(as_text=True)
empty_pane = re.search(
    r'<aside\s+id="tree-pane"[^>]*>(.*?)</aside>',
    html2,
    re.DOTALL,
).group(1)
assert "No projects yet" in empty_pane, (
    "SR1 empty-FS: on empty data root, #tree-pane's innerHTML on first paint "
    "must already contain the 'No projects yet.' placeholder (server-side "
    "include of tree.html); current inner: " + repr(empty_pane[:200])
)
print("PASS  SR1: base.html includes tree.html so first paint is fully populated; SSE hx-get still wired")
