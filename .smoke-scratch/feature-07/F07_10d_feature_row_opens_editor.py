# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Acceptance criteria -- AC4.

Clicking a feature row opens that file in the editor. Tested as a
round-trip: the row's `hx-get` URL must succeed and return the file
editor HTML.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "scenario_name": "s", "description": "x"},
    )
    folder_html = client.get("/ui/folder/Alpha/Mod").get_data(as_text=True)

    # AC4 (wiring): the feature row's hx-get points at /ui/file/<path>.
    row = re.search(
        r'<tr[^>]*hx-get="/ui/file/Alpha/Mod/case\.feature"[^>]*'
        r'hx-target="#main-pane"[^>]*hx-swap="innerHTML"',
        folder_html,
    )
    assert row, (
        "AC4: feature row must wire hx-get='/ui/file/Alpha/Mod/case.feature' + "
        "hx-target='#main-pane' + hx-swap='innerHTML'"
    )

    # AC4 (round-trip): simulating the click -- fetch the hx-get URL --
    # must resolve to the file editor HTML.
    r = client.get("/ui/file/Alpha/Mod/case.feature")
    assert r.status_code == 200, (
        f"AC4: GET /ui/file/Alpha/Mod/case.feature (simulated row click) "
        f"must return 200, got {r.status_code}"
    )
    file_html = r.get_data(as_text=True)
    assert 'id="file-editor"' in file_html, (
        "AC4: simulated row click must return the file editor partial "
        "(must contain `id=\"file-editor\"` anchor for the editor controller)"
    )
print("PASS  AC4: feature row hx-get -> /ui/file/<p> -> file editor partial (round-trip)")
