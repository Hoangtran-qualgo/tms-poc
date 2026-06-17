"""T10-04 — hx-push-url wiring.

Every main-pane nav element carries hx-push-url; the #main-pane load-trigger
and the #tree-pane SSE element must NOT (they would wrongly push /ui/folder/ on
boot and /ui/tree on every SSE refresh).
"""
import tempfile, pathlib, re
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s = Storage(root)
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    c = app.test_client()

    shell = c.get("/").get_data(as_text=True)
    main = re.search(r'id="main-pane"[^>]*>', shell).group(0)
    assert "hx-push-url" not in main, f"#main-pane load-trigger must not push: {main}"
    tree_pane = re.search(r'id="tree-pane"[^>]*>', shell).group(0)
    assert "hx-push-url" not in tree_pane, f"#tree-pane SSE must not push: {tree_pane}"

    # Directory-tree rows (server-included in the shell) push.
    assert 'hx-push-url="true"' in shell and 'hx-target="#main-pane"' in shell

    # A swapped-in fragment's nav rows push too.
    frag = c.get("/ui/folder/Alpha", headers={"HX-Request": "true"}).get_data(as_text=True)
    assert 'hx-push-url="true"' in frag, "folder-view rows must push"
    print("PASS T10-04 nav pushes; #main-pane load + #tree-pane SSE do not")
