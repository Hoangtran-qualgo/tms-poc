"""Smoke 6: POST /api/runs twice with same slugged file_name → 409.

Run name uniqueness within run group is enforced by Storage.create_run
raising NameConflictError when the target .yaml file already exists.
The modal's submit handler surfaces this as an inline error under the
run-name input.

Verifies two paths:
- exact-duplicate `name`: second POST returns 409;
- slug-collision: two distinct names that slugify to the same
  `file_name` also collide on the server (e.g. "My Run" and "my-run")
  even though the human-readable names differ.
"""
import tempfile, pathlib, json, re
from app import create_app


def _post_run(c, project, group, name, file_name):
    return c.post(
        "/api/runs",
        data=json.dumps({
            "project": project,
            "group": group,
            "name": name,
            "file_name": file_name,
            "case_paths": [],
            "description": "",
        }),
        content_type="application/json",
    )


def main() -> None:
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "alpha" / "test-run" / "smoke").mkdir(parents=True)
    app = create_app(data_root=d)
    c = app.test_client()

    # First create succeeds.
    r1 = _post_run(c, "alpha", "smoke", "My Run", "my-run")
    assert r1.status_code == 201, (r1.status_code, r1.get_data(as_text=True))
    print("PASS  first POST /api/runs returns 201")

    # Exact-duplicate file_name + name → 409.
    r2 = _post_run(c, "alpha", "smoke", "My Run", "my-run")
    assert r2.status_code == 409, (r2.status_code, r2.get_data(as_text=True))
    msg2 = (r2.get_json() or {}).get("error", {}).get("message", "")
    assert re.search(r"already exists", msg2, re.I), msg2
    print("PASS  exact-duplicate POST returns 409 with 'already exists'")

    # Slug-collision: distinct human name that the client would slugify
    # to the same file_name. The modal sends `file_name` directly
    # (already slugified), so this exercises the server's last-line
    # defence rather than the client's pre-check.
    r3 = _post_run(c, "alpha", "smoke", "my run", "my-run")
    assert r3.status_code == 409, (r3.status_code, r3.get_data(as_text=True))
    print("PASS  slug-collision POST returns 409 (server enforces uniqueness)")

    # Only one run file lives on disk.
    files = sorted(p.name for p in (d / "alpha" / "test-run" / "smoke").iterdir())
    assert files == ["my-run.yaml"], files
    print("PASS  exactly one run file exists on disk after collision attempts")


if __name__ == "__main__":
    main()
