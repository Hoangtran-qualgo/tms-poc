# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Empty states -- ES1 (root).

Depth 0 with no projects -> "No projects yet." + central `Create project`
CTA.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    html = app.test_client().get("/ui/folder/").get_data(as_text=True)

# ES1 placeholder text.
assert "No projects yet." in html, (
    "ES1: depth-0 with no projects must render the literal 'No projects yet.' "
    "placeholder text"
)

# ES1 central CTA button labelled "Create project" wired to the same JS helper.
cta = re.search(
    r'<button[^>]*onclick="tmsCreateProject\(\)"[^>]*>Create project</button>',
    html,
)
assert cta, (
    "ES1: depth-0 empty state must render a central `Create project` CTA "
    "button wired to onclick=\"tmsCreateProject()\""
)

# No table rendered when the projects list is empty.
assert "<table" not in html, (
    "ES1: depth-0 empty state must NOT render any <table> elements "
    "(the projects table is conditional on `{% if projects %}`)"
)
print("PASS  ES1: depth-0 empty state shows 'No projects yet.' + central 'Create project' CTA; no tables")
