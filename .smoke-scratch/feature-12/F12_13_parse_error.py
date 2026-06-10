# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S2 -- malformed report -> ReportParseError.

Asserts read_report wraps both malformed YAML and a non-mapping root into
ReportParseError (the uniform 422 envelope), and that list_reports stays
best-effort (lists the broken file with empty fields rather than raising).
"""
import tempfile, pathlib

from app import create_app
from app.storage import Storage
from app.models import Report
from app.errors import ReportParseError


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]

    s.create_folder(["Alpha"])
    # A valid create makes the report/ area exist.
    s.create_run_group("Alpha", "g")
    s.create_run(project="Alpha", group="g", name="r1", file_name="r1", case_paths=[])
    s.create_report("Alpha", "good", Report(type="tag_ranking", title="t", status="FAILED",
                                            run_paths=["Alpha/test-run/g/r1.yaml"]))
    report_dir = root / "Alpha" / "report"

    # 1. Malformed YAML.
    (report_dir / "bad.yaml").write_text("type: tag_ranking\n  : : :\n", encoding="utf-8")
    try:
        s.read_report("Alpha", "bad.yaml")
        raise AssertionError("malformed YAML must raise ReportParseError")
    except ReportParseError:
        pass

    # 2. Non-mapping root (a YAML list).
    (report_dir / "list.yaml").write_text("- a\n- b\n", encoding="utf-8")
    try:
        s.read_report("Alpha", "list.yaml")
        raise AssertionError("non-mapping root must raise ReportParseError")
    except ReportParseError:
        pass

    # 3. list_reports stays best-effort.
    summary = {r["file_name"]: r for r in s.list_reports("Alpha")}
    assert summary["bad.yaml"]["type"] == "" and summary["bad.yaml"]["title"] == "", summary["bad.yaml"]
    assert summary["good.yaml"]["type"] == "tag_ranking", summary["good.yaml"]

print("PASS  F12_13: malformed + non-mapping -> ReportParseError; list_reports best-effort")
