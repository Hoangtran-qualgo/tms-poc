# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / UX3 -- single-hit auto-navigation variant.

UX3: a query that matches exactly one file renders an inline <script>
     that runs htmx.ajax("GET", "/ui/file/<file_path>", { target:
     "#main-pane", swap: "innerHTML" }) — auto-navigating to the editor
     with no intermediate list view (no results table).

Driven end-to-end through /ui/search with a query matching one file.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    s = app.extensions["storage"]
    client = app.test_client()

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    # Exactly one file contains the needle.
    s.create_file(["Alpha", "Mod", "only.feature"], "the unique needle here")
    s.create_file(["Alpha", "Mod", "other.feature"], "nothing relevant")

    resp = client.get("/ui/search?q=needle&match=text&scope=all")
    assert resp.status_code == 200, f"UX3: must render 200, got {resp.status_code}"
    html = resp.get_data(as_text=True)

    # The inline auto-nav script targets the matched file's editor.
    assert "<script>" in html, "UX3: single hit must emit an inline auto-nav <script>"
    assert re.search(
        r'htmx\.ajax\(\s*"GET"\s*,\s*"/ui/file/Alpha/Mod/only\.feature"',
        html,
    ), "UX3: the auto-nav script must htmx.ajax GET the matched file's editor route"
    assert re.search(r'target:\s*"#main-pane"', html), (
        "UX3: the auto-nav swap must target #main-pane"
    )
    assert re.search(r'swap:\s*"innerHTML"', html), (
        "UX3: the auto-nav swap must use swap: 'innerHTML'"
    )

    # No intermediate list view.
    assert "<table" not in html, "UX3: single hit must NOT render the results table"
    assert "No matches" not in html, "UX3: single hit must NOT show the no-matches heading"

print("PASS  UX3: a single-hit query emits the inline htmx.ajax auto-nav to the file editor (no list view)")
