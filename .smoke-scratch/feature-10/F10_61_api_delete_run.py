# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / AP5 -- DELETE /api/runs/<p>/<g>/<file>.

AP5: deletes a run, returning 204; idempotent -- deleting an
     already-absent run returns 204 again (no 404).
"""
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
                 file_name="smoke", case_paths=[])
    yaml_path = root / "Alpha" / "test-run" / "release-1" / "smoke.yaml"
    assert yaml_path.is_file()

    client = app.test_client()

    # --- AP5: delete -> 204, file gone. ---
    r = client.delete("/api/runs/Alpha/release-1/smoke.yaml")
    assert r.status_code == 204, (r.status_code, r.get_data(as_text=True))
    assert not yaml_path.exists()

    # --- AP5: idempotent -> 204 again. ---
    r2 = client.delete("/api/runs/Alpha/release-1/smoke.yaml")
    assert r2.status_code == 204, (r2.status_code, r2.get_data(as_text=True))

print("PASS  AP5: DELETE run returns 204 and is idempotent on an already-absent run")
