# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S3 -- /api/runs/<project> + scope PATCH.

Asserts:
- GET /api/runs/<project> returns a flat {runs:[...]} envelope across all
  groups, each entry carrying the data-root-relative run `path` the run
  picker feeds into a report's run_paths.
- A tag_inventory report's `scope` is editable via PATCH (the detail
  view's "Edit scope" action), re-validated + cross-checked server-side.
"""
import tempfile, pathlib

from app import create_app
from app.storage import Storage
from app.models import Report


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "mod"])
    s.create_folder(["Alpha", "other"])
    s.create_run_group("Alpha", "g1")
    s.create_run_group("Alpha", "g2")
    s.create_run(project="Alpha", group="g1", name="R1", file_name="r1", case_paths=[])
    s.create_run(project="Alpha", group="g2", name="R2", file_name="r2", case_paths=[])

    client = app.test_client()

    # /api/runs/<project> aggregates across groups.
    r = client.get("/api/runs/Alpha")
    assert r.status_code == 200, r.get_data(as_text=True)
    runs = r.get_json()["runs"]
    paths = {x["path"] for x in runs}
    assert paths == {"Alpha/test-run/g1/r1.yaml", "Alpha/test-run/g2/r2.yaml"}, paths
    assert set(runs[0]) == {"path", "group", "file_name", "name", "created_at"}
    # Unknown project -> empty list, not an error.
    assert client.get("/api/runs/Nope").get_json() == {"runs": []}

    # Scope is editable via PATCH (whole-doc).
    s.create_report("Alpha", "inv", Report(
        type="tag_inventory", title="Inv", tag="smoke", scope="Alpha/mod"))
    doc = client.get("/api/reports/Alpha/inv.yaml").get_json()
    doc["scope"] = "Alpha/other"
    r = client.patch("/api/reports/Alpha/inv.yaml", json=doc)
    assert r.status_code == 200, r.get_data(as_text=True)
    assert s.read_report("Alpha", "inv.yaml").scope == "Alpha/other"

    # A non-existent scope is rejected (cross-check) and writes nothing.
    doc["scope"] = "Alpha/ghost"
    r = client.patch("/api/reports/Alpha/inv.yaml", json=doc)
    assert r.status_code == 422, r.get_data(as_text=True)
    assert s.read_report("Alpha", "inv.yaml").scope == "Alpha/other"

print("PASS  F12_25: /api/runs/<project> flat envelope + tag_inventory scope PATCH + cross-check")
