# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S3 -- PATCH run_paths + immutability.

Asserts:
- PATCH /api/reports/<p>/<f> can add and remove runs (200) and the
  stored run_paths reflect the change.
- created_at is preserved across PATCH.
- A PATCH that changes `type` or sends a differing `created_at` is
  rejected 422 and writes nothing.
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
    s.create_run_group("Alpha", "g")
    for n in ("r1", "r2"):
        s.create_run(project="Alpha", group="g", name=n.upper(), file_name=n, case_paths=[])

    s.create_report("Alpha", "tagr", Report(type="tag_ranking", title="Tag R",
                    status="FAILED", run_paths=["Alpha/test-run/g/r1.yaml"]))
    created = s.read_report("Alpha", "tagr.yaml").created_at

    client = app.test_client()

    # Add r2 (now two runs).
    r = client.patch("/api/reports/Alpha/tagr.yaml", json={
        "type": "tag_ranking", "title": "Tag R", "status": "FAILED",
        "run_paths": ["Alpha/test-run/g/r1.yaml", "Alpha/test-run/g/r2.yaml"],
    })
    assert r.status_code == 200, r.get_data(as_text=True)
    after = s.read_report("Alpha", "tagr.yaml")
    assert after.run_paths == ["Alpha/test-run/g/r1.yaml", "Alpha/test-run/g/r2.yaml"]
    assert after.created_at == created, "created_at must be preserved across PATCH"

    # Remove back to none.
    r = client.patch("/api/reports/Alpha/tagr.yaml", json={
        "type": "tag_ranking", "title": "Tag R", "status": "FAILED", "run_paths": [],
    })
    assert r.status_code == 200, r.get_data(as_text=True)
    assert s.read_report("Alpha", "tagr.yaml").run_paths == []

    # Changing type -> 422.
    r = client.patch("/api/reports/Alpha/tagr.yaml", json={
        "type": "enum_ranking", "title": "Tag R", "status": "FAILED",
        "kind": "components", "run_paths": [],
    })
    assert r.status_code == 422, r.get_data(as_text=True)
    assert r.get_json()["error"]["details"]["field"] == "type"

    # Changing created_at -> 422.
    r = client.patch("/api/reports/Alpha/tagr.yaml", json={
        "type": "tag_ranking", "title": "Tag R", "status": "FAILED",
        "created_at": "1999-01-01T00:00:00+00:00", "run_paths": [],
    })
    assert r.status_code == 422, r.get_data(as_text=True)
    assert r.get_json()["error"]["details"]["field"] == "created_at"

    # The two rejected PATCHes wrote nothing: type + created_at unchanged.
    final = s.read_report("Alpha", "tagr.yaml")
    assert final.type == "tag_ranking" and final.created_at == created

print("PASS  F12_23: PATCH add/remove runs + created_at preserved; type/created_at immutable (422)")
