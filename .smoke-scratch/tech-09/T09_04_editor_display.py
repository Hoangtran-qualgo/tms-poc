"""tech-09 / Scenario-Outline in test runs / DO-4 run-editor display.

Verifies the run editor renders per-example results (server-side, via /ui/run):
- D1: an outline result shows the base scenario name PLUS its Examples header +
  matched data row (`| n | label |` / `| 1 | one |`), keyed by `data-example`.
- D3 tolerant-blank: a result whose table/row falls outside the live Examples
  (or a non-outline case) shows the base name only — no example block, no error.
- DQ1 tombstone: a removed case strikes the filename and renders a "file has
  been removed" note UNDER it in the Test-case column; the old remark-column
  "test case was removed" override is gone; the scenario-name cell is blank.
- The scenario-name cell stays display-only (no nested input/select/textarea).
"""
import re
import tempfile, pathlib
from app import create_app
from app.storage import Storage
from app.models import RunResult

OUTLINE = """Feature: count
  Scenario Outline: Verify count
    Given <n> items
    Then it is <label>
  Examples:
    | n | label |
    | 1 | one |
    | 2 | two |
"""


def scenario_cell(row_html):
    return re.search(
        r'<td class="run-scenario-name[^"]*"[^>]*>(.*?)</td>', row_html, re.S
    )


def row_with_example(ex, doc):
    return re.search(
        rf'<tr[^>]*data-example="{re.escape(ex)}"[^>]*>(.*?)</tr>', doc, re.S
    )


PATH = "P/mod/count.feature"

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["P"])
    s.create_folder(["P", "mod"])
    s.create_file(["P", "mod", "count"], scenario_name="Verify count")
    s.write_raw(PATH, OUTLINE)
    s.create_run_group("P", "g")
    s.create_run(project="P", group="g", name="R", file_name="r", case_paths=[PATH])
    # Per-example results on the one outline path: two valid + two out-of-range.
    run = s.read_run("P", "g", "r")
    run.results = [
        RunResult(file_path=PATH, result="PASSED", example={"table": 1, "row": 1}),
        RunResult(file_path=PATH, result="FAILED", example={"table": 1, "row": 2}),
        RunResult(file_path=PATH, result="SKIPPED", example={"table": 1, "row": 9}),
        RunResult(file_path=PATH, result="SKIPPED", example={"table": 2, "row": 1}),
    ]
    s.write_run("P", "g", "r", run)

    client = app.test_client()
    html = client.get("/ui/run/P/g/r.yaml").get_data(as_text=True)

    # --- D1: valid example rows show base + header + matched data row --------
    cell11 = scenario_cell(row_with_example("1.1", html).group(1)).group(1)
    assert "Verify count" in cell11 and "run-example" in cell11, cell11
    assert "| n | label |" in cell11 and "| 1 | one |" in cell11, cell11
    cell12 = scenario_cell(row_with_example("1.2", html).group(1)).group(1)
    assert "| 2 | two |" in cell12 and "| 1 | one |" not in cell12, cell12
    # display-only — no form control inside the scenario cell.
    assert not re.search(r"<(input|select|textarea)", cell11), cell11
    print("PASS  D1: outline result renders base name + Examples header + matched row")

    # --- D3: out-of-range table/row -> base name only, no example block ------
    for ex in ("1.9", "2.1"):
        cell = scenario_cell(row_with_example(ex, html).group(1)).group(1)
        assert "Verify count" in cell, (ex, cell)
        assert "run-example" not in cell and "|" not in cell, (
            f"D3: example {ex} must degrade to base-only, got {cell!r}"
        )
    print("PASS  D3: out-of-range example degrades to base-name-only (tolerant blank)")

    # --- DQ1: remove the case -> tombstone cue moves under the filename ------
    (root / PATH).unlink()
    html2 = client.get("/ui/run/P/g/r.yaml").get_data(as_text=True)
    assert "file has been removed" in html2, "DQ1: missing 'file has been removed' note"
    assert "run-removed-note" in html2, "DQ1: removed note element missing"
    assert "test case was removed" not in html2, (
        "DQ1: the old remark-column override must be gone"
    )
    assert "line-through" in html2, "DQ1: removed filename should be struck through"
    # All rows share the removed path -> scenario cells blank (no example block).
    miss_cell = scenario_cell(row_with_example("1.1", html2).group(1)).group(1)
    assert miss_cell.strip() == "" and "run-example" not in miss_cell, (
        f"DQ1: removed-case scenario cell must be blank, got {miss_cell!r}"
    )
    print("PASS  DQ1: removed case -> 'file has been removed' under filename; no override; blank cell")
