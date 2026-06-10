# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S1 -- validate_report invariants (pure model).

Covers the write-time invariant matrix (no FS): type discriminator,
single-line title/created_at, per-type config requirements, and the
data-source-shape exclusivity rules (run-set vs folder).
"""
from app.models import Report, validate_report
from app.errors import ValidationError


def bad(report, field):
    try:
        validate_report(report)
    except ValidationError as e:
        assert e.field == field, f"expected field {field!r}, got {e.field!r}"
        return
    raise AssertionError(f"expected ValidationError(field={field!r})")


def ok(report):
    validate_report(report)


BASE = dict(title="t", created_at="2026-06-09T00:00:00+00:00")

# -- type discriminator --
bad(Report(type="bogus", **BASE), "type")

# -- title / created_at shape --
bad(Report(type="tag_inventory", title="  ", created_at="x", tag="t", scope="Alpha"), "title")
bad(Report(type="tag_inventory", title="line\n2", created_at="x", tag="t", scope="Alpha"), "title")
bad(Report(type="tag_inventory", title="t", created_at="", tag="t", scope="Alpha"), "created_at")
bad(Report(type="tag_inventory", title="t", created_at="a\nb", tag="t", scope="Alpha"), "created_at")

# -- per-type config --
bad(Report(type="enum_ranking", status="NOPE", kind="components", **BASE), "status")
bad(Report(type="enum_ranking", status="FAILED", kind="", **BASE), "kind")
bad(Report(type="enum_ranking", status="FAILED", kind="1bad", **BASE), "kind")
bad(Report(type="tag_ranking", status="NOPE", **BASE), "status")
bad(Report(type="case_trend", case_path="  ", **BASE), "case_path")
bad(Report(type="tag_inventory", scope="Alpha", tag="", **BASE), "tag")
bad(Report(type="tag_inventory", tag="smoke", scope="", **BASE), "scope")

# -- data-source-shape exclusivity --
bad(Report(type="tag_ranking", status="FAILED", scope="Alpha", **BASE), "scope")
bad(Report(type="tag_ranking", status="FAILED", tag="x", **BASE), "tag")
bad(Report(type="case_trend", case_path="Alpha/a.feature",
           run_paths=[f"Alpha/test-run/g/r{i}.yaml" for i in range(11)], **BASE), "run_paths")
bad(Report(type="case_trend", case_path="Alpha/a.feature",
           run_paths=["Alpha/test-run/g/r1.yaml", "Alpha/test-run/g/r1.yaml"], **BASE), "run_paths[1]")
bad(Report(type="case_trend", case_path="Alpha/a.feature",
           run_paths=[""], **BASE), "run_paths[0]")
bad(Report(type="tag_inventory", tag="smoke", scope="Alpha",
           run_paths=["Alpha/test-run/g/r1.yaml"], **BASE), "run_paths")

# -- valid reports pass --
ok(Report(type="enum_ranking", status="FAILED", kind="components",
          run_paths=["Alpha/test-run/g/r1.yaml"], **BASE))
ok(Report(type="tag_ranking", status="PASSED", run_paths=[], **BASE))  # empty run set legal
ok(Report(type="case_trend", case_path="Alpha/mod/a.feature", **BASE))
ok(Report(type="tag_inventory", tag="smoke", scope="Alpha/mod", **BASE))

print("PASS  F12_06: validate_report type/config/shape invariant matrix")
