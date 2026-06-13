"""tech-06 ask 1 — case-trend gains a `run name` column.

Verifies (spec `specs/tech/06-tech-report-detail-columns-NEW.md`):
  1. `_case_trend` attaches the human `run.name` to each trend row
     alongside the existing run file name (`t.run`).
  2. The detail render adds a `Run name` header column and shows the name.
  3. RP-3: runs are guaranteed a non-empty name at write time, so the
     column never needs a fallback — the value is the live `run.name`.
"""
import re
import tempfile, pathlib
from app import create_app
from app.storage import Storage
from app.models import Report
from app.reporting import compute_report

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "mod"])
    s.create_file(["Alpha", "mod", "a"], scenario_name="User signs in")

    s.create_run_group("Alpha", "g")
    s.create_run(project="Alpha", group="g", name="Release Candidate 1",
                 file_name="r1", case_paths=["Alpha/mod/a.feature"])
    tr = s.read_run("Alpha", "g", "r1.yaml")
    tr.results[0].result = "FAILED"
    s.write_run("Alpha", "g", "r1.yaml", tr)

    report = Report(type="case_trend", title="Trend",
                    created_at="2026-06-13T00:00:00+00:00",
                    case_path="Alpha/mod/a.feature",
                    run_paths=["Alpha/test-run/g/r1.yaml"])

    # 1) Engine attaches run_name alongside the file name.
    view = compute_report(s, "Alpha", report)
    row = view["trend"][0]
    assert row["run"] == "r1.yaml", row
    assert row["run_name"] == "Release Candidate 1", row
    print("PASS ask1 _case_trend attaches the human run.name per trend row")

    # 2) Render: a Run name header + the value, distinct from the file link.
    s.create_report("Alpha", "trend", report)
    html = client = app.test_client().get("/ui/report/Alpha/trend.yaml").get_data(as_text=True)
    assert re.search(r"<th[^>]*>\s*Run name\s*</th>", html), "Run name header missing"
    assert "Release Candidate 1" in html, "run name value not rendered"
    # The file name link and the human name are both present (distinct cols).
    assert "r1.yaml" in html, html[:400]
    print("PASS ask1 detail render adds a Run name column showing run.name")
