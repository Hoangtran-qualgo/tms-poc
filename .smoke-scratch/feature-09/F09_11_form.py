# Pattern: see .smoke-scratch/README.md
"""feature-09 / search / FM1 + scope-picker drift.

FM1: the top-bar form renders with all four controls wired to the
     ids/names tmsWireSearch expects, inside
     `<form id="search-form" onsubmit="event.preventDefault();">`:
       - #search-q   (type=search, name=q)
       - #search-scope (select, name=scope)
       - #search-match (select, name=match) with text/tag options
       - #search-case (checkbox, name=case, value=true)

DRIFT (scope-picker): the spec's public surface advertises three scope
     values (all / project:<name> / module:<proj>/<mod>), but the
     rendered #search-scope select only offers a single hard-coded
     `<option value="all">All</option>`. No project/module options are
     populated. Pinned here as a real assertion so the drift is caught
     if the template ever starts (or stops) rendering scope options.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()

    html = client.get("/").get_data(as_text=True)

    # --- FM1: the form wrapper with preventDefault submit. ---
    assert re.search(
        r'<form[^>]*\bid="search-form"[^>]*onsubmit="event\.preventDefault\(\);?"',
        html,
    ), "FM1: #search-form must render with onsubmit=event.preventDefault()"

    # --- FM1: query input. ---
    assert re.search(
        r'<input[^>]*\bid="search-q"[^>]*\btype="search"[^>]*\bname="q"', html
    ) or re.search(
        r'<input[^>]*\bid="search-q"[^>]*\bname="q"', html
    ), "FM1: #search-q text/search input (name=q) must render"

    # --- FM1: match select with both modes. ---
    assert re.search(r'<select[^>]*\bid="search-match"[^>]*\bname="match"', html), (
        "FM1: #search-match select (name=match) must render"
    )
    assert '<option value="text"' in html and '<option value="tag"' in html, (
        "FM1: #search-match must offer both 'text' and 'tag' options"
    )

    # --- FM1: case checkbox. ---
    assert re.search(
        r'<input[^>]*\bid="search-case"[^>]*\btype="checkbox"[^>]*\bname="case"[^>]*\bvalue="true"',
        html,
    ), "FM1: #search-case checkbox (name=case, value=true) must render"

    # --- FM1 + DRIFT: scope select renders but offers ONLY 'all'. ---
    scope_m = re.search(
        r'(<select[^>]*\bid="search-scope"[^>]*\bname="scope"[^>]*>)(.*?)(</select>)',
        html,
        re.DOTALL,
    )
    assert scope_m, "FM1: #search-scope select (name=scope) must render"
    options = re.findall(r'<option\s+value="([^"]*)"', scope_m.group(2))
    assert options == ["all"], (
        f"DRIFT: #search-scope must offer exactly one hard-coded 'all' option "
        f"(no project/module options are rendered despite the spec), got {options}"
    )

print("PASS  FM1 + scope-picker drift: form renders all four wired controls; #search-scope offers only the hard-coded 'all' option")
