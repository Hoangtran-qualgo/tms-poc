"""tech-09 / Scenario-Outline in test runs / DO-5 manual add + round-trip.

Two halves:

A) Static JS wiring (`06_run_editor.js`) for A4 + BS-F:
   - `_expandCasePaths` turns an outline into one {file_path, example} entry per
     Examples data row (1-based {table,row}); plain/unreadable -> one null entry.
   - the "+ Add test case" confirm runs the expansion before building rows.
   - `_createResultRow(file_path, example=...)` stamps `data-example`.
   - `_readCurrent` carries the example; `_compareJson`/`_sortKey` key on it so
     same-path outline rows stay stable across dirty / Save / disk compares.

B) HTTP round-trip (BS-F): PATCH a run with per-example results -> the example
   survives the wire (GET returns it), order preserved; a duplicate (file_path,
   example) is rejected 422 while distinct examples on one path are accepted.
"""
import json
import re
import pathlib
import tempfile

from app import create_app
from app.storage import Storage

# ---------------------------------------------------------------- A) JS wiring
js = pathlib.Path("app/static/06_run_editor.js").read_text()


def body_of(name):
    m = re.search(rf"{name}\([^)]*\)\s*\{{(.*?)\n  \}},", js, re.S)
    assert m, f"could not locate {name} in 06_run_editor.js"
    return m.group(1)

expand = body_of("_expandCasePaths")
assert 'scenario.kind === "outline"' in expand, expand
assert "table: ti + 1" in expand and "row: ri + 1" in expand, expand
assert "example: null" in expand, "plain/unreadable case must fall back to one null entry"
print("PASS  A4: _expandCasePaths expands an outline into one entry per Examples row")

add = body_of("_onAddCaseClicked")
assert "_expandCasePaths(" in add, "add-case confirm must expand picked paths first"
print("PASS  A4: the add-case flow runs outline expansion before building rows")

create = body_of("_createResultRow")
assert re.search(r"_createResultRow\(file_path[^)]*example", js), "signature must accept example"
assert "tr.dataset.example" in create, "_createResultRow must stamp data-example"
print("PASS  BS-F: _createResultRow stamps the example onto data-example")

read = body_of("_readCurrent")
assert "_exampleOf(tr)" in read and "result.example" in read, read
print("PASS  BS-F: _readCurrent carries the per-row example into the snapshot")

compare = body_of("_compareJson")
assert "r.example" in compare and "_sortKey" in compare, compare
print("PASS  BS-F: _compareJson canonicalises + sorts on the example coordinate")


# --------------------------------------------------------- B) HTTP round-trip
OUTLINE = """Feature: count
  Scenario Outline: Verify count
    Given <n> items
  Examples:
    | n |
    | 1 |
    | 2 |
"""
PATH = "P/mod/count.feature"

with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s: Storage = app.extensions["storage"]
    s.create_folder(["P"])
    s.create_folder(["P", "mod"])
    s.create_file(["P", "mod", "count"], scenario_name="Verify count")
    s.write_raw(PATH, OUTLINE)
    s.create_run_group("P", "g")
    s.create_run(project="P", group="g", name="R", file_name="r", case_paths=[PATH])
    created_at = s.read_run("P", "g", "r.yaml").created_at
    c = app.test_client()

    def patch(results):
        return c.patch(
            "/api/runs/P/g/r.yaml",
            data=json.dumps({
                "name": "R", "created_at": created_at,
                "description": "", "results": results,
            }),
            content_type="application/json",
        )

    # Two distinct example rows on the one outline path -> accepted.
    r = patch([
        {"file_path": PATH, "result": "PASSED", "remark": "a", "example": {"table": 1, "row": 1}},
        {"file_path": PATH, "result": "FAILED", "remark": "b", "example": {"table": 1, "row": 2}},
    ])
    assert r.status_code == 200, (r.status_code, r.get_data(as_text=True))
    got = [(x["file_path"], x["result"], x["remark"], x.get("example"))
           for x in c.get("/api/runs/P/g/r.yaml").get_json()["results"]]
    assert got == [
        (PATH, "PASSED", "a", {"table": 1, "row": 2 - 1}),
        (PATH, "FAILED", "b", {"table": 1, "row": 2}),
    ], f"BS-F: example must survive the PATCH wire in order, got {got!r}"
    print("PASS  BS-F: PATCH round-trips per-example results (order + example preserved)")

    # Same (file_path, example) twice -> rejected at write (422).
    r = patch([
        {"file_path": PATH, "result": "PASSED", "example": {"table": 1, "row": 1}},
        {"file_path": PATH, "result": "FAILED", "example": {"table": 1, "row": 1}},
    ])
    assert r.status_code == 422, (r.status_code, r.get_data(as_text=True))
    assert r.get_json()["error"]["code"] == "validation_error", r.get_json()
    print("PASS  BS-F: duplicate (file_path, example) is rejected 422 on PATCH")
