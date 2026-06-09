# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Server helper `_folder_crumbs` (SH1).

`_folder_crumbs(segments) -> list[{label, path}]` builds the breadcrumb
chain for the sub-folder view AND the file-editor breadcrumb so both
render N levels uniformly. Tests the function directly (pure helper)
plus a render-side cross-check that the breadcrumb shape matches.
"""
import pathlib
import re
import tempfile

from app import create_app
from app.server import _folder_crumbs


# --- SH1 (direct): contract -- {label, path}, leaf excluded. ------------
# Single segment -> empty crumbs (no ancestors; the segment IS the leaf).
assert _folder_crumbs(["Alpha"]) == [], (
    f"SH1: _folder_crumbs(['Alpha']) must return [] (no ancestors when only "
    f"the leaf is present); got {_folder_crumbs(['Alpha'])!r}"
)

# Two segments -> one ancestor crumb (the project).
two = _folder_crumbs(["Alpha", "Mod"])
assert two == [{"label": "Alpha", "path": "Alpha"}], (
    f"SH1: _folder_crumbs(['Alpha', 'Mod']) must yield exactly one crumb for "
    f"'Alpha' (leaf 'Mod' excluded); got {two!r}"
)

# Deep chain -> one crumb per ancestor, paths cumulative.
deep = _folder_crumbs(["A", "B", "C", "D", "E"])
assert deep == [
    {"label": "A", "path": "A"},
    {"label": "B", "path": "A/B"},
    {"label": "C", "path": "A/B/C"},
    {"label": "D", "path": "A/B/C/D"},
], (
    f"SH1: _folder_crumbs(['A','B','C','D','E']) must yield one cumulative "
    f"crumb per ancestor (leaf 'E' excluded); got {deep!r}"
)

# Empty segments -> empty list (defensive).
assert _folder_crumbs([]) == [], (
    f"SH1: _folder_crumbs([]) must yield []; got {_folder_crumbs([])!r}"
)
print("PASS  SH1 (direct): _folder_crumbs builds N-level crumbs with leaf excluded; paths cumulative")


# --- SH1 (render cross-check): folder_subfolder.html uses the helper. ---
# A depth-5 sub-folder should render anchors for every ancestor (depths
# 1..4) -- the four crumbs that _folder_crumbs produces.
with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    chain = ["A", "B", "C", "D", "E"]  # depth-5 leaf
    for i in range(1, len(chain) + 1):
        client.post(
            "/api/folders",
            json={"parent": "/".join(chain[: i - 1]), "name": chain[i - 1]},
        )
    html = client.get("/ui/folder/A/B/C/D/E").get_data(as_text=True)

# Each ancestor must appear as a separate breadcrumb anchor with the
# cumulative hx-get path.
for label, path in [("A", "A"), ("B", "A/B"), ("C", "A/B/C"), ("D", "A/B/C/D")]:
    pattern = (
        rf'<a[^>]*hx-get="/ui/folder/{re.escape(path)}"[^>]*>{re.escape(label)}</a>'
    )
    assert re.search(pattern, html), (
        f"SH1 (render): folder_subfolder.html breadcrumb must render an anchor "
        f"<a hx-get=\"/ui/folder/{path}\">{label}</a> for ancestor at "
        f"depth {len(path.split('/'))}"
    )
# Leaf 'E' must NOT appear as a breadcrumb anchor -- it's the current
# folder, rendered as a heading instead.
assert not re.search(r'<a[^>]*hx-get="/ui/folder/A/B/C/D/E"', html), (
    "SH1 (render): leaf 'E' must NOT appear as a breadcrumb anchor (it's the "
    "current folder, rendered as <h2>)"
)
print("PASS  SH1 (render): folder_subfolder.html breadcrumb uses _folder_crumbs N-level output")
