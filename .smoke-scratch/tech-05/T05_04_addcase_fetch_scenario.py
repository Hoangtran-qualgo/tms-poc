"""tech-05 RD-1b — newly-added rows fetch their scenario name on add.

The add-case picker only knows file paths, so a freshly-cloned result row
fetches its scenario name from the feature read API and fills the
display-only cell once resolved (RD-1 option b).

Verifies:
  1. The add-row <template> includes the `run-scenario-name` cell.
  2. `_createResultRow` wires the async fill against the new cell.
  3. `_fillScenarioName` GETs `/api/files/<path>`, reads `scenario.name`,
     and sets the cell text — failures leave the cell blank (RD-4).
  4. End-to-end: `GET /api/files/<path>` (the endpoint the fill calls)
     returns the case's scenario name.
"""
import re
import tempfile, pathlib
from app import create_app
from app.storage import Storage

# 1) Add-row template carries the scenario-name cell.
tpl = pathlib.Path("app/templates/run_editor.html").read_text()
row_tpl = re.search(
    r'<template id="run-result-row-template">(.*?)</template>', tpl, re.S
)
assert row_tpl and 'class="run-scenario-name' in row_tpl.group(1), (
    "add-row template missing the run-scenario-name cell"
)
print("PASS RD-1b add-row template includes the scenario-name cell")

# 2/3) JS wiring: _createResultRow calls _fillScenarioName; _fillScenarioName
#      fetches /api/files/<path>, reads scenario.name, fills the cell.
js = pathlib.Path("app/static/06_run_editor.js").read_text()
create = re.search(r"_createResultRow\(file_path[^)]*\)\s*\{(.*?)\n  \},", js, re.S)
assert create, "could not locate _createResultRow"
assert "_fillScenarioName(" in create.group(1) and ".run-scenario-name" in create.group(1)
print("PASS RD-1b _createResultRow wires the async scenario-name fill")

fill = re.search(r"_fillScenarioName\(cell, file_path\)\s*\{(.*?)\n  \},", js, re.S)
assert fill, "could not locate _fillScenarioName"
fb = fill.group(1)
assert "`/api/files/${file_path}`" in fb, fb
assert "data.scenario" in fb and "cell.textContent" in fb, fb
assert "catch" in fb, "fill must swallow errors and leave the cell blank (RD-4)"
print("PASS RD-1b _fillScenarioName fetches the feature API and fills the cell")

# 4) The endpoint it calls actually returns the scenario name.
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_file(["Alpha", "Checkout", "pay"], scenario_name="User pays with card")
    data = app.test_client().get(
        "/api/files/Alpha/Checkout/pay.feature",
        headers={"Accept": "application/json"},
    ).get_json()
    assert data["scenario"]["name"] == "User pays with card", data["scenario"]
    print("PASS RD-1b GET /api/files/<path> returns the scenario name used by the fill")
