# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S2 -- create-time cross-check matrix.

Asserts _cross_check_report (project-relative existence) on top of the
pure validate_report rules, and that a rejected create writes NOTHING:
- unknown enum kind, missing run, wrong-project run, missing scope,
  missing case_path, > 10 runs all raise and create no file/area.
- an empty run set is accepted (D13).
"""
import tempfile, pathlib

from app import create_app
from app.storage import Storage
from app.models import Report
from app.errors import ValidationError


def rejects(s, file_name, report, field=None):
    try:
        s.create_report("Alpha", file_name, report)
    except ValidationError as e:
        if field is not None:
            assert e.field == field, f"expected field {field!r}, got {e.field!r}"
    else:
        raise AssertionError(f"expected ValidationError for {file_name}")
    # nothing written for the rejected create.
    try:
        s.read_report("Alpha", file_name)
        raise AssertionError(f"rejected create must not write {file_name}")
    except FileNotFoundError:
        pass


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "mod"])
    s.create_file(["Alpha", "mod", "a.feature"], "desc")
    s.create_run_group("Alpha", "g")
    s.create_run(project="Alpha", group="g", name="r1", file_name="r1", case_paths=[])
    run_path = "Alpha/test-run/g/r1.yaml"

    BASE = dict(title="t")

    # unknown enum kind (not in enums.yaml vocab).
    rejects(s, "k1", Report(type="enum_ranking", status="FAILED", kind="ghostkind",
                            run_paths=[run_path], **BASE), "kind")
    # missing run file.
    rejects(s, "k2", Report(type="enum_ranking", status="FAILED", kind="components",
                            run_paths=["Alpha/test-run/g/nope.yaml"], **BASE), "run_paths[0]")
    # run path belongs to a different project.
    rejects(s, "k3", Report(type="tag_ranking", status="FAILED",
                            run_paths=["Beta/test-run/g/r1.yaml"], **BASE), "run_paths[0]")
    # > 10 runs (pure rule, caught before cross-check).
    rejects(s, "k4", Report(type="tag_ranking", status="FAILED",
                            run_paths=[f"Alpha/test-run/g/r{i}.yaml" for i in range(11)],
                            **BASE), "run_paths")
    # missing scope folder.
    rejects(s, "k5", Report(type="tag_inventory", tag="smoke", scope="Alpha/ghost", **BASE), "scope")
    # missing case_path file.
    rejects(s, "k6", Report(type="case_trend", case_path="Alpha/mod/nope.feature", **BASE), "case_path")

    # report/ area was never created by any rejected create.
    assert not (root / "Alpha" / "report").exists(), "rejected creates must not mkdir report/"

    # empty run set is accepted (D13).
    s.create_report("Alpha", "ok", Report(type="enum_ranking", status="FAILED",
                                          kind="components", run_paths=[], **BASE))
    assert s.read_report("Alpha", "ok.yaml").run_paths == []

print("PASS  F12_12: cross-check rejects bad refs + writes nothing; empty run set OK")
