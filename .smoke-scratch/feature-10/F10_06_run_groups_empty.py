"""Smoke 3a: GET /api/run-groups on an empty data root.

Verifies the endpoint returns the documented zero shape so the modal's
zero-projects branch can render its "No projects yet" message.
"""
import tempfile, pathlib
from app import create_app


def main() -> None:
    d = pathlib.Path(tempfile.mkdtemp())
    app = create_app(data_root=d)
    c = app.test_client()

    r = c.get("/api/run-groups")
    assert r.status_code == 200, r.status_code
    body = r.get_json()
    assert body == {"projects": [], "groups": []}, body
    print("PASS  empty root -> projects=[], groups=[]")


if __name__ == "__main__":
    main()
