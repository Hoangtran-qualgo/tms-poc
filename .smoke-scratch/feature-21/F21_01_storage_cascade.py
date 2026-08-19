# Pattern: see .smoke-scratch/README.md
"""feature-21 / rename cascade and failed-write compensation."""

from pathlib import Path
from tempfile import TemporaryDirectory

from app.errors import RunParseError
from app.models import Report
from app.storage import Storage


def seed(root: Path) -> Storage:
    storage = Storage(root)
    storage.create_folder(["project"])
    storage.create_folder(["project", "module"])
    storage.create_folder(["project", "module", "branch"])
    storage.create_folder(["project", "module-other"])
    for parts, scenario_name in [
        (["project", "module", "case.feature"], "case"),
        (["project", "module", "branch", "nested.feature"], "nested"),
        (["project", "module-other", "keep.feature"], "keep"),
    ]:
        storage.create_file(parts, scenario_name=scenario_name)
    storage.create_run_group("project", "group")
    storage.create_run(
        "project",
        "group",
        "run",
        "run.yaml",
        [
            "project/module/case.feature",
            "project/module/branch/nested.feature",
            "project/module-other/keep.feature",
        ],
    )
    storage.create_report(
        "project",
        "trend.yaml",
        Report(
            type="case_trend",
            title="trend",
            case_path="project/module/case.feature",
            run_paths=["project/test-run/group/run.yaml"],
        ),
    )
    storage.create_report(
        "project",
        "inventory.yaml",
        Report(
            type="tag_inventory",
            title="inventory",
            tag="smoke",
            scope="project/module",
        ),
    )
    storage.create_report(
        "project",
        "ranking.yaml",
        Report(
            type="tag_ranking",
            title="ranking",
            status="PASSED",
            run_paths=["project/test-run/group/run.yaml"],
        ),
    )
    return storage


with TemporaryDirectory() as td:
    storage = seed(Path(td))

    storage.rename_file(["project", "module", "case.feature"], "primary")
    run = storage.read_run("project", "group", "run.yaml")
    assert [r.file_path for r in run.results] == [
        "project/module/primary.feature",
        "project/module/branch/nested.feature",
        "project/module-other/keep.feature",
    ], "TC1: file rename updates exact run reference only"
    assert storage.read_report("project", "trend.yaml").case_path == (
        "project/module/primary.feature"
    ), "TC2: file rename updates exact case-trend reference"

    storage.rename_folder(["project", "module"], "renamed")
    run = storage.read_run("project", "group", "run.yaml")
    assert [r.file_path for r in run.results] == [
        "project/renamed/primary.feature",
        "project/renamed/branch/nested.feature",
        "project/module-other/keep.feature",
    ], "TC3: folder rename rewrites descendants with a slash boundary"
    assert storage.read_report("project", "trend.yaml").case_path == (
        "project/renamed/primary.feature"
    ), "TC4: folder rename updates report case path"
    assert storage.read_report("project", "inventory.yaml").scope == (
        "project/renamed"
    ), "TC5: folder rename updates report scope"
    assert storage.read_report("project", "ranking.yaml").run_paths == [
        "project/test-run/group/run.yaml"
    ], "TC6: module rename leaves run paths outside its subtree unchanged"

    storage.rename_folder(["project"], "renamed-project")
    run = storage.read_run("renamed-project", "group", "run.yaml")
    assert [r.file_path for r in run.results] == [
        "renamed-project/renamed/primary.feature",
        "renamed-project/renamed/branch/nested.feature",
        "renamed-project/module-other/keep.feature",
    ], "TC7: project rename updates every run result"
    trend = storage.read_report("renamed-project", "trend.yaml")
    assert trend.case_path == "renamed-project/renamed/primary.feature"
    assert trend.run_paths == ["renamed-project/test-run/group/run.yaml"], (
        "TC8: project rename updates report case and run paths"
    )
    assert storage.read_report("renamed-project", "inventory.yaml").scope == (
        "renamed-project/renamed"
    ), "TC9: project rename updates report scope"


with TemporaryDirectory() as td:
    root = Path(td)
    storage = seed(root)
    original_write = storage._atomic_write_bytes

    def fail_report_write(path, data):
        if path.name == "trend.yaml":
            raise OSError("injected report write failure")
        original_write(path, data)

    storage._atomic_write_bytes = fail_report_write
    try:
        storage.rename_file(["project", "module", "case.feature"], "primary")
    except OSError as exc:
        assert str(exc) == "injected report write failure"
    else:
        raise AssertionError("TC10: failed cascade must propagate its write error")
    assert (root / "project" / "module" / "case.feature").is_file(), (
        "TC11: failed cascade restores physical source"
    )
    assert not (root / "project" / "module" / "primary.feature").exists(), (
        "TC12: failed cascade removes physical destination"
    )
    assert storage.read_run("project", "group", "run.yaml").results[0].file_path == (
        "project/module/case.feature"
    ), "TC13: failed cascade restores prior metadata"


with TemporaryDirectory() as td:
    root = Path(td)
    storage = Storage(root)
    storage.create_folder(["project"])
    storage.create_folder(["project", "module"])
    storage.create_file(["project", "module", "case.feature"], scenario_name="case")
    storage.create_run_group("project", "group")
    (root / "project" / "test-run" / "group" / "broken.yaml").write_text(
        "not: [valid", encoding="utf-8"
    )
    try:
        storage.rename_file(["project", "module", "case.feature"], "primary")
    except RunParseError:
        pass
    else:
        raise AssertionError("TC14: malformed run metadata must block rename")
    assert (root / "project" / "module" / "case.feature").is_file(), (
        "TC15: malformed metadata leaves source in place"
    )


print("PASS  TC1-TC15: rename cascades typed paths, respects boundaries, and compensates failures")
