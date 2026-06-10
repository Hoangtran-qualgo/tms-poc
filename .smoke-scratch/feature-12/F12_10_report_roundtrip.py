# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S2 -- report persistence round-trip.

Asserts:
- create_report stamps created_at server-side and persists ONLY the
  keys relevant to the report type (no dead scope/tag/case_path keys).
- read -> write (the PATCH path) is byte-stable (canonical YAML).
"""
import tempfile, pathlib

from app import create_app
from app.storage import Storage
from app.models import Report


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]

    s.create_folder(["Alpha"])  # also writes the default enums.yaml (components)
    s.create_run_group("Alpha", "g")
    s.create_run(project="Alpha", group="g", name="r1", file_name="r1", case_paths=[])
    run_path = "Alpha/test-run/g/r1.yaml"

    rep = Report(type="enum_ranking", title="Most-failed components",
                 status="FAILED", kind="components", run_paths=[run_path])
    s.create_report("Alpha", "comp-fail", rep)

    stored = s.read_report("Alpha", "comp-fail.yaml")
    assert stored.created_at, "created_at must be stamped on create"
    assert stored.type == "enum_ranking" and stored.kind == "components"

    raw1 = s.read_raw(["Alpha", "report", "comp-fail.yaml"])
    # Only type-relevant keys persisted.
    for dead in ("scope:", "tag:", "case_path:"):
        assert dead not in raw1, f"{dead!r} should not be persisted for enum_ranking\n{raw1}"
    for live in ("type:", "title:", "created_at:", "status:", "kind:", "run_paths:"):
        assert live in raw1, f"{live!r} missing\n{raw1}"

    # PATCH path: read -> write -> byte-stable.
    s.write_report("Alpha", "comp-fail.yaml", stored)
    raw2 = s.read_raw(["Alpha", "report", "comp-fail.yaml"])
    assert raw1 == raw2, f"round-trip not byte-stable:\n--- {raw1}\n+++ {raw2}"

print("PASS  F12_10: create stamps created_at + type-only keys + byte-stable round-trip")
