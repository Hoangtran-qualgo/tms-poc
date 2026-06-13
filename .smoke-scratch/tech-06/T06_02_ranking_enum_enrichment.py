"""tech-06 asks 2 & 4 — tag-ranking + tag-inventory per-case gain
scenario name + enums rendered `key : label`.

Verifies (spec `specs/tech/06-tech-report-detail-columns-NEW.md`, RP-2):
  1. tag_ranking per-case entries carry `scenario_name` + an `enums` list
     of `{kind, key, label}`, sorted by kind.
  2. The label is the human `enums.yaml` label (`key : label`).
  3. tag_inventory carrying per-case entries get the same enrichment.
  4. The detail render shows `key : label` for a resolved enum.
  5. Tolerant degrade: when `enums.yaml` is missing/unreadable at report
     time, `_read_vocab` returns {} so the label is blank (key shown alone)
     — no crash. (Stored enums always resolve at write time, so this is the
     only realistic blank-label path.)
"""
import re
import tempfile, pathlib
from app import create_app
from app.storage import Storage
from app.models import Report
from app.reporting import compute_report

ENUMS_YAML = "components:\n  - auth: Authentication\n"


def make(s, path, *, scenario, tags, enums):
    parts = path.split("/")
    s.create_file(parts, scenario_name=scenario)
    f = s.read_feature(path)
    f.tags = list(tags)
    f.enums = dict(enums)
    s.write_feature(path, f)


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    (root / "Alpha" / "enums.yaml").write_text(ENUMS_YAML, encoding="utf-8")
    s.create_folder(["Alpha", "mod"])
    # a.feature: tagged `smoke`, one resolvable enum (components=auth).
    make(s, "Alpha/mod/a.feature", scenario="User signs in",
         tags=["smoke"], enums={"components": "auth"})

    s.create_run_group("Alpha", "g")
    s.create_run(project="Alpha", group="g", name="R1", file_name="r1",
                 case_paths=["Alpha/mod/a.feature"])
    tr = s.read_run("Alpha", "g", "r1.yaml")
    tr.results[0].result = "FAILED"
    s.write_run("Alpha", "g", "r1.yaml", tr)
    run_path = "Alpha/test-run/g/r1.yaml"

    # --- tag_ranking ------------------------------------------------------
    tr_report = Report(type="tag_ranking", title="Tags",
                       created_at="2026-06-13T00:00:00+00:00", status="FAILED",
                       run_paths=[run_path])
    view = compute_report(s, "Alpha", tr_report)
    smoke = next(b for b in view["buckets"] if b["value"] == "smoke")
    case = smoke["cases"][0]
    assert case["file_path"] == "Alpha/mod/a.feature"
    assert case["scenario_name"] == "User signs in", case
    assert case["enums"] == [
        {"kind": "components", "key": "auth", "label": "Authentication"},
    ], case["enums"]
    print("PASS ask2 tag_ranking per-case carries scenario_name + key:label enums")

    # --- tag_inventory ----------------------------------------------------
    inv_report = Report(type="tag_inventory", title="Inv",
                        created_at="2026-06-13T00:00:00+00:00",
                        tag="smoke", scope="Alpha/mod")
    inv = compute_report(s, "Alpha", inv_report)
    carrying = next(b for b in inv["buckets"] if b["value"] == "carrying")
    icase = carrying["cases"][0]
    assert icase["scenario_name"] == "User signs in", icase
    assert {"kind": "components", "key": "auth", "label": "Authentication"} in icase["enums"], icase
    print("PASS ask4 tag_inventory carrying per-case carries scenario_name + key:label enums")

    # --- render -----------------------------------------------------------
    s.create_report("Alpha", "tag", tr_report)
    html = app.test_client().get("/ui/report/Alpha/tag.yaml").get_data(as_text=True)
    assert "User signs in" in html, "scenario name not rendered in per-case row"
    assert re.search(r"auth\s*:\s*Authentication", html), "key : label not rendered"
    print("PASS RP-2 detail render shows `key : label` for a resolved enum")

    # --- 5) tolerant degrade: vocab unreadable at report time -> key only -
    (root / "Alpha" / "enums.yaml").unlink()
    degraded = compute_report(s, "Alpha", tr_report)
    dsmoke = next(b for b in degraded["buckets"] if b["value"] == "smoke")
    assert dsmoke["cases"][0]["enums"] == [
        {"kind": "components", "key": "auth", "label": ""},
    ], dsmoke["cases"][0]["enums"]
    print("PASS RP-2 missing enums.yaml degrades the label to blank (key only), no crash")
