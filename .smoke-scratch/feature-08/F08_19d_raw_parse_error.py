# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / AC6 -- raw save of malformed Gherkin -> 422.

End-to-end: PUT /api/files/<p>/raw with malformed Gherkin must return
422 with a `parse_error` envelope carrying `details.line` and
`details.column`. The on-disk file must be UNCHANGED so the user can
retry. The buffer-stays-dirty half is asserted by SR2/SR3 in
F08_14_save_raw_flow.py via the static body inspection (no
markDirty(false) on the non-2xx branch).
"""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "description": "seed"},
    )

    target = root / "Alpha" / "Mod" / "case.feature"
    bytes_before = target.read_bytes()

    r = client.put(
        "/api/files/Alpha/Mod/case.feature/raw",
        data=b"this is not gherkin at all\n",
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    assert r.status_code == 422, (
        f"AC6: malformed Gherkin PUT must return 422; got {r.status_code}"
    )
    env = r.get_json()
    assert env["error"]["code"] == "parse_error", (
        f"AC6: envelope code must be 'parse_error'; got {env['error']['code']!r}"
    )
    details = env["error"].get("details", {})
    assert isinstance(details.get("line"), int) and details["line"] >= 1, (
        f"AC6: parse_error details must carry an integer `line` >= 1; got {details!r}"
    )
    assert isinstance(details.get("column"), int) and details["column"] >= 1, (
        f"AC6: parse_error details must carry an integer `column` >= 1; got {details!r}"
    )
    assert isinstance(env["error"]["message"], str) and env["error"]["message"], (
        f"AC6: envelope must carry a non-empty message; got {env['error']!r}"
    )

    # Disk content must be UNCHANGED (server refused the bad payload).
    bytes_after = target.read_bytes()
    assert bytes_after == bytes_before, (
        f"AC6: 422 parse_error must NOT mutate the on-disk file; "
        f"before={bytes_before!r}, after={bytes_after!r}"
    )

print("PASS  AC6: raw save of malformed Gherkin returns 422 parse_error with line/column details and leaves the on-disk file unchanged")
