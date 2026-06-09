# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Empty states -- ES3 (module + sub-folder).

Depth 2 / 3+ with no folders AND no features -> "No test cases in <name>
yet." + CTA. The sub-folder empty state hosts both `+ Sub-folder` and
`+ Test case` CTAs side-by-side.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})  # empty module
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod2"})
    client.post("/api/folders", json={"parent": "Alpha/Mod2", "name": "Sub"})  # empty sub

    # --- ES3 module branch (depth 2): empty -> 'No test cases in Mod yet.'
    html = client.get("/ui/folder/Alpha/Mod").get_data(as_text=True)
    assert re.search(r"No test cases in\s*(?:<[^>]+>)?\s*Mod", html), (
        f"ES3 (module branch): empty depth-2 view must render 'No test cases "
        f"in <module> yet.' with the module name 'Mod' interpolated; "
        f"HTML excerpt: {html[800:1200]!r}"
    )
    cta = re.search(
        r'<button[^>]*onclick="tmsCreateFile\(\'Alpha/Mod\'\)"[^>]*>Create test case</button>',
        html,
    )
    assert cta, (
        "ES3 (module branch): empty depth-2 view must render a `Create test "
        "case` CTA wired to onclick=\"tmsCreateFile('Alpha/Mod')\""
    )

    # --- ES3 sub-folder branch (depth 3+): empty -> side-by-side CTAs. ---
    # SPEC/CODE DRIFT: spec says depth-2 AND depth-3+ both render
    # "No test cases in <name> yet." Code: depth-2 matches (folder_module.html);
    # depth-3+ renders "Nothing in <name> yet." (folder_subfolder.html).
    # Test follows code (same shape as feature-04 UI3, feature-05 RR1c).
    # When the templates are aligned to the spec, flip this assertion to
    # match the spec wording.
    html = client.get("/ui/folder/Alpha/Mod2/Sub").get_data(as_text=True)
    assert re.search(r"Nothing in\s*(?:<[^>]+>)?\s*Sub", html), (
        f"ES3 (sub-folder branch, spec/code drift): empty depth-3 view "
        f"renders 'Nothing in <folder> yet.' today (spec says 'No test cases "
        f"in <folder> yet.' -- drift surfaced for spec or template alignment); "
        f"HTML excerpt: {html[800:1200]!r}"
    )
    sub_cta = re.search(
        r'<button[^>]*onclick="tmsCreateSubfolder\(\'Alpha/Mod2/Sub\'\)"[^>]*>\+ Sub-folder</button>',
        html,
    )
    assert sub_cta, (
        "ES3 (sub-folder branch): empty depth-3 view must render a "
        "`+ Sub-folder` CTA wired to "
        "onclick=\"tmsCreateSubfolder('Alpha/Mod2/Sub')\""
    )
    # The empty state's `+ Test case` label drops the "Create" prefix used
    # in module empty state -- both labels are valid per the spec/template
    # drift surfaced during Step-1 sign-off (BD3/BD4 label drift).
    test_cta = re.search(
        r'<button[^>]*onclick="tmsCreateFile\(\'Alpha/Mod2/Sub\'\)"[^>]*>\+ Test case</button>',
        html,
    )
    assert test_cta, (
        "ES3 (sub-folder branch): empty depth-3 view must render a "
        "`+ Test case` CTA wired to "
        "onclick=\"tmsCreateFile('Alpha/Mod2/Sub')\" (label drops the "
        "'Create' prefix in the sub-folder empty state -- accepted drift "
        "per Step-1 sign-off)"
    )
print("PASS  ES3: depth-2 empty -> 'Create test case' CTA; depth-3 empty -> side-by-side '+ Sub-folder' + '+ Test case' CTAs")
