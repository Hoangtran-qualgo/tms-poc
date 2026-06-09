"""3.D — Save (PATCH) round-trip + canonical YAML idempotence.

This is the back half of smoke 3.b from the spec: the client-side dirty
flow is verified manually in the browser; this script asserts the
server contract the Save handler depends on:

  1. PATCH /api/runs/<project>/<group>/<file_name> with whole-doc body
     persists every field (name, description, per-row result + remark).
  2. GET (UI) reflects the change.
  3. PATCH-ing the exact same payload a second time leaves the file
     byte-identical (canonical YAML; required so 'Save twice in a row'
     doesn't churn the disk).
"""
import json
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_run_group("Alpha", "release-1")
    s.create_run(
        project="Alpha", group="release-1", name="Smoke",
        file_name="smoke",
        case_paths=["Alpha/Checkout/a.feature", "Alpha/Checkout/b.feature"],
        description="initial",
    )

    yaml_path = root / "Alpha" / "test-run" / "release-1" / "smoke.yaml"
    assert yaml_path.is_file()

    # Read the freshly-created file to get created_at (immutable across edits).
    initial = s.read_run("Alpha", "release-1", "smoke.yaml").to_dict()
    created_at = initial["created_at"]

    # Build the PATCH payload as the Save handler does.
    payload = {
        "name": "Smoke A (renamed)",
        "created_at": created_at,
        "description": "after first save",
        "results": [
            {"file_path": "Alpha/Checkout/a.feature", "result": "PASSED", "remark": "green"},
            {"file_path": "Alpha/Checkout/b.feature", "result": "FAILED", "remark": "boom"},
        ],
    }

    client = app.test_client()
    r = client.patch(
        "/api/runs/Alpha/release-1/smoke.yaml",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert r.status_code == 200, r.get_data(as_text=True)

    # GET via UI reflects the change.
    html = client.get("/ui/run/Alpha/release-1/smoke.yaml").get_data(as_text=True)
    assert 'value="Smoke A (renamed)"' in html
    assert "after first save" in html
    # Per-row results: PASSED + FAILED are pre-selected in their selects.
    assert '<option value="PASSED" selected>' in html
    assert '<option value="FAILED" selected>' in html
    # Remarks rendered inside textareas.
    assert ">green</textarea>" in html
    assert ">boom</textarea>" in html
    print("PASS 3.D PATCH persisted name + description + results")

    # Canonical idempotence: PATCH the exact same payload again, expect
    # the bytes on disk to be unchanged.
    bytes_after_first = yaml_path.read_bytes()
    r2 = client.patch(
        "/api/runs/Alpha/release-1/smoke.yaml",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert r2.status_code == 200, r2.get_data(as_text=True)
    bytes_after_second = yaml_path.read_bytes()
    assert bytes_after_first == bytes_after_second, (
        "YAML must be byte-identical on consecutive saves of the same data"
    )
    print("PASS 3.D second save with same payload is byte-identical")
