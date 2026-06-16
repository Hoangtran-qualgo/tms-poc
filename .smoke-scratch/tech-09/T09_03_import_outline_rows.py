# Pattern: see .smoke-scratch/README.md
"""tech-09 / Scenario-Outline in test runs / DO-3 import resolver + route.

HTTP smoke over POST /api/runs/import/preview and POST /api/runs/import:
- O1 (preview): an outline's two report rows (`-- @1.1`/`-- @1.2`) BOTH match
  the single case (distinct, not ambiguous, not collapsed). Per-row counts:
  matched counts ROWS (3), not distinct base names (2). Each outline row
  carries its `example` {table,row}; the plain row has none.
- O2 (commit): the run is written with two results on the SAME path with
  distinct examples (no duplicate-path rejection), plus the plain result.
- O3 (unmatched suffixed): a suffixed row whose base resolves to no case is an
  error keyed on the FULL suffixed name; commit aborts all-or-nothing (422).
"""
import base64
import json
import pathlib
import tempfile

from app import create_app

BASE = "Verify retrieve agent conversations count"


def _d(path, obj):
    b64 = base64.b64encode(json.dumps(obj).encode("utf-8")).decode("ascii")
    return f"d('{path}','{b64}')"


def _html(leaves, start_ms=1700000000000):
    suites = {"name": "suites", "children": leaves}
    summary = {"reportName": "R", "time": {"start": start_ms, "stop": start_ms + 1}}
    return (
        "<html><script>Promise.allSettled(["
        + _d("data/suites.json", suites) + ","
        + _d("widgets/summary.json", summary)
        + "])</script></html>"
    )


def _leaf(name, status):
    return {"name": name, "status": status, "time": {"start": 1, "stop": 2}}


def _seed(app):
    s = app.extensions["storage"]
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])
    s.create_file(["proj", "mod", "login.feature"], scenario_name="Login")
    s.create_file(["proj", "mod", "count.feature"], scenario_name=BASE)
    s.create_run_group("proj", "grp")
    return s


# Real Allure renders example rows with a TRAILING space after the suffix.
OUTLINE = _html([
    _leaf("Login", "passed"),
    _leaf(f"{BASE} -- @1.1 ", "passed"),
    _leaf(f"{BASE} -- @1.2 ", "failed"),
])
COUNT_PATH = "proj/mod/count.feature"


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    _seed(app)
    c = app.test_client()

    # --- O1: preview ------------------------------------------------------
    r = c.post("/api/runs/import/preview", json={"project": "proj", "html": OUTLINE})
    assert r.status_code == 200, f"O1: status {r.status_code}: {r.get_json()}"
    data = r.get_json()
    # Per-row counts: the two outline rows each count as a matched ROW (3),
    # NOT the 2 distinct base names the resolver dict would report.
    assert data["counts"] == {"total": 3, "matched": 3, "unmatched": 0, "ambiguous": 0}, (
        f"O1: per-row counts wrong: {data['counts']!r}"
    )
    assert data["errors"] == [], f"O1: errors {data['errors']!r}"
    rows = data["scenarios"]
    # Plain row: matched, no example key.
    assert rows[0]["match"] == "matched" and "example" not in rows[0], f"O1: plain row {rows[0]!r}"
    # Both outline rows: matched to the SAME path, distinct examples.
    outline_rows = rows[1:]
    assert all(row["match"] == "matched" and row["file_path"] == COUNT_PATH
               for row in outline_rows), f"O1: outline rows {outline_rows!r}"
    assert [row["example"] for row in outline_rows] == [
        {"table": 1, "row": 1}, {"table": 1, "row": 2},
    ], f"O1: examples {[r.get('example') for r in outline_rows]!r}"
    print("PASS  O1: preview keeps outline rows distinct; per-row counts; examples attached")

    # --- O2: commit -------------------------------------------------------
    r = c.post("/api/runs/import", json={
        "project": "proj", "group": "grp", "name": "Imp", "file_name": "imp", "html": OUTLINE,
    })
    assert r.status_code == 201, f"O2: status {r.status_code}: {r.get_json()}"
    s = app.extensions["storage"]
    run = s.read_run("proj", "grp", "imp")
    got = [(x.file_path, x.result, x.example) for x in run.results]
    assert got == [
        ("proj/mod/login.feature", "PASSED", None),
        (COUNT_PATH, "PASSED", {"table": 1, "row": 1}),
        (COUNT_PATH, "FAILED", {"table": 1, "row": 2}),
    ], f"O2: results {got!r}"
    print("PASS  O2: commit writes two same-path results with distinct examples + plain row")


# --- O3: unmatched suffixed row aborts, error keyed on suffixed name --------
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    _seed(app)
    c = app.test_client()
    GHOST = _html([_leaf("Ghost scenario -- @1.1 ", "passed")])

    r = c.post("/api/runs/import/preview", json={"project": "proj", "html": GHOST})
    data = r.get_json()
    assert data["counts"] == {"total": 1, "matched": 0, "unmatched": 1, "ambiguous": 0}, (
        f"O3: counts {data['counts']!r}"
    )
    # Error line must carry the FULL suffixed name so the user sees what failed.
    assert "Ghost scenario -- @1.1" in data["errors"][0], f"O3: error line {data['errors']!r}"

    r = c.post("/api/runs/import", json={
        "project": "proj", "group": "grp", "name": "G", "file_name": "g", "html": GHOST,
    })
    assert r.status_code == 422, f"O3: commit status {r.status_code}"
    err = r.get_json()["error"]
    assert err["code"] == "import_validation_error", f"O3: {err!r}"
    assert "Ghost scenario -- @1.1" in err["details"]["reasons"][0], f"O3: reasons {err!r}"
    assert "g.yaml" not in [x["file_name"] for x in app.extensions["storage"].list_runs("proj", "grp")], (
        "O3: nothing written on abort"
    )
    print("PASS  O3: unmatched suffixed row -> error keyed on full name; commit aborts 422")
