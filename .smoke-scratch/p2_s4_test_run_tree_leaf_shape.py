"""list_test_run_tree leaves carry type='run' + project/group/file_name."""
import tempfile, pathlib
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    s = Storage(pathlib.Path(td))
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_run_group("Alpha", "release-1")
    s.create_run(
        project="Alpha",
        group="release-1",
        name="Sprint A",
        file_name="sprint-a",
        case_paths=["Alpha/Checkout/pay.feature"],
    )

    tree = s.list_test_run_tree()
    project_node = tree["children"][0]
    assert project_node == {
        "type": "folder", "name": "Alpha", "depth": 0,
        "path": "Alpha", "children": project_node["children"],
    }, project_node
    group_node = project_node["children"][0]
    assert group_node["name"] == "release-1", group_node
    assert group_node["depth"] == 1, group_node
    assert group_node["path"] == "Alpha/test-run/release-1", group_node
    leaf = group_node["children"][0]
    assert leaf == {
        "type": "run",
        "name": "sprint-a.yaml",
        "path": "Alpha/test-run/release-1/sprint-a.yaml",
        "project": "Alpha",
        "group": "release-1",
        "file_name": "sprint-a.yaml",
    }, leaf
    print("PASS p2-s4 list_test_run_tree leaf shape")
