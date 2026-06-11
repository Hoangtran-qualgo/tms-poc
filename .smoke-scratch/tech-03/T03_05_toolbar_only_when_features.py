# Pattern: see .smoke-scratch/README.md
"""tech-03 / folder bulk-actions / toolbar renders only when features exist.

The bulk toolbar lives inside the `{% if features %}` branch (via the
shared partial), so an empty module / sub-folder shows its create-CTA
empty state with NO toolbar or selection chrome.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Empty"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Full"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Full", "file_name": "case", "description": "x"},
    )
    empty_html = client.get("/ui/folder/Alpha/Empty").get_data(as_text=True)
    full_html = client.get("/ui/folder/Alpha/Full").get_data(as_text=True)

assert "data-bulk-root" not in empty_html, (
    "an empty folder must NOT render the bulk toolbar/selection chrome"
)
assert "data-bulk-action" not in empty_html, (
    "an empty folder must NOT render bulk-action buttons"
)
assert "data-bulk-root" in full_html, (
    "a non-empty folder must render the bulk toolbar"
)
print("PASS  T03_05: bulk toolbar renders only when the folder has direct features")
