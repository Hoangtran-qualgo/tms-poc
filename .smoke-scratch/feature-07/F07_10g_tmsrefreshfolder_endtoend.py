# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Acceptance criteria -- AC7 (end-to-end).

After a CRUD mutation, the main pane reflects the new state on the
writing tab once `tmsRefreshFolder` runs.

End-to-end (per Step-1 sign-off Q3): the smoke executes the full
chain that the JS path takes after a CRUD mutation:
  1. CRUD POST to /api/folders or /api/files.
  2. `tmsRefreshFolder(parent)` issues GET /ui/folder/<parent>
     (simulated here as a direct client.get of the same URL).
  3. The response must reflect the new FS state.

The "tmsRefreshFolder actually fires" link is delegated to JS
runtime behaviour; the static half is covered by F07_09.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()

    # --- AC7 (a): root level -- create a project, refresh root view. ----
    pre_root = client.get("/ui/folder/").get_data(as_text=True)
    assert "Beta" not in pre_root, (
        "AC7 setup (a): root view must NOT yet contain 'Beta' before the "
        "mutation"
    )
    r = client.post("/api/folders", json={"name": "Beta"})
    assert r.status_code == 201, (
        f"AC7 setup (a): POST /api/folders must succeed, got {r.status_code}"
    )
    # Simulate tmsRefreshFolder("") -> GET /ui/folder/
    post_root = client.get("/ui/folder/").get_data(as_text=True)
    assert re.search(
        r'<tr[^>]*hx-get="/ui/folder/Beta"', post_root
    ), (
        "AC7 (a): after POST /api/folders + tmsRefreshFolder(''), GET "
        "/ui/folder/ must surface the new 'Beta' project row"
    )

    # --- AC7 (b): project level -- create a module, refresh project view. -
    pre_proj = client.get("/ui/folder/Beta").get_data(as_text=True)
    assert "Cart" not in pre_proj, (
        "AC7 setup (b): project view must NOT yet contain 'Cart' before "
        "the mutation"
    )
    r = client.post("/api/folders", json={"parent": "Beta", "name": "Cart"})
    assert r.status_code == 201, (
        f"AC7 setup (b): POST /api/folders must succeed, got {r.status_code}"
    )
    # Simulate tmsRefreshFolder("Beta") -> GET /ui/folder/Beta
    post_proj = client.get("/ui/folder/Beta").get_data(as_text=True)
    assert 'hx-get="/ui/folder/Beta/Cart"' in post_proj, (
        "AC7 (b): after POST /api/folders + tmsRefreshFolder('Beta'), GET "
        "/ui/folder/Beta must surface the new 'Cart' module row"
    )

    # --- AC7 (c): module level -- create a test case file, refresh module view.
    pre_mod = client.get("/ui/folder/Beta/Cart").get_data(as_text=True)
    assert "newcase.feature" not in pre_mod, (
        "AC7 setup (c): module view must NOT yet contain 'newcase.feature' "
        "before the mutation"
    )
    r = client.post(
        "/api/files",
        json={"parent": "Beta/Cart", "file_name": "newcase", "description": "x"},
    )
    assert r.status_code == 201, (
        f"AC7 setup (c): POST /api/files must succeed, got {r.status_code}"
    )
    # Simulate tmsRefreshFolder("Beta/Cart") -> GET /ui/folder/Beta/Cart
    post_mod = client.get("/ui/folder/Beta/Cart").get_data(as_text=True)
    assert 'hx-get="/ui/file/Beta/Cart/newcase.feature"' in post_mod, (
        "AC7 (c): after POST /api/files + tmsRefreshFolder('Beta/Cart'), "
        "GET /ui/folder/Beta/Cart must surface the new 'newcase.feature' "
        "file row"
    )
print("PASS  AC7 (end-to-end): CRUD POST + tmsRefreshFolder(parent) GET reflects the new FS state at depths 0, 1, 2")
