# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S1 -- case_trend ordering, absence, tombstone.

Asserts (spec case_trend aggregation):
- The trend walks runs in created_at ASC order regardless of run_paths order.
- A run that does NOT include the case shows the absent placeholder "-".
- tombstoned flips True once the case .feature is gone; trend results
  still come from the historical run records.
"""
import tempfile, pathlib

from app import create_app
from app.storage import Storage
from app.models import Report
from app.reporting import compute_report

TARGET = "Alpha/mod/a.feature"


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "mod"])
    for n in ("a", "b"):
        s.create_file(["Alpha", "mod", f"{n}.feature"], "desc")

    s.create_run_group("Alpha", "g")

    def run(name, created_at, cases, results):
        s.create_run(project="Alpha", group="g", name=name, file_name=name,
                     case_paths=cases)
        tr = s.read_run("Alpha", "g", f"{name}.yaml")
        tr.created_at = created_at
        for r in tr.results:
            r.result = results.get(r.file_path, "PENDING")
        s.write_run("Alpha", "g", f"{name}.yaml", tr)

    run("r1", "2026-01-01T00:00:00+00:00", [TARGET], {TARGET: "PASSED"})
    run("r2", "2026-02-01T00:00:00+00:00", [TARGET], {TARGET: "FAILED"})
    run("r3", "2026-03-01T00:00:00+00:00", ["Alpha/mod/b.feature"], {})  # a absent

    # run_paths deliberately out of chronological order.
    report = Report(type="case_trend", title="trend", created_at="2026-06-09T00:00:00+00:00",
                    case_path=TARGET,
                    run_paths=["Alpha/test-run/g/r3.yaml",
                               "Alpha/test-run/g/r1.yaml",
                               "Alpha/test-run/g/r2.yaml"])

    view = compute_report(s, "Alpha", report)
    assert view["total"] == 3, view["total"]
    seq = [(t["run"], t["result"]) for t in view["trend"]]
    assert seq == [("r1.yaml", "PASSED"), ("r2.yaml", "FAILED"), ("r3.yaml", "\u2014")], seq
    assert view["tombstoned"] is False, view["tombstoned"]

    # Remove the case -> tombstoned True, but historical results persist.
    (root / "Alpha" / "mod" / "a.feature").unlink()
    view2 = compute_report(s, "Alpha", report)
    assert view2["tombstoned"] is True, view2["tombstoned"]
    assert [t["result"] for t in view2["trend"]] == ["PASSED", "FAILED", "\u2014"]
    assert view2["current_tags"] == []

print("PASS  F12_04: case_trend created_at order + absent '-' + tombstone")
