"""3.A.iii — Paths deeper than <project>/test-run/<group> are rejected
with 404; the typed area is exactly two levels (group + run file, and
the run file is reached via /ui/run/..., not /ui/folder/...)."""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_run_group("Alpha", "release-1")
    s.create_folder(["Alpha", "Checkout"])
    s.create_run(project="Alpha", group="release-1", name="S1",
                 file_name="s1", case_paths=["Alpha/Checkout/a.feature"])

    client = app.test_client()
    r = client.get("/ui/folder/Alpha/test-run/release-1/s1.yaml")
    assert r.status_code == 404, r.status_code
    print("PASS 3.A.iii deeper paths under test-run/ return 404")
