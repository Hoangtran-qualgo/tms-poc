# Pattern: see .smoke-scratch/README.md
"""feature-06 / tree-pane / HD1 storage half.

`Storage.list_tree()` filters any child literally named ``"test-run"``
of a depth-1 (project) folder. See
`specs/features/06-feature-tree-pane-NEW.md` § *Invariants & rules →
test-run/ is hidden from the directory tree*.

Moved from `.smoke-scratch/p2_s1_list_tree_hides_test_run.py` during
feature-06 Step 2 (Restructure).
"""
import pathlib
import tempfile

from app.storage import Storage


with tempfile.TemporaryDirectory() as td:
    s = Storage(pathlib.Path(td))
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])  # positive-control module
    s.create_run_group("Alpha", "release-1")  # creates Alpha/test-run/

    tree = s.list_tree()
    projects = tree["children"]
    assert len(projects) == 1, (
        f"HD1 setup: expected exactly one project, got {[p['name'] for p in projects]}"
    )
    project = projects[0]
    assert project["name"] == "Alpha", (
        f"HD1 setup: project name must be 'Alpha', got {project['name']!r}"
    )

    child_names = [c["name"] for c in project["children"]]

    # Negative invariant (HD1): the typed area MUST be filtered.
    assert "test-run" not in child_names, (
        f"HD1: Storage.list_tree() must filter the literal 'test-run' child of "
        f"a depth-1 (project) folder; got project children {child_names!r}"
    )

    # Positive control: sibling modules MUST survive the filter.
    assert "Checkout" in child_names, (
        f"HD1 positive control: sibling module 'Checkout' must appear in the "
        f"project's children (proves the filter targets only 'test-run', not all "
        f"depth-2 entries); got {child_names!r}"
    )
print("PASS  HD1 (storage half): list_tree() filters 'test-run' at depth-1 while keeping siblings")
