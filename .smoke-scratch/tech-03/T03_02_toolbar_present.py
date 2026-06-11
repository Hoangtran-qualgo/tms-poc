# Pattern: see .smoke-scratch/README.md
"""tech-03 / folder bulk-actions / toolbar renders in module + sub-folder views.

The shared `_folder_feature_table.html` partial must render, above the
features table, a bulk-action toolbar with a live count and four buttons
(Move / Re-tag / Run / Delete) that start DISABLED, plus a select-all
checkbox in the table header. Verified at depth 2 (module) and depth 3
(sub-folder) since both views include the same partial.
"""
import pathlib
import re
import tempfile

from app import create_app


def _assert_toolbar(html, where):
    assert re.search(r"data-bulk-root", html), (
        f"{where}: must render the [data-bulk-root] bulk-actions container"
    )
    assert re.search(r'data-role="count"[^>]*>\s*0 selected', html), (
        f"{where}: toolbar must show a '0 selected' count initially"
    )
    assert re.search(
        r'<input[^>]*type="checkbox"[^>]*data-role="select-all"', html
    ), f"{where}: header must carry a select-all checkbox"
    for action in ("move", "retag", "run", "delete"):
        btn = re.search(
            r'<button[^>]*data-bulk-action="' + action + r'"[^>]*>',
            html,
        )
        assert btn, f"{where}: toolbar must have a '{action}' button"
        assert "disabled" in btn.group(0), (
            f"{where}: '{action}' button must start disabled (empty selection)"
        )


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post("/api/folders", json={"parent": "Alpha/Mod", "name": "Sub"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "description": "x"},
    )
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod/Sub", "file_name": "deep", "description": "y"},
    )
    module_html = client.get("/ui/folder/Alpha/Mod").get_data(as_text=True)
    sub_html = client.get("/ui/folder/Alpha/Mod/Sub").get_data(as_text=True)

_assert_toolbar(module_html, "module view (depth 2)")
_assert_toolbar(sub_html, "sub-folder view (depth 3)")
print("PASS  T03_02: bulk toolbar (count + select-all + 4 disabled buttons) renders at depth 2 and 3")
