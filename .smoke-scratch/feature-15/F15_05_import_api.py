# Pattern: see .smoke-scratch/README.md
"""feature-15 / import test run / DO-4 API (preview + commit endpoints).

HTTP smoke over POST /api/runs/import/preview and POST /api/runs/import:
- P1: preview all-matched -> 200, report name + summary-derived created_at,
  per-scenario rows (match + file_path), counts, empty errors.
- P2: preview with unmatched + ambiguous -> match flags, counts, per-line errors.
- P3: preview malformed report -> 400 bad_request.
- P4: preview report > 30 MB -> 400.
- C1: commit all-matched -> 201, run written with report created_at + one
  result per scenario; RETENTION: no .html persisted anywhere under data root.
- C2: commit with non-matched scenarios -> 422 import_validation_error +
  reasons, nothing written.
- C3: commit with zero scenarios -> 422.
- C4: commit report > 30 MB -> 400.
"""
import base64
import json
import pathlib
import tempfile
from datetime import datetime, timezone

from app import create_app


def _html(leaves, start_ms=1700000000000, report_name="My Report"):
    suites = {"name": "suites", "children": leaves}
    summary = {"reportName": report_name, "time": {"start": start_ms, "stop": start_ms + 1}}

    def _d(path, obj):
        b64 = base64.b64encode(json.dumps(obj).encode("utf-8")).decode("ascii")
        return f"d('{path}','{b64}')"

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
    s.create_folder(["proj", "mod2"])
    s.create_file(["proj", "mod", "login.feature"], scenario_name="Login")
    s.create_file(["proj", "mod", "logout.feature"], scenario_name="Logout")
    # Same scenario name in two folders -> ambiguous at project scope.
    s.create_file(["proj", "mod", "dup_a.feature"], scenario_name="Dup")
    s.create_file(["proj", "mod2", "dup_b.feature"], scenario_name="Dup")
    s.create_run_group("proj", "grp")
    return s


EXPECTED_CREATED = datetime.fromtimestamp(
    1700000000000 / 1000, tz=timezone.utc
).isoformat(timespec="seconds")

