# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / TP2 cross-pane HD3 HTML half.

`folder_project.html` (depth-1 module table) must not surface the
typed `test-run/` area. The underlying filter rule lives in
feature-06 HD3 (storage-half: `F06_05c_list_folder_filter.py`); this
smoke is the rendering-layer counterpart that asserts the filter
actually reaches the rendered project view.

Moved from `.smoke-scratch/p2_2c_project_view_hides_test_run.py`
during feature-07 Step 2 (Restructure); refined with positive controls
per Step 3.
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
    r = client.get("/ui/folder/Alpha")
    assert r.status_code == 200, (
        f"TP2 setup: GET /ui/folder/Alpha must return 200, got {r.status_code}"
    )
    html = r.get_data(as_text=True)

    # Positive controls: project name + sibling module row MUST appear,
    # proving the page actually rendered (otherwise the negative
    # invariant below would be vacuously true).
    assert "Alpha" in html, (
        "TP2 positive control: project name 'Alpha' must appear in the "
        "folder_project.html output (otherwise the negative invariant below "
        "is vacuously true)"
    )
    assert 'hx-get="/ui/folder/Alpha/Checkout"' in html, (
        "TP2 positive control: sibling module 'Checkout' must render a row "
        "with hx-get=\"/ui/folder/Alpha/Checkout\" (proves the module table "
        "was actually populated, not just empty-state)"
    )

    # Negative invariant (TP2 + feature-06 HD3 HTML half): no module row
    # may point into the typed area.
    assert "/ui/folder/Alpha/test-run" not in html, (
        "TP2 / feature-06 HD3 HTML half: folder_project.html's module table "
        "must NOT contain any hx-get into 'Alpha/test-run' (the typed area "
        "must be filtered out by Storage.list_folder before the template "
        "renders)"
    )
print("PASS  TP2 / HD3 HTML half: folder_project.html filters 'test-run' from module table while keeping siblings")
