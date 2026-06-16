# Investigation repro (Scenario Outline import) - run individually:
#   .venv/bin/python .smoke-scratch/_investigate/outline-import/03_runmodel_rejects_dup_path.py
"""Blocker 2 (run-model uniqueness): even after trimming the suffix to the BASE
name, the two example rows would produce two RunResults with the SAME file_path
(the one outline case). validate_run rejects duplicate file_paths, and RunResult
has no per-example identity - so "2 scenarios, same case, different Examples
row" is not representable today.
"""
from app.errors import ValidationError
from app.models import RunResult, TestRun, validate_run

run = TestRun(
    name="R",
    created_at="2026-06-15T00:00:00+00:00",
    results=[
        RunResult(file_path="proj/mod/count.feature", result="PASSED"),  # @1.1
        RunResult(file_path="proj/mod/count.feature", result="FAILED"),  # @1.2
    ],
)
try:
    validate_run(run)
    raise SystemExit("FAIL  expected ValidationError on duplicate file_path")
except ValidationError as e:
    print("PASS  two example rows -> same case path rejected by validate_run:")
    print(f"        {e}")
