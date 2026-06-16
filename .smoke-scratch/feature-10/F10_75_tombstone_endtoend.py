# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / AC5 -- tombstone is render-time, not stored.

AC5: deleting a .feature file whose path appears in a run does NOT
     mutate the run on disk. The next /ui/run render marks the now-
     missing case as tombstoned (run-row-missing, data-missing="1",
     "file has been removed" note, hidden-but-preserved remark textarea).
     Restoring the file at the original path un-tombstones the row on
     the next render and the stored remark reappears.

End-to-end: storage + Flask test client.
"""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_file(["Alpha", "Checkout", "a.feature"], "a desc")
    s.create_run_group("Alpha", "release-1")
    s.create_run(project="Alpha", group="release-1", name="Smoke",
                 file_name="smoke", case_paths=["Alpha/Checkout/a.feature"])
    s.update_run_result("Alpha", "release-1", "smoke.yaml",
                        "Alpha/Checkout/a.feature", remark="keep me")

    yaml_path = root / "Alpha" / "test-run" / "release-1" / "smoke.yaml"
    before = yaml_path.read_bytes()
    client = app.test_client()

    # Baseline render: not tombstoned.
    html0 = client.get("/ui/run/Alpha/release-1/smoke.yaml").get_data(as_text=True)
    assert "run-row-missing" not in html0

    # --- AC5: delete the referenced .feature -> run YAML is UNCHANGED. ---
    s.delete_file("Alpha/Checkout/a.feature")
    assert yaml_path.read_bytes() == before, (
        "deleting a referenced case must NOT mutate the run on disk"
    )

    # --- AC5: next render tombstones the row, remark preserved in DOM. ---
    html1 = client.get("/ui/run/Alpha/release-1/smoke.yaml").get_data(as_text=True)
    assert "run-row-missing" in html1
    assert 'data-missing="1"' in html1
    assert "file has been removed" in html1
    assert ">keep me</textarea>" in html1, "stored remark must stay in the (hidden) textarea"

    # --- AC5: restoring the file un-tombstones on the next render. ---
    s.create_file(["Alpha", "Checkout", "a.feature"], "a desc")
    html2 = client.get("/ui/run/Alpha/release-1/smoke.yaml").get_data(as_text=True)
    assert "run-row-missing" not in html2, "restoring the case must un-tombstone the row"
    assert ">keep me</textarea>" in html2, "remark must survive the round-trip"

print("PASS  AC5: deleting a referenced case leaves the run unchanged + tombstones on render; restore un-tombstones")
