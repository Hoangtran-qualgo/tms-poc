# Pattern: see .smoke-scratch/README.md
"""feature-14 / import test cases / Phase 3 API (preview + commit endpoints).

HTTP smoke over POST /api/files/import/preview and POST /api/files/import:
preview metadata + enums_present, preview parse error (line/col), preview
zero scenarios, > 3 MB rejection on both, commit happy path (created paths +
files on disk), names-length mismatch, project/parent mismatch, in-scope
conflict abort (collect-all reasons), and no-scenario content error.
"""
import pathlib
import tempfile

from app import create_app

GOOD = (
    "@feat\n"
    "Feature: shared\n\n"
    "  @a\n  Scenario: alpha\n    Given a1\n\n"
    "  @b\n  Scenario: beta\n    Given b1\n"
)


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s = app.extensions["storage"]
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])
    c = app.test_client()

    # --- P1: preview returns per-scenario metadata + shared header --------
    r = c.post("/api/files/import/preview", json={"source": GOOD})
    assert r.status_code == 200, f"P1: status {r.status_code}: {r.get_json()}"
    data = r.get_json()
    assert data["description"] == "shared", f"P1: desc {data!r}"
    assert data["tags"] == ["feat"], f"P1: feature tags {data!r}"
    assert data["enums_present"] is False, f"P1: enums_present {data!r}"
    assert [x["scenario_name"] for x in data["scenarios"]] == ["alpha", "beta"], f"P1: {data!r}"
    assert data["scenarios"][0]["step_count"] == 1, f"P1: step_count {data!r}"
    assert data["scenarios"][0]["scenario_tags"] == ["a"], f"P1: scenario tags {data!r}"
    print("PASS  P1: preview returns shared header + per-scenario metadata in order")

    # --- P2: enums_present true when directives present -------------------
    r = c.post(
        "/api/files/import/preview",
        json={"source": "# enum.priority: high\n" + GOOD},
    )
    assert r.get_json()["enums_present"] is True, "P2: enums_present must be True"
    print("PASS  P2: preview flags enums_present when directives are present")

    # --- P3: preview parse error (Rule) -> 422 parse_error with loc -------
    r = c.post(
        "/api/files/import/preview",
        json={"source": "Feature: f\n\n  Rule: r\n    Scenario: y\n    Given x\n"},
    )
    assert r.status_code == 422, f"P3: status {r.status_code}"
    err = r.get_json()["error"]
    assert err["code"] == "parse_error", f"P3: code {err!r}"
    assert "line" in err["details"] and "column" in err["details"], f"P3: loc {err!r}"
    print("PASS  P3: preview parse error returns 422 parse_error with line/column")

    # --- P4: preview zero scenarios -> 200 with empty list ----------------
    r = c.post("/api/files/import/preview", json={"source": "Feature: solo\n"})
    assert r.status_code == 200 and r.get_json()["scenarios"] == [], "P4: zero scenarios"
    print("PASS  P4: preview with zero scenarios returns empty scenario list")

    # --- P5: > 3 MB rejected (preview) ------------------------------------
    big = "#" * (3 * 1024 * 1024 + 1)
    r = c.post("/api/files/import/preview", json={"source": big})
    assert r.status_code == 400, f"P5: status {r.status_code}"
    assert "MB limit" in r.get_json()["error"]["message"], f"P5: {r.get_json()!r}"
    print("PASS  P5: preview rejects source > 3 MB with 400")


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s = app.extensions["storage"]
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])
    c = app.test_client()

    # --- C1: commit happy path -------------------------------------------
    r = c.post(
        "/api/files/import",
        json={"parent": "proj/mod", "source": GOOD, "names": ["alpha", "beta"]},
    )
    assert r.status_code == 201, f"C1: status {r.status_code}: {r.get_json()}"
    assert r.get_json()["created"] == ["proj/mod/alpha.feature", "proj/mod/beta.feature"], (
        f"C1: created {r.get_json()!r}"
    )
    assert s.read_feature(["proj", "mod", "alpha.feature"]).scenario.name == "alpha", "C1: file on disk"
    print("PASS  C1: commit writes one file per scenario and returns created paths")

    # --- C2: names-length mismatch -> 400 ---------------------------------
    r = c.post("/api/files/import", json={"parent": "proj/mod", "source": GOOD, "names": ["only"]})
    assert r.status_code == 400 and "match" in r.get_json()["error"]["message"], f"C2: {r.get_json()!r}"
    print("PASS  C2: commit rejects names/scenarios length mismatch with 400")

    # --- C3: project/parent mismatch -> 400 -------------------------------
    r = c.post(
        "/api/files/import",
        json={"project": "other", "parent": "proj/mod", "source": GOOD, "names": ["x", "y"]},
    )
    assert r.status_code == 400 and "must match" in r.get_json()["error"]["message"], f"C3: {r.get_json()!r}"
    print("PASS  C3: commit rejects project not matching parent's first segment")

    # --- C4: in-scope conflict abort (collect-all) ------------------------
    # alpha.feature + scenario 'alpha' already exist from C1.
    r = c.post(
        "/api/files/import",
        json={"parent": "proj/mod", "source": GOOD, "names": ["alpha", "beta"]},
    )
    assert r.status_code == 422, f"C4: status {r.status_code}"
    err = r.get_json()["error"]
    assert err["code"] == "import_validation_error", f"C4: code {err!r}"
    assert len(err["details"]["reasons"]) >= 1, f"C4: reasons {err!r}"
    print("PASS  C4: commit in-scope conflict returns 422 import_validation_error with reasons")

    # --- C5: no scenarios -> 422 import_validation_error ------------------
    r = c.post("/api/files/import", json={"parent": "proj/mod", "source": "Feature: solo\n", "names": []})
    assert r.status_code == 422, f"C5: status {r.status_code}"
    assert r.get_json()["error"]["code"] == "import_validation_error", f"C5: {r.get_json()!r}"
    print("PASS  C5: commit with no scenarios returns 422 import_validation_error")

    # --- C6: > 3 MB rejected (commit) -------------------------------------
    big = "#" * (3 * 1024 * 1024 + 1)
    r = c.post("/api/files/import", json={"parent": "proj/mod", "source": big, "names": []})
    assert r.status_code == 400 and "MB limit" in r.get_json()["error"]["message"], f"C6: {r.get_json()!r}"
    print("PASS  C6: commit rejects source > 3 MB with 400")
