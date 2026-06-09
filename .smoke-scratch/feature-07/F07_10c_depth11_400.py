# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Acceptance criteria -- AC3.

Visiting `/ui/folder/<path>` at depth 11 returns a 400 inline error
snippet (handled by the UI blueprint's ValueError handler).
"""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    # Build the deepest legal path (depth 10), then probe one segment deeper.
    chain = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
    for i in range(1, len(chain) + 1):
        client.post(
            "/api/folders",
            json={"parent": "/".join(chain[: i - 1]), "name": chain[i - 1]},
        )
    deep_path = "/".join(chain) + "/extra11"
    r = client.get(f"/ui/folder/{deep_path}")
    assert r.status_code == 400, (
        f"AC3: GET /ui/folder/<11 segments> must return 400, got {r.status_code}"
    )
    # Inline error snippet -- HTML body with some failure description.
    body = r.get_data(as_text=True)
    assert body, (
        "AC3: 400 response must carry a non-empty inline error snippet body "
        "(handled by the UI blueprint's ValueError handler)"
    )
print("PASS  AC3: GET /ui/folder/<11 segments> -> 400 + inline error snippet body")
