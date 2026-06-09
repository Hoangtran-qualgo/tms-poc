# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Empty states -- ES2 (project).

Depth 1 with no modules -> "No modules in <project> yet." + `Create module`
CTA.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})  # empty project
    html = client.get("/ui/folder/Alpha").get_data(as_text=True)

# ES2 placeholder text -- project name interpolated.
assert "No modules in" in html and "Alpha" in html and "yet." in html, (
    f"ES2: depth-1 with no modules must render 'No modules in <project> yet.' "
    f"with the project name interpolated; HTML excerpt: {html[800:1100]!r}"
)
# Looser literal check that does not depend on the exact <span> markup
# wrapping the project name.
assert re.search(r"No modules in\s*(?:<[^>]+>)?\s*Alpha", html), (
    "ES2: 'No modules in' must be followed (possibly through a <span>) by the "
    "project name 'Alpha'"
)

# ES2 CTA button labelled "Create module" wired to tmsCreateModule.
cta = re.search(
    r'<button[^>]*onclick="tmsCreateModule\(\'Alpha\'\)"[^>]*>Create module</button>',
    html,
)
assert cta, (
    "ES2: depth-1 empty state must render a `Create module` CTA button wired "
    "to onclick=\"tmsCreateModule('Alpha')\""
)

# No modules table rendered.
assert "<th" not in html or ">Module</th>" not in html, (
    "ES2: depth-1 empty state must NOT render the modules `<th>Module</th>` "
    "table header"
)
print("PASS  ES2: depth-1 empty state shows 'No modules in <project> yet.' + 'Create module' CTA; no modules table")
