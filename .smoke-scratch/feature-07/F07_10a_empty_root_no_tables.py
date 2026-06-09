# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Acceptance criteria -- AC1.

Visiting `/ui/folder/` with no projects renders an empty-state CTA and
NO tables.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    html = app.test_client().get("/ui/folder/").get_data(as_text=True)

assert "No projects yet." in html, (
    "AC1: GET /ui/folder/ on empty FS must render the 'No projects yet.' "
    "placeholder"
)
assert re.search(
    r'<button[^>]*onclick="tmsCreateProject\(\)"[^>]*>Create project</button>',
    html,
), (
    "AC1: GET /ui/folder/ on empty FS must render a `Create project` CTA "
    "button wired to onclick=\"tmsCreateProject()\""
)
assert "<table" not in html, (
    "AC1: GET /ui/folder/ on empty FS must NOT render any <table> elements "
    "(the projects table is conditional on `{% if projects %}`)"
)
print("PASS  AC1: empty FS -> 'No projects yet.' + 'Create project' CTA; no tables")
