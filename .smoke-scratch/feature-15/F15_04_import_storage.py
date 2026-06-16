# Pattern: see .smoke-scratch/README.md
"""feature-15 / import test run / DO-2 storage write path (import_test_run).

Exercises Storage.import_test_run:
- H1: happy write preserves the report's created_at (not server-now), the
  run name/description, and per-case results in order.
- C1: duplicate file_path across results is rejected (validate_run) - nothing
  written.
- C2: NameConflictError when the run file already exists.
- C3: FileNotFoundError when the destination group does not exist.
"""
import pathlib
import tempfile
from datetime import datetime, timezone

from app import create_app
from app.errors import NameConflictError, ValidationError
from app.models import RunResult


def _storage(td):
    s = create_app(data_root=pathlib.Path(td)).extensions["storage"]
    s.create_folder(["proj"])
    s.create_run_group("proj", "grp")
    return s


REPORT_CREATED = "2026-05-01T10:00:00+00:00"


# --- H1: happy write preserves created_at, name, description, results ------
with tempfile.TemporaryDirectory() as td:
    s = _storage(td)
    results = [
        RunResult(file_path="proj/mod/a.feature", result="PASSED"),
        RunResult(file_path="proj/mod/b.feature", result="FAILED"),
        RunResult(file_path="proj/mod/c.feature", result="SKIPPED"),
    ]
    s.import_test_run(
        project="proj",
        group="grp",
        name="Imported Run",
        file_name="imported",
        created_at=REPORT_CREATED,
        results=results,
        description="from allure",
    )
    run = s.read_run("proj", "grp", "imported")
    assert run.name == "Imported Run", f"H1: name, got {run.name!r}"
    assert run.description == "from allure", f"H1: description, got {run.description!r}"
    assert run.created_at == REPORT_CREATED, (
        f"H1: created_at must be the report's time, got {run.created_at!r}"
    )
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    assert run.created_at != now_iso, "H1: created_at must not be server-now"
    assert [(r.file_path, r.result) for r in run.results] == [
        ("proj/mod/a.feature", "PASSED"),
        ("proj/mod/b.feature", "FAILED"),
        ("proj/mod/c.feature", "SKIPPED"),
    ], f"H1: results/order, got {[(r.file_path, r.result) for r in run.results]!r}"
    print("PASS  H1: import_test_run preserves report created_at + per-case results in order")


# --- C1: duplicate file_path rejected (validate_run), nothing written ------
with tempfile.TemporaryDirectory() as td:
    s = _storage(td)
    try:
        s.import_test_run(
            project="proj",
            group="grp",
            name="Dup",
            file_name="dup",
            created_at=REPORT_CREATED,
            results=[
                RunResult(file_path="proj/mod/x.feature", result="PASSED"),
                RunResult(file_path="proj/mod/x.feature", result="FAILED"),
            ],
        )
    except ValidationError as e:
        assert "file_path" in e.field or "Duplicate" in e.message, (
            f"C1: expected duplicate file_path error, got {e}"
        )
    else:
        raise AssertionError("C1: duplicate file_path must raise ValidationError")
    assert s.list_runs("proj", "grp") == [], "C1: nothing written on validation failure"
    print("PASS  C1: duplicate file_path rejected by validate_run, nothing written")


# --- C2: NameConflictError on an existing run file -------------------------
with tempfile.TemporaryDirectory() as td:
    s = _storage(td)
    base = dict(
        project="proj", group="grp", name="Run", file_name="run",
        created_at=REPORT_CREATED,
        results=[RunResult(file_path="proj/mod/a.feature", result="PASSED")],
    )
    s.import_test_run(**base)
    try:
        s.import_test_run(**base)
    except NameConflictError:
        pass
    else:
        raise AssertionError("C2: importing onto an existing file must raise NameConflictError")
    print("PASS  C2: existing run file raises NameConflictError")


# --- C3: FileNotFoundError when the group does not exist -------------------
with tempfile.TemporaryDirectory() as td:
    s = create_app(data_root=pathlib.Path(td)).extensions["storage"]
    s.create_folder(["proj"])  # project exists, but no run group created
    try:
        s.import_test_run(
            project="proj",
            group="missing",
            name="Run",
            file_name="run",
            created_at=REPORT_CREATED,
            results=[RunResult(file_path="proj/mod/a.feature", result="PASSED")],
        )
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("C3: missing group must raise FileNotFoundError")
    print("PASS  C3: missing destination group raises FileNotFoundError")
