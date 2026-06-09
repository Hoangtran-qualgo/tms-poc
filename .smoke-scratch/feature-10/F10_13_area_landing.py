"""3.A.i — GET /ui/folder/<project>/test-run renders folder_test_run_area.html
with the project's groups listed."""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_run_group("Alpha", "release-1")
    s.create_run_group("Alpha", "qa-cycle")

    client = app.test_client()
    r = client.get("/ui/folder/Alpha/test-run")
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)

    # Breadcrumb shows Projects / Alpha / test-run (leaf is heading).
    assert ">Projects<" in html
    assert ">Alpha<" in html
    assert ">test-run<" in html

    # Both groups listed.
    assert ">release-1<" in html or "release-1" in html
    assert "qa-cycle" in html

    # New-run / + Sub-folder buttons NOT on this page (groups are
    # auto-created by the first run; the landing is navigation only).
    assert "+ New run" not in html
    print("PASS 3.A.i area landing renders project's groups")

# Empty-state: no groups at all.
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s = app.extensions["storage"]
    s.create_folder(["Alpha"])
    client = app.test_client()
    r = client.get("/ui/folder/Alpha/test-run")
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)
    assert "No run groups yet" in html
    print("PASS 3.A.i empty-state landing")
