# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / UX4 -- multi-hit list-view variant.

UX4: a query that matches >= 2 hits renders a table; each row is an
     hx-get to /ui/file/<file_path> (target #main-pane) and shows the
     file_path, the first line of the description, and a match badge
     carrying matched_field + match_value (@-prefixed for tag mode).

Driven end-to-end through /ui/search with two matching files.
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
    # Two files match; first description is multi-line to prove first-line trunc.
    s.create_file(["Alpha", "Mod", "one.feature"], "needle first line\nsecond line ignored")
    s.create_file(["Alpha", "Mod", "two.feature"], "needle other file")

    resp = client.get("/ui/search?q=needle&match=text&scope=all")
    assert resp.status_code == 200, f"UX4: must render 200, got {resp.status_code}"
    html = resp.get_data(as_text=True)

    # --- UX4: a results table with the match count heading. ---
    assert "<table" in html, "UX4: >=2 hits must render the results table"
    assert "2 matches for" in html, "UX4: the heading must report the hit count"
    assert "<script>" not in html, "UX4: list view must NOT emit the single-hit auto-nav script"

    # --- UX4: each row is an hx-get to the file editor, target #main-pane. ---
    for fp in ("Alpha/Mod/one.feature", "Alpha/Mod/two.feature"):
        assert re.search(
            rf'<tr[^>]*hx-get="/ui/file/{re.escape(fp)}"[^>]*>',
            html,
            re.DOTALL,
        ), f"UX4: row for {fp} must be an hx-get to its editor route"
    assert re.search(r'hx-target="#main-pane"', html), (
        "UX4: result rows must target #main-pane"
    )

    # --- UX4: first-line-only description in the visible cell text. ---
    # (The full multi-line description still rides along in the cell's
    # title="" attribute; we assert on the rendered cell body only.)
    desc_cells = re.findall(
        r'text-slate-700 truncate"[^>]*>\s*(.*?)\s*</td>', html, re.DOTALL
    )
    assert desc_cells, "UX4: description cells must render"
    joined = "\n".join(desc_cells)
    assert "needle first line" in joined, "UX4: cell must show the first description line"
    assert "second line ignored" not in joined, (
        "UX4: only the first line of the description is shown in the cell body"
    )

    # --- UX4: each row carries a match badge with matched_field. ---
    assert html.count(">description</span>") == 2, (
        "UX4: each text-mode row must show a 'description' matched_field badge"
    )

print("PASS  UX4: >=2 hits render a list-view table; rows hx-get the editor, show first-line description + match badge")
