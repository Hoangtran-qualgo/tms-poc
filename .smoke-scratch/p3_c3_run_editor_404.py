"""3.C — Missing run produces a 404; the blueprint's error handler
returns a JSON envelope (or a 404 HTTP status; either way it must not
be a 500)."""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_run_group("Alpha", "release-1")

    client = app.test_client()
    r = client.get("/ui/run/Alpha/release-1/never.yaml")
    assert r.status_code == 404, r.status_code
    print("PASS 3.C missing run yields 404")