GOOD = _html([_leaf("Login", "passed"), _leaf("Logout", "failed")])
BAD = _html([_leaf("Login", "passed"), _leaf("Ghost", "skipped"), _leaf("Dup", "passed")])


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    _seed(app)
    c = app.test_client()

    # --- P1: preview all matched -----------------------------------------
    r = c.post("/api/runs/import/preview", json={"project": "proj", "html": GOOD})
    assert r.status_code == 200, f"P1: status {r.status_code}: {r.get_json()}"
    data = r.get_json()
    assert data["report_name"] == "My Report", f"P1: report_name {data!r}"
    assert data["created_at"] == EXPECTED_CREATED, f"P1: created_at {data!r}"
    assert data["counts"] == {"total": 2, "matched": 2, "unmatched": 0, "ambiguous": 0}, (
        f"P1: counts {data['counts']!r}"
    )
    assert data["errors"] == [], f"P1: errors {data['errors']!r}"
    rows = data["scenarios"]
    assert rows[0] == {"no": 1, "name": "Login", "result": "PASSED",
                       "match": "matched", "file_path": "proj/mod/login.feature"}, f"P1: {rows!r}"
    assert rows[1]["result"] == "FAILED" and rows[1]["file_path"] == "proj/mod/logout.feature", f"P1: {rows!r}"
    print("PASS  P1: preview all-matched returns name, created_at, rows, counts, no errors")

    # --- P2: preview with unmatched + ambiguous --------------------------
    r = c.post("/api/runs/import/preview", json={"project": "proj", "html": BAD})
    assert r.status_code == 200, f"P2: status {r.status_code}"
    data = r.get_json()
    assert data["counts"] == {"total": 3, "matched": 1, "unmatched": 1, "ambiguous": 1}, (
        f"P2: counts {data['counts']!r}"
    )
    by_name = {row["name"]: row for row in data["scenarios"]}
    assert by_name["Login"]["match"] == "matched", f"P2: {by_name!r}"
    assert by_name["Ghost"]["match"] == "unmatched" and "file_path" not in by_name["Ghost"], f"P2: {by_name!r}"
    assert by_name["Dup"]["match"] == "ambiguous" and "file_path" not in by_name["Dup"], f"P2: {by_name!r}"
    joined = " || ".join(data["errors"])
    assert "Ghost : cannot import - no case" in joined, f"P2: unmatched line {data['errors']!r}"
    assert "Dup : cannot import - multiple cases" in joined, f"P2: ambiguous line {data['errors']!r}"
    assert len(data["errors"]) == 2, f"P2: one error per non-matched, got {data['errors']!r}"
    print("PASS  P2: preview flags unmatched/ambiguous with counts + per-line errors")

    # --- P3: malformed report -> 400 -------------------------------------
    r = c.post("/api/runs/import/preview", json={"project": "proj", "html": "<html>nope</html>"})
    assert r.status_code == 400, f"P3: status {r.status_code}"
    assert r.get_json()["error"]["code"] == "bad_request", f"P3: {r.get_json()!r}"
    print("PASS  P3: preview of a non-Allure report returns 400 bad_request")

    # --- P4: > 30 MB -> 400 ----------------------------------------------
    big = "#" * (30 * 1024 * 1024 + 1)
    r = c.post("/api/runs/import/preview", json={"project": "proj", "html": big})
    assert r.status_code == 400 and "MB limit" in r.get_json()["error"]["message"], f"P4: {r.get_json()!r}"
    print("PASS  P4: preview rejects report > 30 MB with 400")


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s = _seed(app)
    c = app.test_client()

    # --- C1: commit happy path + retention -------------------------------
    r = c.post("/api/runs/import", json={
        "project": "proj", "group": "grp", "name": "Imported", "file_name": "imported",
        "description": "from report", "html": GOOD,
    })
    assert r.status_code == 201, f"C1: status {r.status_code}: {r.get_json()}"
    run = s.read_run("proj", "grp", "imported")
    assert run.name == "Imported" and run.description == "from report", f"C1: meta {run!r}"
    assert run.created_at == EXPECTED_CREATED, f"C1: created_at {run.created_at!r}"
    assert [(x.file_path, x.result) for x in run.results] == [
        ("proj/mod/login.feature", "PASSED"),
        ("proj/mod/logout.feature", "FAILED"),
    ], f"C1: results {[(x.file_path, x.result) for x in run.results]!r}"
    # RETENTION: the uploaded HTML must not be persisted anywhere under data root.
    assert list(pathlib.Path(td).rglob("*.html")) == [], "C1: no .html may be written under the project"
    assert (pathlib.Path(td) / "proj" / "test-run" / "grp" / "imported.yaml").is_file(), "C1: run .yaml written"
    print("PASS  C1: commit writes run with report created_at + results; no .html retained")

    # --- C2: non-matched scenarios -> 422, nothing written ---------------
    r = c.post("/api/runs/import", json={
        "project": "proj", "group": "grp", "name": "Bad", "file_name": "badrun", "html": BAD,
    })
    assert r.status_code == 422, f"C2: status {r.status_code}"
    err = r.get_json()["error"]
    assert err["code"] == "import_validation_error", f"C2: code {err!r}"
    assert len(err["details"]["reasons"]) == 2, f"C2: reasons {err!r}"
    names = [run["file_name"] for run in s.list_runs("proj", "grp")]
    assert "badrun.yaml" not in names, f"C2: nothing written, got {names!r}"
    print("PASS  C2: commit with unmatched/ambiguous returns 422 + reasons, nothing written")

    # --- C3: zero scenarios -> 422 ---------------------------------------
    empty = _html([])
    r = c.post("/api/runs/import", json={
        "project": "proj", "group": "grp", "name": "Empty", "file_name": "empty", "html": empty,
    })
    assert r.status_code == 422, f"C3: status {r.status_code}"
    assert r.get_json()["error"]["code"] == "import_validation_error", f"C3: {r.get_json()!r}"
    print("PASS  C3: commit with zero scenarios returns 422 import_validation_error")

    # --- C4: > 30 MB -> 400 ----------------------------------------------
    big = "#" * (30 * 1024 * 1024 + 1)
    r = c.post("/api/runs/import", json={
        "project": "proj", "group": "grp", "name": "Big", "file_name": "big", "html": big,
    })
    assert r.status_code == 400 and "MB limit" in r.get_json()["error"]["message"], f"C4: {r.get_json()!r}"
    print("PASS  C4: commit rejects report > 30 MB with 400")
