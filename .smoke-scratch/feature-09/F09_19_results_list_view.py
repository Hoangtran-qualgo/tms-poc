# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / UX4 -- multi-hit list-view variant.

UX4: a query that matches >= 2 hits renders a table; each row is an
     hx-get to /ui/file/<file_path> (target #main-pane) and shows the
     file_path, the scenario name (tech-04 OQ8 — was the description),
     and a match badge carrying matched_field + match_value
     (@-prefixed for tag mode).

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
    # Two files match on description text; each carries a scenario name,
    # which is what the results list now displays (OQ8).
    s.create_file(["Alpha", "Mod", "one.feature"], "needle first line",
                  scenario_name="Checkout with card")
    s.create_file(["Alpha", "Mod", "two.feature"], "needle other file",
                  scenario_name="Refund flow")

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

    # --- UX4: the scenario name is the visible cell text (OQ8 swap). ---
    name_cells = re.findall(
        r'text-slate-700 truncate"[^>]*>\s*(.*?)\s*</td>', html, re.DOTALL
    )
    assert name_cells, "UX4: scenario-name cells must render"
    joined = "\n".join(name_cells)
    assert "Checkout with card" in joined and "Refund flow" in joined, (
        "UX4: each row's cell must show the scenario name"
    )
    # The description text is no longer the displayed column (OQ8).
    assert "needle first line" not in joined, (
        "UX4: the description is no longer shown in the results cell"
    )

    # --- UX4: each row carries a match badge with matched_field. ---
    assert html.count(">description</span>") == 2, (
        "UX4: each text-mode row must show a 'description' matched_field badge"
    )

print("PASS  UX4: >=2 hits render a list-view table; rows hx-get the editor, show the scenario name (OQ8) + match badge")
