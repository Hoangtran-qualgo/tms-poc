# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S3 -- /ui/reports-tree aggregation.

Asserts the Reports sidebar partial lists every project's reports as
leaves that link to /ui/report/<project>/<file>, with the report title
shown. Empty state when no reports exist.
"""
import tempfile, pathlib

from app import create_app
from app.storage import Storage
from app.models import Report


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    client = app.test_client()

    # Empty state first.
    html = client.get("/ui/reports-tree").get_data(as_text=True)
    assert "No reports yet" in html, html

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "mod"])
    s.create_report("Alpha", "smoke-cov", Report(
        type="tag_inventory", title="Smoke coverage", tag="smoke", scope="Alpha/mod"))

    html = client.get("/ui/reports-tree").get_data(as_text=True)
    assert "Alpha" in html, html
    assert "Smoke coverage" in html, html
    assert "/ui/report/Alpha/smoke-cov.yaml" in html, html

print("PASS  F12_21: /ui/reports-tree lists report leaves + links + empty state")
