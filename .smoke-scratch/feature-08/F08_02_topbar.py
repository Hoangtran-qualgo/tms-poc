# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / TP1 -- topbar buttons.

Render the file editor partial and confirm every topbar element listed
in the public-surface section of `08-feature-file-editor-NEW.md` is
present with the documented `id` AND visible label/role:
  - breadcrumb (Projects + crumb anchors)
  - `#dirty-indicator` (initially hidden)
  - `#saved-indicator` (role="status", initially hidden)
  - `#btn-rename`, `#btn-move`, `#btn-reload`, `#btn-save`

Cross-credit (cosmetic only): `feature-05/F05_03_ui_gaps.py` already
confirms that #btn-delete / #btn-duplicate are NOT present. This file
asserts the positive shape.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "description": "x"},
    )
    html = client.get("/ui/file/Alpha/Mod/case.feature").get_data(as_text=True)

# Breadcrumb root anchor.
assert re.search(
    r'<a[^>]*hx-get="/ui/folder/"[^>]*>Projects</a>', html
), (
    "TP1: topbar must render a 'Projects' anchor with "
    'hx-get="/ui/folder/" as the breadcrumb root'
)
# Per-crumb anchors. Two crumbs expected: Alpha, Mod.
for crumb in ("Alpha", "Alpha/Mod"):
    assert f'hx-get="/ui/folder/{crumb}"' in html, (
        f"TP1: breadcrumb must include an anchor for {crumb!r} "
        f'(hx-get="/ui/folder/{crumb}")'
    )

# Dirty + saved indicators with the right initial classes.
assert re.search(
    r'<span[^>]*id="dirty-indicator"[^>]*class="[^"]*\bhidden\b[^"]*"', html
), "TP1: #dirty-indicator must render initially hidden"
assert re.search(
    r'<span[^>]*id="saved-indicator"[^>]*class="[^"]*\bhidden\b[^"]*"[^>]*role="status"',
    html,
), "TP1: #saved-indicator must render initially hidden with role='status'"

# Topbar buttons -- id + visible label.
for btn_id, label in (
    ("btn-rename", "Rename"),
    ("btn-move", "Move"),
    ("btn-reload", "Reload"),
    ("btn-save", "Save"),
):
    pat = re.compile(
        rf'<button[^>]*id="{re.escape(btn_id)}"[^>]*>([\s\S]*?)</button>',
    )
    m = pat.search(html)
    assert m, f"TP1: topbar must render a <button id={btn_id!r} ...>"
    visible = re.sub(r"&[a-z]+;", "", m.group(1)).strip()
    assert label in visible, (
        f"TP1: #{btn_id} button label must include {label!r}; got {visible!r}"
    )

# Negative: no delete or duplicate button in the topbar.
for forbidden in ("btn-delete", "btn-duplicate"):
    assert f'id="{forbidden}"' not in html, (
        f"TP1 (gap): editor topbar must NOT carry #{forbidden} button "
        "(feature-05 owns the absence claim; this is a sanity check)"
    )

print(
    "PASS  TP1: editor topbar renders breadcrumb + dirty/saved indicators + "
    "btn-rename / btn-move / btn-reload / btn-save"
)
