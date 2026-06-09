"""Smoke 4: POST /api/runs/<project>/groups auto-creates the test-run/ area.

This is the cold-start path the modal exercises when the user picks
`+ Create new group...` and targets a project with no test-run/ folder
yet. Storage.create_run_group is the only intended writer of the typed
area; the endpoint passes through to it.

Verifies:
- response status is 201;
- the typed-area folder `<project>/test-run/` exists on disk after;
- the new group folder `<project>/test-run/<group>/` exists on disk;
- the group then surfaces in GET /api/run-groups (the same endpoint the
  modal would re-fetch on its next open).
"""
import tempfile, pathlib, json
from app import create_app


def main() -> None:
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "kchatb2b").mkdir()  # bare project, no test-run/
    app = create_app(data_root=d)
    c = app.test_client()

    assert not (d / "kchatb2b" / "test-run").exists(), "precondition: area must be absent"

    r = c.post(
        "/api/runs/kchatb2b/groups",
        data=json.dumps({"name": "smoke"}),
        content_type="application/json",
    )
    assert r.status_code == 201, (r.status_code, r.get_data(as_text=True))
    print("PASS  POST /api/runs/<project>/groups returns 201")

    assert (d / "kchatb2b" / "test-run").is_dir(), "test-run/ area not created"
    print("PASS  test-run/ typed area auto-created on disk")

    assert (d / "kchatb2b" / "test-run" / "smoke").is_dir(), "group folder not created"
    print("PASS  group folder created on disk")

    body = c.get("/api/run-groups").get_json()
    assert {"project": "kchatb2b", "group": "smoke"} in body["groups"], body
    print("PASS  group surfaces in GET /api/run-groups after POST")


if __name__ == "__main__":
    main()
