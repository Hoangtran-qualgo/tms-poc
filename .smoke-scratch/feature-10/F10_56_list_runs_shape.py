# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / SM4 -- list_runs entry shape + resilience.

SM4: list_runs(project, group) returns one dict per .yaml in the group
     with shape {file_name, name, created_at, case_count,
     results_count_by_status}. Files that fail to parse are still
     listed, as zero-count entries (no exception), so the UI can
     surface them for repair.
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
                 file_name="sprint-1",
                 case_paths=["Alpha/m/a.feature", "Alpha/m/b.feature"])
    s.update_run_result("Alpha", "release-1", "sprint-1.yaml",
                        "Alpha/m/a.feature", result="PASSED")

    # A malformed sibling .yaml must not break the listing.
    (root / "Alpha" / "test-run" / "release-1" / "broken.yaml").write_text(
        ":\n  bad: : :\n", encoding="utf-8")

    runs = {r["file_name"]: r for r in s.list_runs("Alpha", "release-1")}

    # --- SM4: parseable entry carries the full shape. ---
    good = runs["sprint-1.yaml"]
    assert set(good) == {"file_name", "name", "created_at", "case_count",
                         "results_count_by_status"}, good
    assert good["name"] == "Sprint 1"
    assert good["case_count"] == 2
    assert good["results_count_by_status"] == {"PASSED": 1, "PENDING": 1}, good

    # --- SM4: unreadable entry is listed as a zero-count stub, no raise. ---
    bad = runs["broken.yaml"]
    assert bad["name"] == "" and bad["case_count"] == 0, bad
    assert bad["results_count_by_status"] == {}, bad

print("PASS  SM4: list_runs returns full per-run shape; unreadable runs surface as zero-count stubs")
