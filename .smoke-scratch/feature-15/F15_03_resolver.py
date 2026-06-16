# Pattern: see .smoke-scratch/README.md
"""feature-15 / import test run / DO-3 resolver (resolve_scenarios) + retry compose.

Exercises Storage.resolve_scenarios over a seeded project:
- S1: matched (exactly one), case-insensitive on scenario name.
- S2: unmatched (no case) and ambiguous (2+ cases) classification + order.
- S3: a project with no folder leaves every name unmatched.
- S4: compose with the parser - retries collapse (IR-5b) to a single name that
  resolves to a single path (never a duplicate-file_path abort).
"""
import base64
import json
import pathlib
import tempfile

from app import create_app
from app.allure_io import parse_allure_report


def _seed():
    td = tempfile.mkdtemp()
    s = create_app(data_root=pathlib.Path(td)).extensions["storage"]
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod1"])
    s.create_folder(["proj", "mod2"])
    # Unique scenario in one folder.
    s.create_file(["proj", "mod1", "login.feature"], scenario_name="Login Works")
    # Same scenario name in two folders -> ambiguous at project scope.
    s.create_file(["proj", "mod1", "dup_a.feature"], scenario_name="Shared Name")
    s.create_file(["proj", "mod2", "dup_b.feature"], scenario_name="Shared Name")
    return s


# --- S1: matched, case-insensitive -----------------------------------------
s = _seed()
res = s.resolve_scenarios("proj", ["login works"])  # different case
assert res["matched"] == {"login works": "proj/mod1/login.feature"}, (
    f"S1: case-insensitive match, got {res['matched']!r}"
)
assert res["unmatched"] == [] and res["ambiguous"] == [], f"S1: {res!r}"
print("PASS  S1: scenario name matched case-insensitively to its single path")


# --- S2: unmatched + ambiguous classification, input order preserved -------
s = _seed()
res = s.resolve_scenarios(
    "proj", ["No Such Scenario", "Shared Name", "another missing"]
)
assert res["matched"] == {}, f"S2: none should match uniquely, got {res['matched']!r}"
assert res["ambiguous"] == ["Shared Name"], f"S2: ambiguous, got {res['ambiguous']!r}"
assert res["unmatched"] == ["No Such Scenario", "another missing"], (
    f"S2: unmatched + order, got {res['unmatched']!r}"
)
print("PASS  S2: unmatched / ambiguous classified, input order preserved")


# --- S3: project with no folder -> everything unmatched --------------------
with tempfile.TemporaryDirectory() as td:
    s = create_app(data_root=pathlib.Path(td)).extensions["storage"]
    res = s.resolve_scenarios("ghost", ["anything"])
    assert res == {"matched": {}, "unmatched": ["anything"], "ambiguous": []}, (
        f"S3: missing project -> all unmatched, got {res!r}"
    )
print("PASS  S3: project with no folder leaves every name unmatched")


# --- S4: parser retry-collapse composes to a single matched path -----------
s = _seed()
suites = {
    "name": "suites",
    "children": [
        # Two runs (retries) of the SAME scenario that exists once in the project.
        {"name": "Login Works", "status": "failed", "time": {"start": 100, "stop": 200}},
        {"name": "Login Works", "status": "passed", "time": {"start": 300, "stop": 400}},
    ],
}
summary = {"reportName": "R", "time": {"start": 100, "stop": 400}}


def _d(path, obj):
    b64 = base64.b64encode(json.dumps(obj).encode("utf-8")).decode("ascii")
    return f"d('{path}','{b64}')"


html = "<script>" + _d("data/suites.json", suites) + "," + _d("widgets/summary.json", summary) + "</script>"
report = parse_allure_report(html)
names = [sc.name for sc in report.scenarios]
assert names == ["Login Works"], f"S4: parser must collapse retries to one name, got {names!r}"
res = s.resolve_scenarios("proj", names)
# One name -> one path means the eventual RunResult list has no duplicate file_path.
assert res["matched"] == {"Login Works": "proj/mod1/login.feature"}, (
    f"S4: collapsed retry resolves to a single path, got {res['matched']!r}"
)
assert len(set(res["matched"].values())) == len(res["matched"]), (
    "S4: matched paths must be unique (no duplicate-file_path abort)"
)
print("PASS  S4: parser-collapsed retries resolve to one path (no duplicate file_path)")
