# Pattern: see .smoke-scratch/README.md
"""tech-02 / E2 / run editor JS touch-points for folder grouping.

specs/tech/02 § E2 (Serialize/dirty integration + Order-sensitivity): the run
editor's JS must treat heading rows as non-results and keep comparisons
order-insensitive while persisting grouped DOM order. Static JS inspection.

Asserts on 06_run_editor.js:
1. _readCurrent + the add-flow exclude set + _afterRowsChanged all read result
   rows via `tr[data-file-path]` (so `run-group-head` rows are skipped).
2. _compareJson sorts results by file_path before stringify (order-insensitive
   compare), and is used for baseline / live / disk comparisons.
3. _insertResultRow places added cases in their folder group (creating a
   heading), and remove drops an empty heading via _groupIsEmpty.
"""
import pathlib
import re

JS = (pathlib.Path("app/static") / "06_run_editor.js").read_text(encoding="utf-8")

# 1. Result-row reads are scoped to tr[data-file-path].
assert JS.count('tr[data-file-path]') >= 3, (
    "result-row queries (_readCurrent, exclude set, _afterRowsChanged) must "
    "scope to tr[data-file-path] so heading rows are skipped"
)
assert 'querySelectorAll("tr[data-file-path]").length' in JS, (
    "_afterRowsChanged must count result rows via tr[data-file-path]"
)

# 2. _compareJson sorts by file_path and drives the comparisons.
assert "_compareJson(snapshot)" in JS, "E2: _compareJson projection must exist"
cmp_body = re.search(r"_compareJson\(snapshot\)\s*\{.*?\n  \},", JS, re.S).group(0)
assert ".sort(" in cmp_body and "file_path" in cmp_body, (
    "_compareJson must sort results by file_path (order-insensitive compare)"
)
assert "this._compareJson(this._readCurrent())" in JS, (
    "baseline/live comparisons must go through _compareJson"
)

# 3. Folder-group insertion + empty-heading cleanup.
assert "_insertResultRow(tbody, " in JS, "add-flow must insert via _insertResultRow"
assert "_createGroupHead(" in JS, "_insertResultRow must create a heading for a new folder"
assert "run-group-head-template" in JS, "headings cloned from the server template"
assert "_groupIsEmpty(head)" in JS and "head.remove()" in JS, (
    "remove handler must drop a folder heading once its group is empty"
)

print("PASS  T02_06: E2 JS touch-points — tr[data-file-path] reads, _compareJson, group insert/cleanup")
