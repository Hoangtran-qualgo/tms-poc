# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / AP2 -- GET /api/runs/<project>/<group>.

AP2: lists run summaries for a group under a `{"runs": [...]}` envelope;
     each entry is a list_runs() summary dict.
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
    s.create_run(project="Alpha", group="release-1", name="Sprint 1",
                 file_name="sprint-1", case_paths=["Alpha/m/a.feature"])
    s.create_run(project="Alpha", group="release-1", name="Sprint 2",
                 file_name="sprint-2", case_paths=[])

    client = app.test_client()
    r = client.get("/api/runs/Alpha/release-1")
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert set(body) == {"runs"}, body
    by_name = {x["file_name"]: x for x in body["runs"]}
    assert set(by_name) == {"sprint-1.yaml", "sprint-2.yaml"}, by_name
    assert by_name["sprint-1.yaml"]["case_count"] == 1
    assert set(by_name["sprint-1.yaml"]) == {
        "file_name", "name", "created_at", "case_count", "results_count_by_status"}

    # Empty / unknown group -> empty list (no error).
    assert client.get("/api/runs/Alpha/nope").get_json() == {"runs": []}

print("PASS  AP2: GET /api/runs/<p>/<g> returns the {runs:[...]} summary envelope")
