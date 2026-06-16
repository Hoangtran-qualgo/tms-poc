# Investigation repro (Scenario Outline import) - run individually:
#   .venv/bin/python .smoke-scratch/_investigate/outline-import/01_parser_splits_examples.py
"""Blocker context: Allure renders ONE Scenario Outline as N example-row leaves
named '<base> -- @1.<row>'. The feature-15 parser keys retry-collapse on the
case-folded *full* name, so these rows have DISTINCT keys and stay as N separate
scenarios (no collapse). Documents why the report yields 2 entries for 1 case.
"""
import base64
import json

from app.allure_io import parse_allure_report

BASE = "Verify retrieve agent conversations count"


def _d(path, obj):
    return f"d('{path}','{base64.b64encode(json.dumps(obj).encode()).decode()}')"


suites = {"children": [{"name": "F", "children": [
    {"name": f"{BASE} -- @1.1", "status": "passed", "time": {"start": 1, "stop": 2}},
    {"name": f"{BASE} -- @1.2", "status": "failed", "time": {"start": 3, "stop": 4}},
]}]}
html = (
    "<script>"
    + _d("data/suites.json", suites)
    + _d("widgets/summary.json", {"reportName": "R", "time": {"start": 1000}})
    + "</script>"
)

rep = parse_allure_report(html)
names = [s.name for s in rep.scenarios]
assert names == [f"{BASE} -- @1.1", f"{BASE} -- @1.2"], names
print("PASS  parser keeps outline example rows as 2 DISTINCT scenarios (no collapse):")
for sc in rep.scenarios:
    print(f"        {sc.name!r} -> {sc.result}")
