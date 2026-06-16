# Pattern: see .smoke-scratch/README.md
"""feature-15 / import test run / DO-1 status map (IR-3) + retry collapse (IR-5b).

Pure-model smoke: exercises app.allure_io.parse_allure_report directly.

Covers:
- S1: every Allure status maps to the locked RUN_RESULTS value, incl.
  broken -> FAILED and unknown -> SKIPPED; an unrecognised status -> SKIPPED.
- S2: same-name leaves (retries) collapse to the FINAL run (latest time.stop).
- S3: retry collapse is case-insensitive and keeps the final run regardless
  of report order (final = latest stop, not last-listed).
"""
import base64
import json

from app.allure_io import parse_allure_report


def _report(leaves, summary=None):
    suites = {"name": "suites", "children": leaves}
    summary = summary or {"reportName": "R", "time": {"start": 1000, "stop": 2000}}

    def _d(path, obj):
        b64 = base64.b64encode(json.dumps(obj).encode("utf-8")).decode("ascii")
        return f"d('{path}','{b64}')"

    html = (
        "<script>"
        + _d("data/suites.json", suites) + ","
        + _d("widgets/summary.json", summary)
        + "</script>"
    )
    return parse_allure_report(html)


def _leaf(name, status, start=1000, stop=1100):
    return {"name": name, "status": status, "time": {"start": start, "stop": stop}}


# --- S1: status map (IR-3) -------------------------------------------------
cases = [
    ("passed", "PASSED"),
    ("failed", "FAILED"),
    ("broken", "FAILED"),
    ("skipped", "SKIPPED"),
    ("unknown", "SKIPPED"),
    ("totally-bogus", "SKIPPED"),  # unrecognised -> SKIPPED
]
report = _report([_leaf(f"t-{allure}", allure) for allure, _ in cases])
got = {s.name: s.result for s in report.scenarios}
for allure, expected in cases:
    assert got[f"t-{allure}"] == expected, (
        f"S1: {allure!r} must map to {expected}, got {got[f't-{allure}']!r}"
    )
print("PASS  S1: Allure statuses map to RUN_RESULTS (broken->FAILED, unknown->SKIPPED)")


# --- S2: retry collapse keeps the final run (latest stop) ------------------
# Two runs of "flaky": first failed (earlier stop), retry passed (later stop).
report = _report([
    _leaf("flaky", "failed", start=100, stop=200),
    _leaf("flaky", "passed", start=300, stop=400),
])
assert len(report.scenarios) == 1, (
    f"S2: retries must collapse to one scenario, got {len(report.scenarios)}"
)
assert report.scenarios[0].result == "PASSED", (
    f"S2: final run (latest stop) wins, got {report.scenarios[0].result!r}"
)
print("PASS  S2: same-name retries collapse to the final (latest time.stop) run")


# --- S3: collapse is case-insensitive + order-independent ------------------
# The PASSED run has the latest stop but is listed FIRST; the FAILED retry is
# listed last with an earlier stop. Final = latest stop, not last-listed.
report = _report([
    _leaf("Login Works", "passed", start=300, stop=900),
    _leaf("login works", "failed", start=100, stop=200),
])
assert len(report.scenarios) == 1, (
    f"S3: case-folded retries must collapse, got {len(report.scenarios)}"
)
assert report.scenarios[0].result == "PASSED", (
    f"S3: latest-stop run must win regardless of order, got "
    f"{report.scenarios[0].result!r}"
)
print("PASS  S3: retry collapse is case-insensitive and picks latest stop, not last-listed")
