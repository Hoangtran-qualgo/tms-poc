# Pattern: see .smoke-scratch/README.md
"""feature-06 / tree-pane / HD2 storage + HTML halves.

Depths other than 2 are untouched — a folder named ``test-run`` at
depth 3 (e.g. `Alpha/Checkout/test-run/`) IS still listed in
`Storage.list_tree()` AND in the `/ui/tree` HTML, because the HD1
filter is depth-1-only. See
`specs/features/06-feature-tree-pane-NEW.md` § *Invariants & rules →
test-run/ is hidden from the directory tree* ("Other depths are
untouched").

Moved from
`.smoke-scratch/p2_s5_deep_test_run_not_treated_as_typed_area.py`
during feature-06 Step 2 (Restructure); extended with the HTML half
per Step 3.
"""
import pathlib
import tempfile

from app import create_app
from app.storage import Storage


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s = Storage(root)
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_folder(["Alpha", "Checkout", "test-run"])  # depth-3, NOT a typed area

    # --- HD2 storage half: list_tree() shows the depth-3 'test-run'. -------
    alpha = s.list_tree()["children"][0]
    checkout = next(c for c in alpha["children"] if c["name"] == "Checkout")
    deep_names = [c["name"] for c in checkout["children"]]
    assert "test-run" in deep_names, (
        f"HD2: Storage.list_tree() must NOT filter 'test-run' at depth 3 "
        f"(the HD1 filter is depth-1-only); got Checkout's children {deep_names!r}"
    )

    # --- HD2 storage cross-check: list_test_run_tree() skips Alpha entirely.
    # The typed area is depth-2-only; a depth-3 'test-run/' must NOT be
    # treated as one.
    tree = s.list_test_run_tree()
    assert tree["children"] == [], (
        f"HD2 cross-check: list_test_run_tree() must skip projects that have "
        f"NO depth-2 'test-run/' folder, even when a depth-3 one exists; "
        f"got tree['children']={tree['children']!r}"
    )

    # --- HD2 HTML half: /ui/tree carries the depth-3 'test-run' row. -------
    client = app.test_client()
    r = client.get("/ui/tree")
    assert r.status_code == 200, (
        f"HD2 setup: GET /ui/tree must return 200, got {r.status_code}"
    )
    html = r.get_data(as_text=True)
    assert 'data-path="Alpha/Checkout/test-run"' in html, (
        "HD2 (HTML half): /ui/tree must render the depth-3 'test-run' row "
        "with data-path='Alpha/Checkout/test-run' (depth-3 is NOT filtered)"
    )
print("PASS  HD2 (storage + HTML): depth-3 'test-run/' is rendered in list_tree() AND /ui/tree")
