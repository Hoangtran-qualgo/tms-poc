# Pattern: see .smoke-scratch/README.md
"""tech-02 / E4 / report detail: shared palette + emphasised key factors.

specs/tech/02 § E4: report detail reuses the SAME single-source status palette
as E3 (no inline colour map), bold-emphasises the key factors (status / kind /
case / run-count / tag / scope), and palette-colours the enum-ranking `status`
filter via data-status.

Asserts:
1. The inline result_colors Jinja map is gone from report_detail.html, and no
   inline Tailwind status-colour classes remain on the trend cell.
2. The case_trend Result cell colours via data-status (shared palette).
3. The enum_ranking `status` param is palette-coloured via data-status.
4. Key factors are bold-emphasised (font-semibold) in the rendered header.
"""
import tempfile, pathlib

from app import create_app
from app.storage import Storage
from app.models import Report

REPO = pathlib.Path(__file__).resolve().parents[2]

# 1. Static: the inline colour map is deleted (palette is the only source).
report_tpl = (REPO / "app" / "templates" / "report_detail.html").read_text(encoding="utf-8")
assert "result_colors" not in report_tpl, "E4: inline result_colors map must be removed"
for cls in ("text-emerald-600", "text-rose-600", "text-sky-600", "text-amber-600"):
    assert cls not in report_tpl, f"E4: inline status colour {cls!r} must be removed"

ENUMS_YAML = "components:\n  - auth: Authentication\n"

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]

    s.create_folder(["Alpha"])
    (root / "Alpha" / "enums.yaml").write_text(ENUMS_YAML, encoding="utf-8")
    s.create_folder(["Alpha", "mod"])
    s.create_file(["Alpha", "mod", "a.feature"], "desc")
    f = s.read_feature("Alpha/mod/a.feature")
    f.enums = {"components": "auth"}
    s.write_feature("Alpha/mod/a.feature", f)

    s.create_run_group("Alpha", "g")
    s.create_run(project="Alpha", group="g", name="R1", file_name="r1",
                 case_paths=["Alpha/mod/a.feature"])
    tr = s.read_run("Alpha", "g", "r1.yaml")
    tr.results[0].result = "FAILED"
    s.write_run("Alpha", "g", "r1.yaml", tr)
    run_path = "Alpha/test-run/g/r1.yaml"

    s.create_report("Alpha", "enum", Report(type="enum_ranking", title="Enum R",
                    status="FAILED", kind="components", run_paths=[run_path]))
    s.create_report("Alpha", "trend", Report(type="case_trend", title="Trend R",
                    case_path="Alpha/mod/a.feature", run_paths=[run_path]))

    client = app.test_client()
    enum_html = client.get("/ui/report/Alpha/enum.yaml").get_data(as_text=True)
    trend_html = client.get("/ui/report/Alpha/trend.yaml").get_data(as_text=True)

# 2. case_trend Result cell colours via data-status.
assert 'data-status="FAILED"' in trend_html, "E4: trend cell must colour via data-status"

# 3. enum_ranking status param palette-coloured via data-status.
assert 'data-status="FAILED"' in enum_html, (
    "E4: enum_ranking status param must be palette-coloured via data-status"
)

# 4. Key factors are bold-emphasised.
assert "font-semibold" in enum_html, "E4: key factors must be bold-emphasised"

print("PASS  T02_04: report detail uses shared palette + emphasises key factors")
