"""Smoke 3b: GET /api/run-groups lists projects that have no test-run/.

A project should appear in ``projects`` even when its ``test-run/``
folder does not exist yet. This is the cold-start path: the modal's
"Create new group..." sub-select must be able to target such projects
so the area can be lazy-created on the first POST.
"""
import tempfile, pathlib
from app import create_app


def main() -> None:
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "kchatb2b").mkdir()
    app = create_app(data_root=d)
    c = app.test_client()

    body = c.get("/api/run-groups").get_json()
    assert body["projects"] == ["kchatb2b"], body["projects"]
    assert body["groups"] == [], body["groups"]
    print("PASS  project without test-run/ listed; groups=[]")


if __name__ == "__main__":
    main()
