# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Route (RT1).

`GET /ui/folder/` and `GET /ui/folder/<path:p>` are both handled by
`ui_folder`; each reads `storage.list_folder(segments)` and renders
the depth-appropriate template.
"""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})

    # Both URL variants must be handled by the same view function.
    # The empty-path variant uses Flask's default arg (p="").
    r_empty = client.get("/ui/folder/")
    assert r_empty.status_code == 200, (
        f"RT1: GET /ui/folder/ must return 200, got {r_empty.status_code}"
    )
    assert r_empty.mimetype == "text/html", (
        f"RT1: GET /ui/folder/ must return HTML, got mimetype {r_empty.mimetype!r}"
    )

    # The <path:p> variant accepts arbitrary segments.
    r_proj = client.get("/ui/folder/Alpha")
    assert r_proj.status_code == 200, (
        f"RT1: GET /ui/folder/Alpha must return 200, got {r_proj.status_code}"
    )
    r_mod = client.get("/ui/folder/Alpha/Mod")
    assert r_mod.status_code == 200, (
        f"RT1: GET /ui/folder/Alpha/Mod must return 200, got {r_mod.status_code}"
    )

    # Each response must be driven by storage.list_folder() output --
    # the project / module names must appear in the rendered HTML.
    assert "Alpha" in r_empty.get_data(as_text=True), (
        "RT1: GET /ui/folder/ HTML must contain 'Alpha' "
        "(proves list_folder('') output drove the render)"
    )
    assert "Mod" in r_proj.get_data(as_text=True), (
        "RT1: GET /ui/folder/Alpha HTML must contain 'Mod' "
        "(proves list_folder(['Alpha']) output drove the render)"
    )
print("PASS  RT1: /ui/folder/ + /ui/folder/<path:p> -> 200 text/html; list_folder() output drives the render")
