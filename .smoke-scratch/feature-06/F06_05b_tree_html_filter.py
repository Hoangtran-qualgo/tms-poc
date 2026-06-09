# Pattern: see .smoke-scratch/README.md
"""feature-06 / tree-pane / HD1 HTML half.

`GET /ui/tree` HTML must not carry a `data-path="<project>/test-run"`
row for any depth-1 (project) folder. Mirrors HD1's storage-side
assertion in `F06_05a` at the rendered-partial layer.

Moved from `.smoke-scratch/p2_2b_tree_hides_test_run.py` during
feature-06 Step 2 (Restructure); refined with positive-control
assertions per Step 3.
"""
import pathlib
import tempfile

from app import create_app
from app.storage import Storage


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s = Storage(pathlib.Path(td))
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])  # positive-control module
    s.create_run_group("Alpha", "release-1")  # creates Alpha/test-run/

    client = app.test_client()
    r = client.get("/ui/tree")
    assert r.status_code == 200, (
        f"HD1 setup: GET /ui/tree must return 200, got {r.status_code}"
    )
    html = r.get_data(as_text=True)

    # Positive controls: the project name and the sibling module MUST
    # both appear in the rendered partial, proving the tree was actually
    # populated. Without this, a regressed HD1 (the whole tree empty)
    # would silently pass the negative-only assertion below.
    assert "Alpha" in html, (
        "HD1 positive control: project name 'Alpha' must appear in the "
        "/ui/tree HTML (otherwise the negative invariant below is vacuously true)"
    )
    assert 'data-path="Alpha/Checkout"' in html, (
        "HD1 positive control: sibling module 'Alpha/Checkout' must carry a "
        "data-path attribute in the /ui/tree HTML (proves the filter targets "
        "only the 'test-run' child, not all depth-2 children)"
    )

    # Negative invariant (HD1): no folder/file row may carry a
    # data-path pointing into the typed area.
    assert 'data-path="Alpha/test-run' not in html, (
        "HD1: /ui/tree HTML must NOT carry any data-path attribute starting "
        "with 'Alpha/test-run' (the typed area must be filtered out by "
        "Storage.list_tree() before the template renders)"
    )
print("PASS  HD1 (HTML half): /ui/tree hides 'test-run' rows while keeping siblings")
