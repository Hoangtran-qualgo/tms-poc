"""tech-09 / Scenario-Outline in test runs / DO-6 end-to-end on the real sample.

Drives the whole DO-1 -> DO-5 chain against the bundled Allure report
(`specs/sample-data/allure-report-single/index.html`, 9 PASSED scenarios where
two are the outline rows `... count -- @1.1`/`@1.2`):

- import PREVIEW: all 9 rows matched; per-row counts (matched=9, NOT 8 distinct
  bases); the two count rows resolve to the SAME case with example {1,1}/{1,2}.
- import COMMIT: writes a run with 9 results carrying the sample's created_at;
  the two count results share one path with distinct examples (no duplicate
  rejection); plain rows carry no example.
- run EDITOR (/ui/run): renders the count outline rows with the base name + live
  Examples header + matched data row, keyed by data-example; plain rows render
  with no example block.
"""
import pathlib
import re

from app import create_app
from app.storage import Storage

SAMPLE = pathlib.Path("specs/sample-data/allure-report-single/index.html").read_text(encoding="utf-8")
SAMPLE_CREATED = "2026-06-15T11:17:26+00:00"
BASE_COUNT = "Verify retrieve agent conversations count"

# Every distinct base scenario name in the sample -> (leaf, is_outline). The two
# `count -- @1.x` rows both resolve to the single outline case `count.feature`.
CASES = [
    ("list", "Verify retrieve agent conversations list", False),
    ("list_noauth", "Verify retrieve agent conversations list without authorization", False),
    ("count", BASE_COUNT, True),
    ("count_noauth", "Verify retrieve agent conversations count without authorization", False),
    ("crud", "Verify CRUD agent conversation", False),
    ("create_empty", "Verify create an agent conversation with empty title", False),
    ("get_missing", "Verify retrieve a non-existent agent conversation", False),
    ("delete_missing", "Verify delete a non-existent agent conversation", False),
]
COUNT_PATH = "Agent/conv/count.feature"

OUTLINE = f"""Feature: count
  Scenario Outline: {BASE_COUNT}
    Given <n> conversations
    Then the count is <n>
  Examples:
    | n |
    | 1 |
    | 2 |
"""


def _seed(app):
    s: Storage = app.extensions["storage"]
    s.create_folder(["Agent"])
    s.create_folder(["Agent", "conv"])
    for leaf, name, is_outline in CASES:
        s.create_file(["Agent", "conv", leaf], scenario_name=name)
        if is_outline:
            s.write_raw(f"Agent/conv/{leaf}.feature", OUTLINE)
    s.create_run_group("Agent", "g")
    return s


import tempfile

with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s = _seed(app)
    c = app.test_client()

    # --- PREVIEW: all matched; per-row counts; outline rows carry examples ---
    r = c.post("/api/runs/import/preview", json={"project": "Agent", "html": SAMPLE})
    assert r.status_code == 200, (r.status_code, r.get_data(as_text=True))
    data = r.get_json()
    assert data["created_at"] == SAMPLE_CREATED, data["created_at"]
    assert data["counts"] == {"total": 9, "matched": 9, "unmatched": 0, "ambiguous": 0}, (
        f"per-row counts must tally 9 rows (not 8 distinct bases): {data['counts']!r}"
    )
    assert data["errors"] == [], data["errors"]
    count_rows = [row for row in data["scenarios"] if row["name"].startswith(BASE_COUNT + " -- @")]
    assert len(count_rows) == 2, f"expected 2 outline rows, got {count_rows!r}"
    assert all(row["match"] == "matched" and row["file_path"] == COUNT_PATH for row in count_rows), count_rows
    assert sorted((row["example"]["table"], row["example"]["row"]) for row in count_rows) == [(1, 1), (1, 2)], (
        f"outline rows must carry {{1,1}}/{{1,2}}: {[row.get('example') for row in count_rows]!r}"
    )
    # A plain row carries no example.
    plain = next(row for row in data["scenarios"] if row["name"] == "Verify CRUD agent conversation")
    assert "example" not in plain, plain
    print("PASS  DO-6 preview: 9/9 matched; outline rows -> one case w/ {1,1}/{1,2}; plain rows bare")

    # --- COMMIT: run written with created_at + 9 results, examples intact ----
    r = c.post("/api/runs/import", json={
        "project": "Agent", "group": "g", "name": "Sample", "file_name": "sample", "html": SAMPLE,
    })
    assert r.status_code == 201, (r.status_code, r.get_data(as_text=True))
    run = s.read_run("Agent", "g", "sample.yaml")
    assert run.created_at == SAMPLE_CREATED, run.created_at
    assert len(run.results) == 9, len(run.results)
    count_results = [(x.result, x.example) for x in run.results if x.file_path == COUNT_PATH]
    assert count_results == [
        ("PASSED", {"table": 1, "row": 1}),
        ("PASSED", {"table": 1, "row": 2}),
    ], f"count case must have two same-path results w/ distinct examples: {count_results!r}"
    assert all(x.example is None for x in run.results if x.file_path != COUNT_PATH), "plain rows keep example=None"
    print("PASS  DO-6 commit: run written w/ sample created_at; outline -> 2 same-path example results")

    # --- EDITOR: /ui/run renders the outline rows with the Examples row ------
    html = c.get("/ui/run/Agent/g/sample.yaml").get_data(as_text=True)

    def cell_for(ex):
        row = re.search(rf'<tr[^>]*data-example="{re.escape(ex)}"[^>]*>(.*?)</tr>', html, re.S)
        assert row, f"row data-example={ex} missing"
        cell = re.search(r'<td class="run-scenario-name[^"]*"[^>]*>(.*?)</td>', row.group(1), re.S)
        return cell.group(1)

    c11 = cell_for("1.1")
    assert BASE_COUNT in c11 and "run-example" in c11 and "| n |" in c11 and "| 1 |" in c11, c11
    c12 = cell_for("1.2")
    assert "| 2 |" in c12 and "| 1 |" not in c12, c12
    # A plain case row has no example block.
    crud_row = re.search(r'<tr[^>]*data-file-path="Agent/conv/crud\.feature"[^>]*>(.*?)</tr>', html, re.S)
    assert crud_row and "data-example" not in crud_row.group(1) and "run-example" not in crud_row.group(1), "plain row must have no example block"
    print("PASS  DO-6 editor: outline rows show base + Examples header + matched data row; plain rows bare")
