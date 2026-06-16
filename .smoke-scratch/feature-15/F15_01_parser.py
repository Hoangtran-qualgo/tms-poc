# Pattern: see .smoke-scratch/README.md
"""feature-15 / import test run / DO-1 parser happy-path + structure.

Pure-model smoke: exercises app.allure_io.parse_allure_report directly.

Covers:
- S1: the real single-file sample decodes to report_name, a created_at
  derived from summary.time.start (NOT server-now), and 10 PASSED scenarios.
- S2: a synthetic nested suites.json (epic -> feature -> story -> test)
  flattens depth-agnostically to its leaves.
- S3: non-Allure / malformed input raises ValueError (-> HTTP 400).
"""
import base64
import json
from datetime import datetime, timezone
from pathlib import Path

from app.allure_io import parse_allure_report

SAMPLE = Path("specs/sample-data/allure-report-single/index.html")


def _d(path, obj):
    """Render one Allure embedded-data call d('<path>','<b64-of-json>')."""
    b64 = base64.b64encode(json.dumps(obj).encode("utf-8")).decode("ascii")
    return f"d('{path}','{b64}')"


# --- S1: real sample -------------------------------------------------------
html = SAMPLE.read_text(encoding="utf-8")
report = parse_allure_report(html)

assert report.report_name == "Allure Report", (
    f"S1: report_name, got {report.report_name!r}"
)
# created_at must equal the transform applied to the report's OWN embedded
# summary.time.start (read straight from the sample, no magic constant).
import re as _re

_blobs = dict(_re.findall(r"d\(\s*'([^']+)'\s*,\s*'([^']*)'\s*\)", html))
_start_ms = json.loads(base64.b64decode(_blobs["widgets/summary.json"]))["time"]["start"]
expected_created = datetime.fromtimestamp(
    _start_ms / 1000, tz=timezone.utc
).isoformat(timespec="seconds")
assert report.created_at == expected_created, (
    f"S1: created_at must come from summary.time.start ({expected_created}), "
    f"got {report.created_at!r}"
)
# Deterministic (report-derived, never server-now): re-parsing yields the same.
assert parse_allure_report(html).created_at == report.created_at, (
    "S1: created_at must be deterministic (derived from the report, not the clock)"
)
assert len(report.scenarios) == 9, (
    f"S1: expected 9 distinct scenarios, got {len(report.scenarios)}"
)
assert all(s.result == "PASSED" for s in report.scenarios), (
    f"S1: all sample scenarios are PASSED, got "
    f"{sorted({s.result for s in report.scenarios})}"
)
names = {s.name for s in report.scenarios}
assert "Verify CRUD agent conversation" in names, (
    f"S1: expected a known scenario name, got {sorted(names)!r}"
)
print("PASS  S1: real sample -> name + summary-derived created_at + 9 PASSED")


# --- S2: synthetic nested suites flatten depth-agnostically ----------------
nested_suites = {
    "name": "suites",
    "children": [
        {
            "name": "Epic A",
            "children": [
                {
                    "name": "Feature A1",
                    "children": [
                        {"name": "deep test 1", "status": "passed",
                         "time": {"start": 1000, "stop": 1100}},
                        {"name": "deep test 2", "status": "failed",
                         "time": {"start": 1000, "stop": 1200}},
                    ],
                },
            ],
        },
        {"name": "shallow test", "status": "skipped",
         "time": {"start": 900, "stop": 950}},
    ],
}
summary = {"reportName": "Nested", "time": {"start": 5000, "stop": 9000}}
nested_html = (
    "<html><script>Promise.allSettled(["
    + _d("data/suites.json", nested_suites) + ","
    + _d("widgets/summary.json", summary)
    + "])</script></html>"
)
nested = parse_allure_report(nested_html)
assert nested.report_name == "Nested", f"S2: report_name, got {nested.report_name!r}"
got = {s.name: s.result for s in nested.scenarios}
assert got == {
    "deep test 1": "PASSED",
    "deep test 2": "FAILED",
    "shallow test": "SKIPPED",
}, f"S2: nested tree did not flatten to all leaves, got {got!r}"
print("PASS  S2: nested suite tree flattens depth-agnostically to its leaves")


# --- S3: malformed / non-Allure input -> ValueError ------------------------
for bad in ("<html>no embedded data here</html>", "", "not html at all"):
    try:
        parse_allure_report(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"S3: {bad!r} must raise ValueError")

# Has the d() loader shape but no suites.json key -> still rejected.
only_summary = (
    "<html><script>" + _d("widgets/summary.json", summary) + "</script></html>"
)
try:
    parse_allure_report(only_summary)
except ValueError:
    pass
else:
    raise AssertionError("S3: missing data/suites.json must raise ValueError")
print("PASS  S3: non-Allure / malformed / suites-less input raises ValueError")
