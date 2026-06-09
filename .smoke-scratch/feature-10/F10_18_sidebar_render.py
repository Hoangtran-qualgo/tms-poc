"""GET /ui/test-run-tree renders 200 with leaf URLs + empty state."""
import tempfile, pathlib
from app import create_app

# Empty data root -> empty state
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    client = app.test_client()
    r = client.get("/ui/test-run-tree")
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)
    assert "No test runs yet" in html, html
    print("PASS p2-s6a empty state renders")

# Seeded data root -> project node + run leaf with /ui/run/... link
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    from app.storage import Storage
    s = Storage(pathlib.Path(td))
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_run_group("Alpha", "release-1")
    s.create_run(project="Alpha", group="release-1", name="Sprint A",
                 file_name="sprint-a", case_paths=["Alpha/Checkout/pay.feature"])
    client = app.test_client()
    r = client.get("/ui/test-run-tree")
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)
    assert "Alpha" in html, html
    assert "release-1" in html, html
    assert "sprint-a.yaml" in html, html
    assert 'hx-get="/ui/run/Alpha/release-1/sprint-a.yaml"' in html, html
    assert "No test runs yet" not in html, html
    print("PASS p2-s6b seeded tree renders with /ui/run link")
