# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / RT2 + MS3 (UI half).

RT2: `GET /ui/search` renders `search_results.html` with the same query
     args as /api/search.
MS3: the UI layer strips `q` first; empty/whitespace-only `q` short-
     circuits to the empty-state partial (`show_empty_state=True`,
     hits=[]) BEFORE calling Storage.search.

Also covers AC1's server half (empty query renders the "Type a query…"
empty state) — the client-skip half is IF1 in F09_14.
"""
import pathlib
import tempfile

from app import create_app


EMPTY_STATE = "Type a query in the search box above and press Enter."


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    s = app.extensions["storage"]
    client = app.test_client()

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    s.create_file(["Alpha", "Mod", "hit.feature"], "contains needle here")

    # --- RT2: non-empty q renders search_results.html (HTML, 200). ---
    r = client.get("/ui/search?q=needle&match=text")
    assert r.status_code == 200, f"RT2: /ui/search must return 200, got {r.status_code}"
    assert "text/html" in r.headers.get("Content-Type", ""), (
        "RT2: /ui/search must respond with HTML"
    )
    html = r.get_data(as_text=True)
    # The partial roots itself at <div data-folder-path="search">.
    assert 'data-folder-path="search"' in html, (
        "RT2: rendered partial must be search_results.html "
        "(missing data-folder-path=\"search\" root)"
    )
    assert EMPTY_STATE not in html, (
        "RT2: a non-empty q with hits must NOT render the empty-state message"
    )

    # --- MS3 (UI half): empty q → empty-state short-circuit. ---
    blank = client.get("/ui/search?q=").get_data(as_text=True)
    assert EMPTY_STATE in blank, (
        "MS3: empty q at /ui/search must render the 'Type a query…' empty state"
    )

    # --- MS3: whitespace-only q ALSO short-circuits (the UI strips). ---
    # This is the UI-specific divergence: /api/search would delegate to
    # Storage.search (→ []), but /ui/search strips → empty-state branch.
    ws = client.get("/ui/search?q=%20%20%20").get_data(as_text=True)
    assert EMPTY_STATE in ws, (
        "MS3: whitespace-only q at /ui/search must strip → empty-state partial"
    )
    # And it must NOT render the 'No matches' branch (that would mean it
    # called Storage.search with the whitespace query).
    assert "No matches for" not in ws, (
        "MS3: whitespace-only q must short-circuit BEFORE Storage.search "
        "(no 'No matches' branch)"
    )

print("PASS  RT2 + MS3(UI): /ui/search renders search_results.html; empty/whitespace q strips → 'Type a query…' empty-state short-circuit")
