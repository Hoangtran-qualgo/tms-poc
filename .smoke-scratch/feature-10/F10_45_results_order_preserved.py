# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / DM2 -- results insertion order is canonical.

DM2: `results` is a list whose insertion order is the canonical on-disk
     order; storage never reshuffles it. Creation order is preserved on
     read, and a whole-doc PATCH that reorders the rows persists the new
     order verbatim (no sorting / normalisation).

Exercised through create_run + PATCH /api/runs/... .
"""
import json
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_run_group("Alpha", "release-1")
    s.create_run(project="Alpha", group="release-1", name="Smoke",
                 file_name="smoke",
                 case_paths=["Alpha/m/c.feature", "Alpha/m/a.feature",
                             "Alpha/m/b.feature"])

    # --- DM2: creation order preserved on read (NOT alphabetised). ---
    got = [r.file_path for r in s.read_run("Alpha", "release-1", "smoke.yaml").results]
    assert got == ["Alpha/m/c.feature", "Alpha/m/a.feature", "Alpha/m/b.feature"], got

    # --- DM2: a reordering PATCH persists the new order verbatim. ---
    created_at = s.read_run("Alpha", "release-1", "smoke.yaml").created_at
    reordered = ["Alpha/m/b.feature", "Alpha/m/c.feature", "Alpha/m/a.feature"]
    client = app.test_client()
    r = client.patch(
        "/api/runs/Alpha/release-1/smoke.yaml",
        data=json.dumps({"name": "Smoke", "created_at": created_at, "description": "",
                         "results": [{"file_path": p, "result": "PENDING", "remark": ""}
                                     for p in reordered]}),
        content_type="application/json",
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    got2 = [r.file_path for r in s.read_run("Alpha", "release-1", "smoke.yaml").results]
    assert got2 == reordered, f"reordered results must persist verbatim, got {got2}"

print("PASS  DM2: results preserve insertion order on create and verbatim across a reordering PATCH")
