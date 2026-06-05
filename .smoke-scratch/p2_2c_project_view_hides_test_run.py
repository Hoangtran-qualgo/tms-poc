"""2.c — folder_project.html (module table) hides test-run/."""
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
    r = client.get("/ui/folder/Alpha")
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)

    assert "Checkout" in html, "module row missing"
    # The module row hx-get is built as /ui/folder/<project>/<module>;
    # if test-run had leaked, we'd see that URL.
    assert "/ui/folder/Alpha/test-run" not in html, "test-run row appeared in module table"
    print("PASS 2.c project module table hides test-run/")
