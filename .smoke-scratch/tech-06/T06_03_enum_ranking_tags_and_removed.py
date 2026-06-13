"""tech-06 ask 3 — enum-ranking per-case gains scenario name + tags;
tombstoned `(removed)` cases enrich to blanks.

Verifies (spec `specs/tech/06-tech-report-detail-columns-NEW.md`):
  1. enum_ranking per-case entries carry `scenario_name` + a sorted `tags`
     list (union of feature + scenario tags).
  2. A case that recorded the status but whose `.feature` was deleted lands
     in the `(removed)` bucket with `scenario_name=""` and `tags=[]` (no
     crash — tolerant enrichment).
  3. The detail render shows the scenario name + the case's tags.
"""
import re
import tempfile, pathlib
from app import create_app
from app.storage import Storage
from app.models import Report
from app.reporting import compute_report

ENUMS_YAML = "components:\n  - auth: Authentication\n"

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    (root / "Alpha" / "enums.yaml").write_text(ENUMS_YAML, encoding="utf-8")
    s.create_folder(["Alpha", "mod"])

    s.create_file(["Alpha", "mod", "a"], scenario_name="User signs in")
    fa = s.read_feature("Alpha/mod/a.feature")
    fa.enums = {"components": "auth"}
    fa.tags = ["regression"]
    fa.scenario.tags = ["smoke"]
    s.write_feature("Alpha/mod/a.feature", fa)

    # b.feature qualifies, then gets deleted -> (removed) bucket.
    s.create_file(["Alpha", "mod", "b"], scenario_name="User signs out")
    fb = s.read_feature("Alpha/mod/b.feature")
    fb.enums = {"components": "auth"}
    s.write_feature("Alpha/mod/b.feature", fb)

    s.create_run_group("Alpha", "g")
    s.create_run(project="Alpha", group="g", name="R1", file_name="r1",
                 case_paths=["Alpha/mod/a.feature", "Alpha/mod/b.feature"])
    tr = s.read_run("Alpha", "g", "r1.yaml")
    for r in tr.results:
        r.result = "FAILED"
    s.write_run("Alpha", "g", "r1.yaml", tr)

    (root / "Alpha" / "mod" / "b.feature").unlink()  # tombstone b

    report = Report(type="enum_ranking", title="Enums",
                    created_at="2026-06-13T00:00:00+00:00", status="FAILED",
                    kind="components", run_paths=["Alpha/test-run/g/r1.yaml"])
    view = compute_report(s, "Alpha", report)

    # 1) auth bucket holds the live case a with scenario name + sorted tags.
    auth = next(b for b in view["buckets"] if b["value"] == "auth")
    acase = auth["cases"][0]
    assert acase["scenario_name"] == "User signs in", acase
    assert acase["tags"] == ["regression", "smoke"], acase["tags"]
    assert "enums" not in acase, "enum_ranking enriches with tags, not enums"
    print("PASS ask3 enum_ranking per-case carries scenario_name + sorted tags")

    # 2) (removed) bucket: tombstoned case enriches to blanks.
    removed = next(b for b in view["buckets"] if b["value"] == "(removed)")
    rcase = removed["cases"][0]
    assert rcase["file_path"] == "Alpha/mod/b.feature"
    assert rcase["scenario_name"] == "" and rcase["tags"] == [], rcase
    print("PASS RP-4 tombstoned (removed) case enriches to blank scenario_name + empty tags")

    # 3) render shows scenario name + tag.
    s.create_report("Alpha", "enum", report)
    html = app.test_client().get("/ui/report/Alpha/enum.yaml").get_data(as_text=True)
    assert "User signs in" in html and "@smoke" in html, html[:500]
    print("PASS ask3 detail render shows the scenario name + the case's tags")
