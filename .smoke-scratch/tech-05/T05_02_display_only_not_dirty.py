"""tech-05 RD-3 — scenario name stays out of dirty tracking + the model.

Verifies (spec `specs/tech/05-tech-run-detail-scenario-name-NEW.md`):
  1. The run-editor DOM snapshot (`_readCurrent`) projects ONLY
     {file_path, result, remark} — it never reads the scenario-name cell,
     so the display-only column can never flip the dirty flag.
  2. The persisted run model / JSON API result objects carry exactly
     {file_path, result, remark} — scenario_name is a render-only field
     attached by `ui_run`, never serialised into the run YAML / API.
"""
import re
import tempfile, pathlib
from app import create_app
from app.storage import Storage

# 1) Static JS invariant: _readCurrent reads only file_path/result/remark.
js = pathlib.Path("app/static/06_run_editor.js").read_text()
body = re.search(r"_readCurrent\(\)\s*\{(.*?)\n  \},", js, re.S)
assert body, "could not locate _readCurrent in 06_run_editor.js"
snap = body.group(1)
assert "file_path: tr.dataset.filePath" in snap
assert ".run-result-select" in snap and ".run-remark" in snap
assert "run-scenario-name" not in snap, (
    "_readCurrent must not read the display-only scenario-name cell"
)
print("PASS RD-3 _readCurrent snapshot excludes the scenario-name cell")

# 2) The model / JSON API never carry scenario_name.
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_file(["Alpha", "Checkout", "pay"], scenario_name="User pays with card")
    s.create_run_group("Alpha", "release-1")
    s.create_run(
        project="Alpha", group="release-1", name="Smoke", file_name="smoke",
        case_paths=["Alpha/Checkout/pay.feature"],
    )

    persisted = s.read_run("Alpha", "release-1", "smoke.yaml").to_dict()
    for r in persisted["results"]:
        assert set(r.keys()) == {"file_path", "result", "remark"}, r
    print("PASS RD-3 persisted run model results carry no scenario_name")

    client = app.test_client()
    api = client.get("/api/runs/Alpha/release-1/smoke.yaml").get_json()
    for r in api["results"]:
        assert "scenario_name" not in r, r
    print("PASS RD-3 JSON run API does not leak the render-only scenario_name")
