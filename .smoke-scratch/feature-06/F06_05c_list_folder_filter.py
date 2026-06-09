# Pattern: see .smoke-scratch/README.md
"""feature-06 / tree-pane / HD3 storage half.

`Storage.list_folder(parts)` filters ``"test-run"`` out of the
returned ``modules`` list when ``len(parts) == 1``, so
`folder_project.html`'s module table hides the typed area too. See
`specs/features/06-feature-tree-pane-NEW.md` § *Invariants & rules →
test-run/ is hidden from the directory tree* (symmetric clause).

The HTML half of HD3 (the rendered `folder_project.html` module
table) lives in `.smoke-scratch/p2_2c_project_view_hides_test_run.py`
because that template's primary frame is feature-07 (folder views).

Moved from `.smoke-scratch/p2_s2_list_folder_hides_test_run.py`
during feature-06 Step 2 (Restructure).
"""
import pathlib
import tempfile

from app.storage import Storage


with tempfile.TemporaryDirectory() as td:
    s = Storage(pathlib.Path(td))
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])  # positive-control module
    s.create_run_group("Alpha", "release-1")  # creates Alpha/test-run/

    result = s.list_folder(["Alpha"])
    assert result["kind"] == "project", (
        f"HD3 setup: list_folder(['Alpha']) must return kind='project', "
        f"got {result.get('kind')!r}"
    )
    modules = result["modules"]

    # Negative invariant (HD3): typed area filtered from modules list.
    assert "test-run" not in modules, (
        f"HD3: Storage.list_folder(['Alpha']) must filter 'test-run' from "
        f"the returned modules list (len(parts) == 1); got {modules!r}"
    )

    # Positive control: real modules survive.
    assert "Checkout" in modules, (
        f"HD3 positive control: sibling module 'Checkout' must appear in the "
        f"modules list (proves the filter targets only 'test-run'); got {modules!r}"
    )
print("PASS  HD3 (storage half): list_folder([project]) filters 'test-run' from modules")
