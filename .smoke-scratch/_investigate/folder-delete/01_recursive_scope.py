"""Spike: generic folder deletion recurses through visible and typed project data."""
import pathlib
import tempfile

from app.storage import Storage


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    storage = Storage(root)
    storage.create_folder(["project"])
    storage.create_folder(["project", "module"])
    storage.create_folder(["project", "module", "branch"])
    storage.create_file(
        ["project", "module", "case"], "", scenario_name="Case"
    )
    storage.create_file(
        ["project", "module", "branch", "deep-case"], "", scenario_name="Deep case"
    )

    storage.delete_folder(["project", "module"])
    assert not (root / "project" / "module").exists(), (
        "module deletion must remove sub-folders and every nested test case"
    )
    assert (root / "project" / "enums.yaml").is_file(), (
        "module deletion must not remove sibling project configuration"
    )
    print("PASS module deletion recursively removes only the selected branch")

    storage.create_folder(["project", "module"])
    storage.create_run_group("project", "release")
    report_dir = root / "project" / "report"
    report_dir.mkdir()
    (report_dir / "quality.yaml").write_text("type: tag_inventory\n", encoding="utf-8")

    storage.delete_folder(["project"])
    assert not (root / "project").exists(), (
        "project deletion must remove enums, test-run, report, and all folders"
    )
    print("PASS project deletion also removes hidden typed areas and enums")
