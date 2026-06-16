# Pattern: see .smoke-scratch/README.md
"""tech-09 / Scenario-Outline in test runs / DO-2 RunResult.example + uniqueness.

Pure-model smoke: exercises app.models RunResult / TestRun / validate_run.

Covers:
- D2 uniqueness: same file_path + DIFFERENT {table,row} is allowed; same
  file_path + SAME example is rejected; two plain results (both example=None)
  on one path are still rejected (legacy invariant preserved).
- R1 legacy shape: a plain result's to_dict() is EXACTLY {file_path,result,
  remark} (no `example` key); an outline result includes `example`.
- from_dict coercion + YAML round-trip: example survives a
  to_dict -> yaml.safe_dump -> safe_load -> from_dict cycle; malformed example
  payloads coerce to None.
"""
import yaml

from app.errors import ValidationError
from app.models import RunResult, TestRun, validate_run

CREATED = "2026-06-15T11:17:26+00:00"


def _run(results):
    return TestRun(name="r", created_at=CREATED, description="", results=results)


# --- D2: uniqueness key is (file_path, example) ----------------------------
# same path, two distinct example rows -> OK
validate_run(_run([
    RunResult(file_path="P/count.feature", result="PASSED", example={"table": 1, "row": 1}),
    RunResult(file_path="P/count.feature", result="FAILED", example={"table": 1, "row": 2}),
]))
print("PASS  D2a: same path + distinct {table,row} validates")

# same path, SAME example -> rejected
for dup in (
    [RunResult(file_path="P/c.feature", example={"table": 1, "row": 1}),
     RunResult(file_path="P/c.feature", example={"table": 1, "row": 1})],
    [RunResult(file_path="P/c.feature"), RunResult(file_path="P/c.feature")],  # both None (legacy)
):
    try:
        validate_run(_run(dup))
    except ValidationError:
        pass
    else:
        raise AssertionError(f"D2b: duplicate (file_path, example) must reject: {dup!r}")
print("PASS  D2b: same path + same example (or both plain) rejected")


# --- R1: legacy to_dict() shape is unchanged for plain results -------------
plain = RunResult(file_path="P/a.feature", result="PASSED", remark="ok")
assert plain.to_dict() == {
    "file_path": "P/a.feature", "result": "PASSED", "remark": "ok",
}, f"R1: plain result must omit `example`, got {plain.to_dict()!r}"

outline = RunResult(file_path="P/c.feature", result="FAILED",
                    example={"table": 2, "row": 3})
assert outline.to_dict() == {
    "file_path": "P/c.feature", "result": "FAILED", "remark": "",
    "example": {"table": 2, "row": 3},
}, f"R1: outline result must include `example`, got {outline.to_dict()!r}"
print("PASS  R1: plain to_dict omits `example`; outline includes it")


# --- from_dict coercion + YAML round-trip ----------------------------------
run = _run([
    RunResult(file_path="P/c.feature", result="PASSED", example={"table": 1, "row": 2}),
    RunResult(file_path="P/a.feature", result="SKIPPED"),
])
reloaded = TestRun.from_dict(yaml.safe_load(yaml.safe_dump(run.to_dict(), sort_keys=False)))
assert reloaded.results[0].example == {"table": 1, "row": 2}, (
    f"RT: example must survive YAML round-trip, got {reloaded.results[0].example!r}"
)
assert reloaded.results[1].example is None, "RT: plain result stays example=None"

# Malformed example payloads coerce to None (never crash).
for bad in ({"table": 1}, {"row": 2}, {"table": "x", "row": 1}, [1, 2], "1.2", None):
    assert RunResult.from_dict({"file_path": "p", "example": bad}).example is None, (
        f"RT: malformed example {bad!r} must coerce to None"
    )
print("PASS  RT: example round-trips through YAML; malformed -> None")
