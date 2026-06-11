"""S4 smoke — GET /ui/enums-tree lists projects with a legacy badge.

Asserts:
1. Every project (list_root) is listed with an hx-get to its manager.
2. A project whose enums.yaml is missing carries the "no file" legacy badge;
   an initialised one does not.
"""
import pathlib
import tempfile

from app import create_app
from app.storage import Storage


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["Alpha"])      # auto-init → has enums.yaml
    (root / "Legacy").mkdir()        # manual → no enums.yaml
    c = create_app(data_root=root).test_client()

    r = c.get("/ui/enums-tree")
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)
    assert "Alpha" in html and "Legacy" in html, html
    assert 'hx-get="/ui/enums/Alpha"' in html, html
    assert 'hx-get="/ui/enums/Legacy"' in html, html
    print("PASS  /ui/enums-tree lists every project linking to its manager")

    # The legacy badge appears once and belongs to the Legacy row (project
    # order is OS listing order, so don't assume Alpha precedes Legacy).
    assert html.count("no file") == 1, html

    def _row(project: str) -> str:
        seg = html.split(f'data-project="{project}"', 1)[1]
        nxt = seg.find('data-project="')
        return seg if nxt == -1 else seg[:nxt]

    assert "no file" in _row("Legacy"), "Legacy row missing the badge"
    assert "no file" not in _row("Alpha"), "Alpha row should not carry the badge"
    print("PASS  legacy project carries the 'no file' badge; initialised one does not")
