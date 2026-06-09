# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / UX1 -- empty-state variant.

UX1: when show_empty_state is True (blank query), search_results.html
     renders the prompt "Type a query in the search box above and press
     Enter." and NONE of the other variants (no "No matches" heading,
     no auto-nav <script>, no results table).

Driven end-to-end through /ui/search with a blank query, which the
route short-circuits to show_empty_state=True regardless of fixtures.
"""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    s = app.extensions["storage"]
    client = app.test_client()

    # A matching file exists, proving the empty-state path ignores data.
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    s.create_file(["Alpha", "Mod", "a.feature"], "needle here")

    for url in ("/ui/search?q=", "/ui/search?q=%20%20"):  # blank + whitespace-only
        resp = client.get(url)
        assert resp.status_code == 200, f"UX1: {url} must render 200, got {resp.status_code}"
        html = resp.get_data(as_text=True)

        assert "Type a query in the search box above and press Enter." in html, (
            f"UX1: {url} must render the empty-state prompt"
        )
        # None of the other variants leak in.
        assert "No matches" not in html, "UX1: empty state must NOT show the no-matches heading"
        assert "<script>" not in html, "UX1: empty state must NOT emit an auto-nav script"
        assert "<table" not in html, "UX1: empty state must NOT render the results table"

print("PASS  UX1: blank/whitespace query renders the empty-state prompt only (no no-matches / auto-nav / table)")
