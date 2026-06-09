# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Acceptance criteria -- AC2.

Visiting `/ui/folder/<existing path>` at any depth 0..10 must render
without error (200 status, HTML body).
"""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    chain = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
    for i in range(1, len(chain) + 1):
        client.post(
            "/api/folders",
            json={"parent": "/".join(chain[: i - 1]), "name": chain[i - 1]},
        )

    # Depth 0 + depths 1..10.
    paths = [""] + ["/".join(chain[:d]) for d in range(1, 11)]
    for path in paths:
        url = f"/ui/folder/{path}" if path else "/ui/folder/"
        r = client.get(url)
        assert r.status_code == 200, (
            f"AC2 (depth {len(path.split('/')) if path else 0}, url {url!r}): "
            f"existing-path GET must return 200, got {r.status_code} "
            f"body={r.get_data(as_text=True)[:120]!r}"
        )
        assert r.mimetype == "text/html", (
            f"AC2 (url {url!r}): must return HTML, got mimetype {r.mimetype!r}"
        )
print("PASS  AC2: GET /ui/folder/<existing path> renders 200 at every depth 0..10")
