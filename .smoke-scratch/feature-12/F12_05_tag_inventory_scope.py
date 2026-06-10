# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S1 -- tag_inventory folder survey.

Asserts (spec tag_inventory aggregation):
- Every .feature under the folder scope is surveyed live (NOT via runs).
- Cases split into a carrying bucket and a not-carrying bucket;
  total = readable cases, pct reconciles to 1.0.
- The union of feature-level and scenario-level tags decides membership.
"""
import tempfile, pathlib
from math import isclose

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

    make_feature(s, "Alpha/mod/a.feature", tags=["smoke"])
    make_feature(s, "Alpha/mod/b.feature", scenario_tags=["smoke"])  # scenario-level
    make_feature(s, "Alpha/mod/c.feature", tags=["regression"])
    make_feature(s, "Alpha/mod/d.feature")
    make_feature(s, "Alpha/mod/e.feature", tags=["wip"])

    report = Report(type="tag_inventory", title="smoke coverage",
                    created_at="2026-06-09T00:00:00+00:00",
                    tag="smoke", scope="Alpha/mod")

    view = compute_report(s, "Alpha", report)
    assert view["total"] == 5, view["total"]
    carrying, not_carrying = view["buckets"]
    assert carrying["value"] == "carrying" and carrying["count"] == 2, carrying
    assert not_carrying["value"] == "not_carrying" and not_carrying["count"] == 3, not_carrying
    assert isclose(carrying["pct"], 0.4) and isclose(not_carrying["pct"], 0.6), view["buckets"]
    # scenario-level tag counts toward membership.
    carried_paths = {c["file_path"] for c in carrying["cases"]}
    assert carried_paths == {"Alpha/mod/a.feature", "Alpha/mod/b.feature"}, carried_paths
    assert not view["warnings"], view["warnings"]

print("PASS  F12_05: tag_inventory carrying/not-carrying split + scope survey")
