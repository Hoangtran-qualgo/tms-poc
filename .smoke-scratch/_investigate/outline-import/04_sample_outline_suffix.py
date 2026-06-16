# Investigation repro (Scenario Outline import) - run individually:
#   PYTHONPATH=. .venv/bin/python .smoke-scratch/_investigate/outline-import/04_sample_outline_suffix.py
"""Grounds the REAL example-row suffix format by parsing the bundled sample
Allure report and printing every scenario name (highlighting ' -- @<n>.<m>'
suffixes). Confirms the exact token the importer must trim/retain.
"""
import pathlib
import re

from app.allure_io import parse_allure_report

SAMPLE = pathlib.Path("specs/sample-data/allure-report-single/index.html")

rep = parse_allure_report(SAMPLE.read_text())
suffix_re = re.compile(r" -- @(\d+)\.(\d+)\s*$")  # NOTE: sample has trailing space

print(f"sample created_at: {rep.created_at}")
print(f"sample scenarios ({len(rep.scenarios)}):")
seen_suffix = False
for sc in rep.scenarios:
    m = suffix_re.search(sc.name)
    tag = f"  <-- suffix n={m.group(1)} m={m.group(2)}" if m else ""
    seen_suffix = seen_suffix or bool(m)
    print(f"  [{sc.result:8}] {sc.name!r}{tag}")

print("PASS  suffixed example rows present" if seen_suffix
      else "NOTE  no ' -- @n.m' suffixes in this sample")
