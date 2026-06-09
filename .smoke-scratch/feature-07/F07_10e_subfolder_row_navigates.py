# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Acceptance criteria -- AC5.

Clicking a sub-folder row navigates the main pane to that folder's view.
Tested as a round-trip: the row's hx-get URL must resolve to a
folder_subfolder.html / folder_module.html partial.
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
    client.post("/api/folders", json={"parent": "Alpha/Mod", "name": "Sub"})

    # AC5 (wiring): sub-folder row in the module view hx-gets to the
    # sub-folder's view.
    mod_html = client.get("/ui/folder/Alpha/Mod").get_data(as_text=True)
    row = re.search(
        r'<tr[^>]*hx-get="/ui/folder/Alpha/Mod/Sub"[^>]*'
        r'hx-target="#main-pane"[^>]*hx-swap="innerHTML"',
        mod_html,
    )
    assert row, (
        "AC5: sub-folder row in folder_module.html must wire "
        "hx-get='/ui/folder/Alpha/Mod/Sub' + hx-target='#main-pane' + "
        "hx-swap='innerHTML'"
    )

    # AC5 (round-trip): the row's hx-get URL resolves to the sub-folder
    # view (folder_subfolder.html at depth 3 -- heading shows 'Sub').
    r = client.get("/ui/folder/Alpha/Mod/Sub")
    assert r.status_code == 200, (
        f"AC5: GET /ui/folder/Alpha/Mod/Sub (simulated row click) must "
        f"return 200, got {r.status_code}"
    )
    sub_html = r.get_data(as_text=True)
    assert ">Sub</h2>" in sub_html, (
        "AC5: simulated sub-folder row click must return the sub-folder "
        "view with the leaf as heading (got page without ><h2>Sub</h2>)"
    )
print("PASS  AC5: sub-folder row hx-get -> /ui/folder/<sub-path> -> folder_subfolder.html (round-trip)")
