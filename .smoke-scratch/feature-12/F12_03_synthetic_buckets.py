# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S1 -- synthetic (unset)/(removed) buckets.

Asserts (spec D11):
- A qualifying case whose enum key is empty/absent buckets into (unset).
- A qualifying case whose .feature is now missing/unparseable buckets
  into (removed).
- Both are flagged synthetic (muted) and pinned after the real buckets
  so the bucket counts reconcile against total.
"""
import tempfile, pathlib

from app import create_app
from app.storage import Storage
from app.models import Report
from app.reporting import compute_report

ENUMS_YAML = "components:\n  - auth: Authentication\n"


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
    make_feature(s, "Alpha/mod/b.feature", "")    # unset
    make_feature(s, "Alpha/mod/c.feature", "auth")  # will be removed

    cases = [f"Alpha/mod/{n}.feature" for n in ("a", "b", "c")]
    s.create_run_group("Alpha", "g")
    s.create_run(project="Alpha", group="g", name="r1", file_name="r1", case_paths=cases)
    tr = s.read_run("Alpha", "g", "r1.yaml")
    for r in tr.results:
        r.result = "FAILED"
    s.write_run("Alpha", "g", "r1.yaml", tr)

    # Tombstone c: delete the .feature while the run still references it.
    (root / "Alpha" / "mod" / "c.feature").unlink()

    report = Report(type="enum_ranking", title="r", created_at="2026-06-09T00:00:00+00:00",
                    status="FAILED", kind="components",
                    run_paths=["Alpha/test-run/g/r1.yaml"])

    view = compute_report(s, "Alpha", report)
    assert view["total"] == 3, view["total"]
    rows = [(b["value"], b["synthetic"], b["count"]) for b in view["buckets"]]
    assert rows == [
        ("auth", False, 1),
        ("(unset)", True, 1),
        ("(removed)", True, 1),
    ], rows
    # counts reconcile with the distinct total.
    assert sum(b["count"] for b in view["buckets"]) == view["total"]

print("PASS  F12_03: (unset)+(removed) synthetic buckets pinned last + reconcile")
