# Pattern: see .smoke-scratch/README.md
"""feature-06 / tree-pane / Click navigation (CN1-CN3).

Renders /ui/tree with a fixture FS that exercises every depth + every
row kind, then asserts the documented hx-get + onclick contracts.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    # Walk to depth 5 to prove CN2 works at any depth.
    chain = ["Alpha", "Mod", "Sub1", "Sub2", "Sub3"]
    for i in range(1, len(chain) + 1):
        client.post(
            "/api/folders",
            json={"parent": "/".join(chain[: i - 1]), "name": chain[i - 1]},
        )
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "scenario_name": "s", "description": "x"},
    )
    (root / "Alpha" / "Mod" / "note.txt").write_text("scratch", encoding="utf-8")

    html = client.get("/ui/tree").get_data(as_text=True)

# --- CN1: caret has onclick + stopPropagation + toggleTreeFolder; NO hx-*.
carets = re.findall(r'<button[^>]*class="caret[^"]*"[^>]*>', html)
assert carets, "CN1 setup: at least one caret button must render"
for caret in carets:
    assert "event.stopPropagation()" in caret, (
        f"CN1: caret <button> must call event.stopPropagation() so the "
        f"toggle does not bubble to the row's HTMX navigation; got {caret!r}"
    )
    assert "toggleTreeFolder" in caret, (
        f"CN1: caret <button> must invoke toggleTreeFolder(...); got {caret!r}"
    )
    assert "hx-" not in caret, (
        f"CN1: caret <button> must NOT carry any hx-* attribute (caret "
        f"toggles only -- no HTMX navigation); got {caret!r}"
    )

# --- CN2: folder name <span> hx-get="/ui/folder/<path>" at any depth. ---
for path in chain[:1] + ["Alpha/Mod", "Alpha/Mod/Sub1", "Alpha/Mod/Sub1/Sub2/Sub3"]:
    pattern = (
        r'<span[^>]*hx-get="/ui/folder/' + re.escape(path) + r'"[^>]*'
        r'hx-target="#main-pane"[^>]*hx-swap="innerHTML"'
    )
    assert re.search(pattern, html), (
        f"CN2: folder name <span> for path {path!r} must carry "
        f"hx-get=\"/ui/folder/{path}\" + hx-target=\"#main-pane\" + "
        f"hx-swap=\"innerHTML\" (must work at any depth)"
    )

# --- CN3: .tree-file (and .tree-other) rows hx-get="/ui/file/<path>". ---
tree_file = re.search(
    r'<div[^>]*class="tree-file[^"]*"[^>]*hx-get="/ui/file/Alpha/Mod/case\.feature"[^>]*'
    r'hx-target="#main-pane"[^>]*hx-swap="innerHTML"',
    html,
)
assert tree_file, (
    "CN3: .tree-file row for Alpha/Mod/case.feature must carry "
    "hx-get=\"/ui/file/Alpha/Mod/case.feature\" + hx-target=\"#main-pane\" "
    "+ hx-swap=\"innerHTML\""
)
tree_other = re.search(
    r'<div[^>]*class="tree-other[^"]*"[^>]*hx-get="/ui/file/Alpha/Mod/note\.txt"[^>]*'
    r'hx-target="#main-pane"[^>]*hx-swap="innerHTML"',
    html,
)
assert tree_other, (
    "CN3: .tree-other row for Alpha/Mod/note.txt must carry the same hx-get "
    "shape (route resolves non-.feature to unsupported.html)"
)

# Confirm the route ACTUALLY maps non-.feature -> unsupported.html.
r = client.get("/ui/file/Alpha/Mod/note.txt")
assert r.status_code == 200, (
    f"CN3 route check: GET /ui/file/<non-feature> must return 200, got {r.status_code}"
)
body = r.get_data(as_text=True)
assert "unsupported" in body.lower() or "not supported" in body.lower(), (
    "CN3 route check: GET /ui/file/<non-feature> must render unsupported.html "
    f"(its body should mention 'unsupported' / 'not supported'); got {body[:120]!r}"
)
print("PASS  CN1-CN3: caret stopPropagation+toggleTreeFolder; folder hx-get; tree-file/other -> /ui/file -> unsupported.html")
