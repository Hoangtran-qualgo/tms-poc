"""Prove the current physical renames leave stored path references stale.

Run: PYTHONPATH=. .venv/bin/python \
  .smoke-scratch/_investigate/rename-ui/01_stale_references.py
"""

from __future__ import annotations

import pathlib
import tempfile

from app import create_app
from app.errors import ValidationError
from app.models import Report


def seeded_storage():
    root = tempfile.TemporaryDirectory()
    storage = create_app(data_root=pathlib.Path(root.name)).extensions["storage"]
    storage.create_folder(["project"])
    storage.create_folder(["project", "module"])
    storage.create_file(
        ["project", "module", "case.feature"], "", scenario_name="case"
    )
    storage.create_run_group("project", "group")
    storage.create_run(
        "project",
        "group",
        "run",
        "run.yaml",
        ["project/module/case.feature"],
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
    return root, storage


# File rename moves the case but not RunResult.file_path or Report.case_path.
root, storage = seeded_storage()
try:
    storage.rename_file(["project", "module", "case.feature"], "next")
    assert storage.read_feature(["project", "module", "next.feature"])
    assert storage.read_run("project", "group", "run.yaml").results[0].file_path == (
        "project/module/case.feature"
    )
    report = storage.read_report("project", "trend.yaml")
    try:
        storage.write_report("project", "trend.yaml", report)
    except ValidationError as exc:
        assert exc.field == "case_path", exc
    else:
        raise AssertionError("renamed case must make the report reference invalid")
    print("PASS  file rename leaves run/report case paths stale")
finally:
    root.cleanup()


# Project rename moves typed files, but their data-root-relative paths stay old.
root, storage = seeded_storage()
try:
    storage.rename_folder(["project"], "renamed-project")
    assert storage.read_feature(["renamed-project", "module", "case.feature"])
    assert storage.read_run(
        "renamed-project", "group", "run.yaml"
    ).results[0].file_path == "project/module/case.feature"
    report = storage.read_report("renamed-project", "trend.yaml")
    try:
        storage.write_report("renamed-project", "trend.yaml", report)
    except ValidationError as exc:
        assert exc.field == "run_paths[0]", exc
    else:
        raise AssertionError("renamed project must make report run path invalid")
    print("PASS  project rename leaves run/report project paths stale")
finally:
    root.cleanup()
