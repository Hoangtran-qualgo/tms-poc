"""A 'test-run' folder at depth 3 is NOT a reserved area: list_tree still
shows it AND list_test_run_tree must ignore it (only depth-2 test-run/
folders are the typed area)."""
import tempfile, pathlib
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    s = Storage(pathlib.Path(td))
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_folder(["Alpha", "Checkout", "test-run"])  # depth-3, allowed

    # list_tree shows it (filter is depth-1-only)
    alpha = s.list_tree()["children"][0]
    checkout = next(c for c in alpha["children"] if c["name"] == "Checkout")
    deep_names = [c["name"] for c in checkout["children"]]
    assert "test-run" in deep_names, deep_names

    # list_test_run_tree must skip Alpha entirely (no depth-2 test-run/)
    tree = s.list_test_run_tree()
    assert tree["children"] == [], tree
    print("PASS p2-s5 depth-3 'test-run' is not a typed area")
