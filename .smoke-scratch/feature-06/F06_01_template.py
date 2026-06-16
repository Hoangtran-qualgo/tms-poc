# Pattern: see .smoke-scratch/README.md
"""feature-06 / tree-pane / Template macro (TM1-TM4).

Asserts the rendered HTML shape from `app/templates/tree.html` via
`GET /ui/tree`. The template is render-and-grep-tested: we build a
small fixture FS (project + module + .feature file + non-.feature
sibling), hit the route, and grep for the documented row shapes.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "scenario_name": "s", "description": "seed"},
    )
    # A non-.feature sibling. /api/files refuses these (FN1 reject),
    # so we drop it directly through pathlib to exercise the
    # tree-other branch of the template.
    (root / "Alpha" / "Mod" / "note.txt").write_text("scratch", encoding="utf-8")

    html = client.get("/ui/tree").get_data(as_text=True)

# --- TM1: `<ul>` with `<li>` per child. ----------------------------------
assert re.search(r'<ul[^>]*>\s*<li>', html), (
    "TM1: tree.html must render children as a nested `<ul>...<li>` list "
    "(one `<li>` per child). No `<ul><li>` pair found in /ui/tree HTML."
)
li_count = len(re.findall(r"<li>", html))
assert li_count >= 3, (
    f"TM1: expected at least 3 `<li>` rows (Alpha, Mod, case.feature, "
    f"note.txt); got {li_count}"
)

# --- TM2: caret <button> + name <span> are SEPARATE elements. ------------
# The caret toggles via onclick=toggleTreeFolder; the name span navigates
# via hx-get to /ui/folder/<path>. They must be distinct elements so the
# caret can stopPropagation() without cancelling the name's navigation.
caret = re.search(
    r'<button[^>]*class="caret[^"]*"[^>]*onclick="[^"]*toggleTreeFolder',
    html,
)
assert caret, (
    "TM2: folder rows must carry a `<button class=\"caret\" "
    "onclick=\"... toggleTreeFolder(...)\">` element (caret toggles)"
)
name_span = re.search(
    r'<span[^>]*hx-get="/ui/folder/Alpha"', html,
)
assert name_span, (
    "TM2: folder rows must carry a `<span ... hx-get=\"/ui/folder/<path>\">` "
    "element (name navigates); caret and name MUST be separate elements"
)

# --- TM3: .feature files emit <div class="tree-file"> with /ui/file/<p>. -
tree_file = re.search(
    r'<div[^>]*class="tree-file[^"]*"[^>]*hx-get="/ui/file/Alpha/Mod/case\.feature"',
    html,
)
assert tree_file, (
    "TM3: .feature file rows must render as "
    "`<div class=\"tree-file\" ... hx-get=\"/ui/file/<path>\">` "
    "(checked Alpha/Mod/case.feature)"
)

# --- TM4: non-.feature files emit <div class="tree-other"> w/ same hx-get.
tree_other = re.search(
    r'<div[^>]*class="tree-other[^"]*"[^>]*hx-get="/ui/file/Alpha/Mod/note\.txt"',
    html,
)
assert tree_other, (
    "TM4: non-.feature file rows must render as "
    "`<div class=\"tree-other\" ... hx-get=\"/ui/file/<path>\">` "
    "(checked Alpha/Mod/note.txt)"
)
print("PASS  TM1-TM4: tree.html emits <ul><li>; caret+name separate; tree-file/tree-other hx-get to /ui/file/<p>")
