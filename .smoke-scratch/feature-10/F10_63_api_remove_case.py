# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / AP7 + SM10 -- DELETE .../cases/<path>.

AP7/SM10: DELETE /api/runs/<p>/<g>/<file>/cases/<case_path> removes the
     matching RunResult and returns 204; idempotent -- removing a case
     that is not in the run still returns 204 and leaves the run
     unchanged. The case_path captures embedded slashes via the
     <path:> converter.
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
                 file_name="smoke",
                 case_paths=["Alpha/m/a.feature", "Alpha/m/b.feature"])

    client = app.test_client()
    base = "/api/runs/Alpha/release-1/smoke.yaml/cases"

    # --- AP7 + SM10: remove an existing case -> 204, gone from results. ---
    r = client.delete(f"{base}/Alpha/m/a.feature")
    assert r.status_code == 204, (r.status_code, r.get_data(as_text=True))
    remaining = [x.file_path for x in s.read_run("Alpha", "release-1", "smoke.yaml").results]
    assert remaining == ["Alpha/m/b.feature"], remaining

    # --- SM10: removing an absent case is idempotent -> 204, unchanged. ---
    r2 = client.delete(f"{base}/Alpha/m/ghost.feature")
    assert r2.status_code == 204, (r2.status_code, r2.get_data(as_text=True))
    assert [x.file_path for x in s.read_run("Alpha", "release-1", "smoke.yaml").results] == [
        "Alpha/m/b.feature"]

print("PASS  AP7+SM10: DELETE case returns 204, removes the row, idempotent on absent case")
