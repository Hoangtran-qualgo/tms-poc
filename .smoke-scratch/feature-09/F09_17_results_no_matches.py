# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / UX2 -- zero-matches variant.

UX2: a non-empty query that matches no file renders the heading
     "No matches for <q>" plus a hint line, and NONE of the other
     variants (no empty-state prompt, no auto-nav <script>, no table).

Driven end-to-end through /ui/search with a query that no fixture
contains.
"""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    s = app.extensions["storage"]
    client = app.test_client()

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    s.create_file(["Alpha", "Mod", "a.feature"], "something unrelated")

    resp = client.get("/ui/search?q=zzz-nomatch&match=text&scope=all")
    assert resp.status_code == 200, f"UX2: must render 200, got {resp.status_code}"
    html = resp.get_data(as_text=True)

    # The query is echoed into the heading.
    assert "No matches for" in html and "zzz-nomatch" in html, (
        "UX2: a zero-hit query must render 'No matches for <q>' echoing the query"
    )
    assert "Try a different query" in html, "UX2: the no-matches hint line must render"

    # None of the other variants leak in.
    assert "Type a query in the search box above" not in html, (
        "UX2: zero-hit (non-empty query) must NOT show the empty-state prompt"
    )
    assert "<script>" not in html, "UX2: zero-hit must NOT emit an auto-nav script"
    assert "<table" not in html, "UX2: zero-hit must NOT render the results table"

print("PASS  UX2: a non-empty query with zero hits renders 'No matches for <q>' + hint (no empty-state / auto-nav / table)")
