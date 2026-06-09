"""list_test_run_tree omits projects that have no test-run/ folder."""
import tempfile, pathlib
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    s = Storage(pathlib.Path(td))
    s.create_folder(["Alpha"])
    s.create_run_group("Alpha", "release-1")
    s.create_folder(["Beta"])  # no runs in Beta

    tree = s.list_test_run_tree()
    project_names = [c["name"] for c in tree["children"]]
    assert tree["name"] == "", tree
    assert project_names == ["Alpha"], project_names
    print("PASS p2-s3 list_test_run_tree skips projects without test-run/")
