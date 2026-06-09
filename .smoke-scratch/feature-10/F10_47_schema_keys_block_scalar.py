# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / SC1 + SC2 -- on-disk schema shape.

SC1: top-level keys are emitted in the stable order
     name -> created_at -> description -> results (sort_keys=False).
SC2: a multi-line `remark` round-trips with its newlines intact.

DRIFT (SC2 encoding): the spec's on-disk example shows `remark: |`
block scalars, but the actual serializer (`yaml.safe_dump` with
default settings, no custom representer) encodes a multi-line string
as a *single-quoted* multi-line scalar, NOT a `|` block scalar. The
load-bearing invariant -- newlines survive the round-trip -- holds
either way; the `|` rendering is cosmetic and does not match the
as-shipped bytes. This smoke pins the real behaviour (preservation)
and asserts the on-disk form is NOT a literal block scalar so the
drift is caught if the encoding ever changes.

Inspects the raw on-disk YAML bytes after a PATCH that sets a
multi-line remark.
"""
import json
import re
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_run_group("Alpha", "release-1")
    s.create_run(project="Alpha", group="release-1", name="Smoke",
                 file_name="smoke", case_paths=["Alpha/m/a.feature"])
    created_at = s.read_run("Alpha", "release-1", "smoke.yaml").created_at

    client = app.test_client()
    multiline = "line one\nline two\n"
    r = client.patch("/api/runs/Alpha/release-1/smoke.yaml", data=json.dumps({
        "name": "Smoke", "created_at": created_at, "description": "desc",
        "results": [{"file_path": "Alpha/m/a.feature", "result": "FAILED",
                     "remark": multiline}],
    }), content_type="application/json")
    assert r.status_code == 200, r.get_data(as_text=True)

    text = (root / "Alpha" / "test-run" / "release-1" / "smoke.yaml").read_text()

    # --- SC1: stable top-level key order. ---
    order = [m.group(1) for m in re.finditer(r"(?m)^(name|created_at|description|results):", text)]
    assert order == ["name", "created_at", "description", "results"], order

    # --- SC2 DRIFT: the as-shipped encoding is NOT a `|` block scalar. ---
    assert not re.search(r"remark:\s*\|", text), (
        "DRIFT regression: the serializer now emits a block scalar; the spec "
        "example finally matches the bytes -- update this smoke + COVERAGE."
    )

    # --- SC2: the load-bearing invariant -- newlines survive the round-trip. ---
    assert s.read_run("Alpha", "release-1", "smoke.yaml").results[0].remark == multiline, (
        "multi-line remark must round-trip with newlines intact"
    )

print("PASS  SC1+SC2: stable key order; multi-line remark round-trips with newlines (as single-quoted scalar, NOT `|` block -- drift pinned)")
