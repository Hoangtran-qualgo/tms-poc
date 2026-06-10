# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S3 -- each type renders its detail shape.

Builds one report of every type over a shared fixture (a tagged + enum-
tagged case failing in one run) and asserts each detail HTML carries its
distinctive markers: ranking buckets for enum/tag/inventory, a timeline
table for case_trend.
"""
import tempfile, pathlib

from app import create_app
from app.storage import Storage
from app.models import Report

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
    f.tags = ["smoke"]
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
    s.create_report("Alpha", "tag", Report(type="tag_ranking", title="Tag R",
                    status="FAILED", run_paths=[run_path]))
    s.create_report("Alpha", "trend", Report(type="case_trend", title="Trend R",
                    case_path="Alpha/mod/a.feature", run_paths=[run_path]))
    s.create_report("Alpha", "inv", Report(type="tag_inventory", title="Inv R",
                    tag="smoke", scope="Alpha/mod"))

    client = app.test_client()

    enum_html = client.get("/ui/report/Alpha/enum.yaml").get_data(as_text=True)
    assert "Authentication" in enum_html, "enum_ranking must resolve the label"
    assert "details" in enum_html.lower(), "ranking renders collapsible buckets"

    tag_html = client.get("/ui/report/Alpha/tag.yaml").get_data(as_text=True)
    assert "smoke" in tag_html and "Tag R" in tag_html, tag_html[:400]

    trend_html = client.get("/ui/report/Alpha/trend.yaml").get_data(as_text=True)
    assert "FAILED" in trend_html and ">When<" in trend_html, "trend renders a timeline table"
    assert 'data-status="FAILED"' in trend_html, (
        "trend result cells colour-coded by status via the shared data-status palette"
    )

    inv_html = client.get("/ui/report/Alpha/inv.yaml").get_data(as_text=True)
    assert "carrying" in inv_html and "Inv R" in inv_html, inv_html[:400]

print("PASS  F12_22: enum/tag/inventory render buckets; case_trend renders a timeline")
