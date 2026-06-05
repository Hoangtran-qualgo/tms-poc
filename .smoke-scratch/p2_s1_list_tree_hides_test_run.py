"""list_tree filter: 'test-run' child of a project must not appear."""
import tempfile, pathlib
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    s = Storage(pathlib.Path(td))
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_run_group("Alpha", "release-1")

    project = s.list_tree()["children"][0]
    child_names = [c["name"] for c in project["children"]]
    assert project["name"] == "Alpha", project
    assert "Checkout" in child_names, child_names
    assert "test-run" not in child_names, child_names
    print("PASS p2-s1 list_tree hides test-run at depth 1")
