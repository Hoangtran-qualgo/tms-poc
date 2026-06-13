# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S1 -- tag_ranking multi-valued buckets.

Asserts (spec D10 + tag_ranking aggregation):
- A case increments EVERY tag bucket it carries (union of feature-level
  and scenario-level tags), so bucket counts can sum to > total_distinct.
- A case with no tags lands in the muted (untagged) bucket.
- total_distinct is still the distinct qualifying-case count.
"""
import tempfile, pathlib

from app import create_app
from app.storage import Storage
from app.models import Report
from app.reporting import compute_report


def make_feature(s, path, *, tags=(), scenario_tags=()):
    parts = path.split("/")
    s.create_file(parts, "desc")
    f = s.read_feature(path)
    f.tags = list(tags)
    f.scenario.tags = list(scenario_tags)
    s.write_feature(path, f)


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "mod"])

    make_feature(s, "Alpha/mod/a.feature", tags=["smoke", "regression"], scenario_tags=["auth"])
    make_feature(s, "Alpha/mod/b.feature", tags=["smoke"])
    make_feature(s, "Alpha/mod/c.feature")  # untagged

    cases = [f"Alpha/mod/{n}.feature" for n in ("a", "b", "c")]
    s.create_run_group("Alpha", "g")
    s.create_run(project="Alpha", group="g", name="r1", file_name="r1", case_paths=cases)
    tr = s.read_run("Alpha", "g", "r1.yaml")
    for r in tr.results:
        r.result = "FAILED"
    s.write_run("Alpha", "g", "r1.yaml", tr)

    report = Report(type="tag_ranking", title="Most-failed tags",
                    created_at="2026-06-09T00:00:00+00:00", status="FAILED",
                    run_paths=["Alpha/test-run/g/r1.yaml"])

    view = compute_report(s, "Alpha", report)

    assert view["total"] == 3, view["total"]
    counts = {b["value"]: b["count"] for b in view["buckets"]}
    assert counts == {"smoke": 2, "regression": 1, "auth": 1, "(untagged)": 1}, counts

    # multi-valued: real-tag counts sum to more than the distinct total.
    real_sum = sum(b["count"] for b in view["buckets"] if not b["synthetic"])
    assert real_sum == 4 > view["total"], real_sum

    # smoke ranks first (highest count); (untagged) is muted + pinned last.
    assert view["buckets"][0]["value"] == "smoke", view["buckets"]
    # tech-06: per-case entries now also carry scenario_name + enums (an
    # untagged case has no enums here, so enums == []).
    assert view["buckets"][-1] == {
        "value": "(untagged)", "label": "(untagged)", "synthetic": True,
        "count": 1, "pct": view["buckets"][-1]["pct"],
        "cases": [{"file_path": "Alpha/mod/c.feature", "scenario_name": "", "enums": []}],
    }, view["buckets"][-1]

print("PASS  F12_02: tag_ranking multi-valued buckets + untagged + >100% sum")
