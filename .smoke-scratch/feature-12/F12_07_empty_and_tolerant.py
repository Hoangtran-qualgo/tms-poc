# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S1 -- empty + render-time tolerance.

Asserts (spec D11 + D13): aggregation never raises on degenerate inputs.
- An empty run set yields total 0 with no buckets and no warnings.
- A missing / malformed run path degrades into a warning, not a crash.
- A tag_inventory over a non-existent scope folder yields total 0 plus a
  warning rather than a FileNotFoundError.
"""
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

    # 1. Empty run set -> clean zero state.
    empty = Report(type="enum_ranking", title="t", created_at="2026-06-09T00:00:00+00:00",
                   status="FAILED", kind="components", run_paths=[])
    v1 = compute_report(s, "Alpha", empty)
    assert v1["total"] == 0 and v1["buckets"] == [] and v1["warnings"] == [], v1

    # 2. Missing + malformed run paths -> warnings, no crash.
    broken = Report(type="tag_ranking", title="t", created_at="2026-06-09T00:00:00+00:00",
                    status="FAILED",
                    run_paths=["Alpha/test-run/g/missing.yaml", "not/a/run/path/x"])
    v2 = compute_report(s, "Alpha", broken)
    assert v2["total"] == 0 and v2["buckets"] == [], v2
    assert len(v2["warnings"]) == 2, v2["warnings"]

    # 3. tag_inventory over a non-existent scope -> tolerant warning.
    ghost = Report(type="tag_inventory", title="t", created_at="2026-06-09T00:00:00+00:00",
                   tag="smoke", scope="Alpha/ghost")
    v3 = compute_report(s, "Alpha", ghost)
    assert v3["total"] == 0 and v3["warnings"], v3

print("PASS  F12_07: empty run set + missing/malformed run paths + missing scope tolerated")
