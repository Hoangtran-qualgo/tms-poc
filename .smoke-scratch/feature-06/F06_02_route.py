# Pattern: see .smoke-scratch/README.md
"""feature-06 / tree-pane / Route (RT1).

`GET /ui/tree` renders `tree.html` with `tree = storage.list_tree()`.
Used by both the manual refresh button and the SSE auto-refresh.
"""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()

    # --- Empty-state branch: list_tree returns an empty children list. ---
    r = client.get("/ui/tree")
    assert r.status_code == 200, (
        f"RT1: GET /ui/tree on empty FS must return 200, got {r.status_code}"
    )
    assert r.mimetype == "text/html", (
        f"RT1: GET /ui/tree must render HTML, got mimetype {r.mimetype!r}"
    )
    body = r.get_data(as_text=True)
    # Empty-state placeholder per spec section
    # *Scope -> Empty-state placeholder when the data root has no projects*.
    assert "No projects yet" in body, (
        "RT1 empty-state: GET /ui/tree on empty FS must render the "
        "'No projects yet.' placeholder; missing in response"
    )

    # --- Populated branch: list_tree() output drives the rendered HTML. --
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "ModA"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "ModB"})
    client.post("/api/folders", json={"name": "Beta"})

    r = client.get("/ui/tree")
    assert r.status_code == 200, (
        f"RT1: GET /ui/tree populated must return 200, got {r.status_code}"
    )
    html = r.get_data(as_text=True)

    # Every project + every module produced by list_tree() must show up.
    for needle in ("Alpha", "Beta", "ModA", "ModB"):
        assert needle in html, (
            f"RT1: GET /ui/tree HTML must contain {needle!r} "
            f"(present in list_tree() output but missing from response)"
        )

    # data-path attributes prove the tree.html macro walked the
    # list_tree() output (rather than rendering a stale cached payload).
    assert 'data-path="Alpha/ModA"' in html, (
        "RT1: GET /ui/tree HTML must carry data-path='Alpha/ModA' "
        "(proves list_tree() output drove the render)"
    )
    assert 'data-path="Alpha/ModB"' in html, (
        "RT1: GET /ui/tree HTML must carry data-path='Alpha/ModB'"
    )
    assert 'data-path="Beta"' in html, (
        "RT1: GET /ui/tree HTML must carry data-path='Beta'"
    )
print("PASS  RT1: GET /ui/tree -> 200 text/html; empty-state placeholder; list_tree() output drives the render")
