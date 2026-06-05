"""2.b — Directory tree hides 'test-run/' under a project."""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s = Storage(pathlib.Path(td))
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_run_group("Alpha", "release-1")

    client = app.test_client()
    r = client.get("/ui/tree")
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)

    assert "Alpha" in html, "project missing"
    assert "Checkout" in html, "module missing"
    # The string 'test-run' must NOT appear as a tree row. We allow the
    # comment/docs in tree.html to mention it (none does), but a defensive
    # check: ensure no folder/file row has data-path containing test-run.
    assert 'data-path="Alpha/test-run' not in html, "test-run leaked into tree HTML"
    print("PASS 2.b directory tree hides test-run/")
