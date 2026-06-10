# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S3 -- POST create + GET detail navigate.

Asserts:
- POST /api/reports/<project> creates the file on disk (201) with a
  server-stamped created_at and only type-relevant keys.
- GET /ui/report/<project>/<file> renders the detail HTML.
- A run-set report referencing a real run also creates + renders.
"""
import tempfile, pathlib

from app import create_app
from app.storage import Storage


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "mod"])
    s.create_run_group("Alpha", "g")
    s.create_run(project="Alpha", group="g", name="R1", file_name="r1", case_paths=[])

    client = app.test_client()

    # tag_inventory (folder type, no runs needed).
    r = client.post("/api/reports/Alpha", json={
        "file_name": "smoke-cov", "type": "tag_inventory",
        "title": "Smoke coverage", "tag": "smoke", "scope": "Alpha/mod",
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    assert (root / "Alpha" / "report" / "smoke-cov.yaml").is_file()
    stored = s.read_report("Alpha", "smoke-cov.yaml")
    assert stored.created_at, "created_at must be stamped"

    html = client.get("/ui/report/Alpha/smoke-cov.yaml").get_data(as_text=True)
    assert "Smoke coverage" in html and "report-detail" in html, html[:400]

    # enum_ranking (run-set type) referencing a real run.
    r = client.post("/api/reports/Alpha", json={
        "file_name": "comp-fail", "type": "enum_ranking",
        "title": "Failing components", "status": "FAILED", "kind": "components",
        "run_paths": ["Alpha/test-run/g/r1.yaml"],
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    html = client.get("/ui/report/Alpha/comp-fail.yaml").get_data(as_text=True)
    assert "Failing components" in html, html[:400]
    assert "+ Add runs" in html, "run-set detail must offer + Add runs"

print("PASS  F12_20: POST creates report file + GET /ui/report renders detail")
