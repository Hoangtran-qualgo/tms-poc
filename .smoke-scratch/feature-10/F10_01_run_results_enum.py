"""Smoke k1: RUN_RESULTS renames IN-PROGRESS → EXECUTING (model layer).

Tracks the "Rename run-result status IN-PROGRESS → EXECUTING" Must-have
item. Model-layer assertions only.

Three assertions:
1. The `RUN_RESULTS` tuple contains `EXECUTING` and not `IN-PROGRESS`.
2. `validate_run` accepts a TestRun whose result is `EXECUTING`.
3. `validate_run` rejects a TestRun whose result is `IN-PROGRESS`
   with a ValidationError pointing at `.result` and an error message
   that lists the new valid set (so the hard-cutover diagnostic
   actually surfaces the rename to the operator).
"""
from app.errors import ValidationError
from app.models import RUN_RESULTS, RunResult, TestRun, validate_run

# --- 1. RUN_RESULTS membership ---------------------------------------
assert "EXECUTING" in RUN_RESULTS, RUN_RESULTS
assert "IN-PROGRESS" not in RUN_RESULTS, RUN_RESULTS
print(f"PASS  RUN_RESULTS contains EXECUTING and not IN-PROGRESS: {RUN_RESULTS}")

# --- 2. validate_run accepts EXECUTING -------------------------------
ok = TestRun(
    name="Smoke",
    created_at="2026-06-08T00:00:00",
    results=[RunResult(file_path="Alpha/feat.feature", result="EXECUTING")],
)
validate_run(ok)  # should not raise
print("PASS  validate_run accepts result='EXECUTING'")

# --- 3. validate_run rejects IN-PROGRESS with a useful message -------
bad = TestRun(
    name="Smoke",
    created_at="2026-06-08T00:00:00",
    results=[RunResult(file_path="Alpha/feat.feature", result="IN-PROGRESS")],
)
try:
    validate_run(bad)
except ValidationError as e:
    msg = str(e)
    assert "IN-PROGRESS" in msg, f"error should echo the rejected value; got: {msg!r}"
    assert "EXECUTING" in msg, (
        "error should list the new valid set so the operator sees the rename; "
        f"got: {msg!r}"
    )
    # The error path is at `results[<i>].result` per validate_run's locator.
    assert ".result" in (getattr(e, "field", "") or msg), (
        f"error should locate the offending field; got field={getattr(e, 'field', None)!r}, msg={msg!r}"
    )
    print(f"PASS  validate_run rejects result='IN-PROGRESS' with diagnostic: {msg}")
else:
    raise AssertionError("validate_run should have raised on result='IN-PROGRESS'")
