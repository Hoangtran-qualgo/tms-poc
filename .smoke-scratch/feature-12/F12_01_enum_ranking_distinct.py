# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S1 -- enum_ranking distinct-case counting.

Asserts (spec D7 + enum_ranking aggregation):
- A case that hit the chosen status in >=1 run is counted exactly ONCE,
  even if it failed in multiple runs (distinct-case unit).
- Cases bucket by their live Feature.enums[kind]; labels resolve from
  the project's enums.yaml; pct = count / total_distinct.
- Buckets sort by count DESC then label ASC.
"""
import tempfile, pathlib
from math import isclose

from app import create_app
from app.storage import Storage
from app.models import Report
from app.reporting import compute_report

ENUMS_YAML = (
    "components:\n"
    "  - auth: Authentication\n"
    "  - billing: Billing\n"
)


def make_feature(s, path, component):
    parts = path.split("/")
    s.create_file(parts, "desc")
    f = s.read_feature(path)
    if component:
        f.enums = {"components": component}
    s.write_feature(path, f)


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]

    s.create_folder(["Alpha"])
    (root / "Alpha" / "enums.yaml").write_text(ENUMS_YAML, encoding="utf-8")
    s.create_folder(["Alpha", "mod"])

    make_feature(s, "Alpha/mod/a.feature", "auth")
    make_feature(s, "Alpha/mod/e.feature", "auth")
    make_feature(s, "Alpha/mod/c.feature", "billing")
    make_feature(s, "Alpha/mod/d.feature", "")  # unset

    cases = [f"Alpha/mod/{n}.feature" for n in ("a", "e", "c", "d")]
    s.create_run_group("Alpha", "g")

    def run(name, **results):
        s.create_run(project="Alpha", group="g", name=name,
                     file_name=name, case_paths=cases)
        tr = s.read_run("Alpha", "g", f"{name}.yaml")
        for r in tr.results:
            r.result = results.get(r.file_path, "PENDING")
        s.write_run("Alpha", "g", f"{name}.yaml", tr)

    run("r1", **{"Alpha/mod/a.feature": "FAILED", "Alpha/mod/e.feature": "FAILED",
                 "Alpha/mod/c.feature": "PASSED", "Alpha/mod/d.feature": "FAILED"})
    run("r2", **{"Alpha/mod/a.feature": "FAILED", "Alpha/mod/c.feature": "FAILED"})

    report = Report(type="enum_ranking", title="Most-failed components",
                    created_at="2026-06-09T00:00:00+00:00", status="FAILED",
                    kind="components",
                    run_paths=["Alpha/test-run/g/r1.yaml", "Alpha/test-run/g/r2.yaml"])

    view = compute_report(s, "Alpha", report)

    # a failed in r1 AND r2 -> counted once; qualifying = {a,e,c,d} = 4.
    assert view["total"] == 4, view["total"]
    rows = [(b["value"], b["label"], b["count"], b["synthetic"]) for b in view["buckets"]]
    assert rows == [
        ("auth", "Authentication", 2, False),
        ("billing", "Billing", 1, False),
        ("(unset)", "(unset)", 1, True),
    ], rows
    assert isclose(view["buckets"][0]["pct"], 0.5), view["buckets"][0]["pct"]
    assert not view["warnings"], view["warnings"]

print("PASS  F12_01: enum_ranking distinct-case counting + label + pct + order")
