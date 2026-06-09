# Pattern: see .smoke-scratch/README.md
"""feature-06 / tree-pane / Manual refresh button (MR1-MR3)."""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    html = client.get("/ui/tree").get_data(as_text=True)

# Locate the refresh button. Anchor on `title="Refresh tree"` to grab
# the one button this rule names; tree.html has only this one.
m = re.search(r'<button[^>]*title="Refresh tree"[^>]*>[^<]*</button>', html)
assert m, (
    "MR1: tree.html must render the refresh `<button title=\"Refresh tree\">` "
    "as part of the partial (so every swap re-renders it). Button not found "
    "in /ui/tree HTML."
)
button = m.group(0)

# --- MR1: the button is rendered INSIDE the partial. -------------------
# Confirmed by the fact that GET /ui/tree (which returns only the
# tree.html partial, not the full base.html) contains the button.
# Stateless re-render: re-fetching /ui/tree yields the same button
# bytes (no client-side state is carried).
html2 = client.get("/ui/tree").get_data(as_text=True)
m2 = re.search(r'<button[^>]*title="Refresh tree"[^>]*>[^<]*</button>', html2)
assert m2 and m2.group(0) == button, (
    "MR1: the refresh button must be stateless -- two consecutive /ui/tree "
    "fetches must return byte-identical button markup. (Re-rendered with "
    "every swap; no client-side state retained.)"
)

# --- MR2: pure HTMX -- correct hx-* triple AND no JS. ------------------
for attr in (
    'hx-get="/ui/tree"',
    'hx-target="#tree-pane"',
    'hx-swap="innerHTML"',
):
    assert attr in button, (
        f"MR2: refresh button must carry {attr}; got {button!r}"
    )
assert "onclick=" not in button, (
    f"MR2: refresh button must be pure HTMX -- NO onclick attribute. "
    f"Got: {button!r}"
)
assert "javascript:" not in button.lower(), (
    f"MR2: refresh button must be pure HTMX -- no `javascript:` href; "
    f"got {button!r}"
)

# --- MR3: aria-label="Refresh tree" AND title="Refresh tree". ----------
# Two separate attribute checks so a missing one names its own failure.
assert 'aria-label="Refresh tree"' in button, (
    f"MR3: refresh button must carry aria-label=\"Refresh tree\" for "
    f"accessibility; got {button!r}"
)
assert 'title="Refresh tree"' in button, (
    f"MR3: refresh button must carry title=\"Refresh tree\" for the "
    f"native tooltip; got {button!r}"
)
print("PASS  MR1-MR3: refresh button rendered in tree.html, pure-HTMX wiring, aria-label + title present")
