# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / RT1 -- GET /ui/file/<path:p>.

End-to-end with the Flask test client:
 1. `.feature` path -> renders file_editor.html (editor scaffold present).
 2. Non-`.feature` path -> renders unsupported.html (no editor scaffold).
 3. Malformed `.feature` on disk -> error envelope (status >= 400).

Note on (3): a malformed on-disk `.feature` makes `read_feature` raise
`GherkinParseError`, which has NO dedicated UI handler (only ValueError
-> 400 and FileNotFoundError -> 404 do), so it falls through to the
catch-all `@ui.errorhandler(Exception)` and returns a generic 500. The
spec's Route § documents this 500 fallback as the intended HTML-route
contract (the 422 `parse_error` envelope is the JSON API surface). The
smoke asserts the observed behaviour (HTTP >= 400 + no editor scaffold).
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()

    # --- (1) .feature happy path -------------------------------------------
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "description": "x"},
    )
    assert r.status_code == 201, "RT1 setup: file POST must succeed"

    r = client.get("/ui/file/Alpha/Mod/case.feature")
    assert r.status_code == 200, (
        f"RT1 (.feature): GET /ui/file/Alpha/Mod/case.feature must return 200, "
        f"got {r.status_code}"
    )
    html = r.get_data(as_text=True)
    for marker, desc in (
        ('id="file-editor"', "file-editor root div"),
        ('id="editor-data"', "JSON payload script tag"),
        ('id="tab-btn-structured"', "structured tab button"),
        ('id="tab-btn-raw"', "raw tab button"),
        ('id="btn-save"', "Save button"),
        ('tmsBootEditor()', "tail-end bootstrap call"),
    ):
        assert marker in html, (
            f"RT1 (.feature): rendered file_editor.html must contain {desc} "
            f"({marker!r})"
        )
    # crumbs + file_name template variables surface.
    assert "Alpha" in html and "Mod" in html and "case.feature" in html, (
        "RT1 (.feature): rendered template must surface crumbs (Alpha/Mod) + "
        "file_name (case.feature) from the route's render_template call"
    )

    # --- (2) non-.feature -> unsupported.html ------------------------------
    r = client.get("/ui/file/notes.txt")
    assert r.status_code == 200, (
        f"RT1 (unsupported): GET /ui/file/<non-feature> must return 200, "
        f"got {r.status_code}"
    )
    html2 = r.get_data(as_text=True)
    assert "File type not supported" in html2, (
        "RT1 (unsupported): non-.feature path must render unsupported.html "
        "(contains 'File type not supported' heading)"
    )
    assert 'id="file-editor"' not in html2, (
        "RT1 (unsupported): unsupported.html must NOT include the file-editor "
        "scaffold"
    )

    # --- (3) parse error on disk -------------------------------------------
    # Write malformed Gherkin directly to disk to bypass server-side
    # validation, then GET the ui_file route. `read_feature` raises
    # GherkinParseError; the UI blueprint's catch-all returns 500 (drift
    # flagged in this file's docstring).
    bad_path = root / "Alpha" / "Mod" / "broken.feature"
    bad_path.write_text("not a valid gherkin file at all\n", encoding="utf-8")
    r = client.get("/ui/file/Alpha/Mod/broken.feature")
    assert r.status_code >= 400, (
        f"RT1 (parse error): malformed .feature must surface an error "
        f"response (status >= 400), got {r.status_code}"
    )
    assert 'id="file-editor"' not in r.get_data(as_text=True), (
        "RT1 (parse error): error response must NOT render the editor scaffold"
    )

print(
    "PASS  RT1: GET /ui/file/<p> -- .feature -> file_editor.html, "
    "non-.feature -> unsupported.html, parse error -> error response"
)
