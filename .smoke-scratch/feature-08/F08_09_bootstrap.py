# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / B1 + B2 -- bootstrap.

B1: `file_editor.html` tail script calls `tmsBootEditor()` after the
    partial is swapped in (render-and-grep).
B2: `tmsEditor.boot()` reads #editor-data, hydrates `state` with the
    documented shape (`path`, `file_name`, `feature`, `raw`,
    `snapshotJson`, `snapshotRaw`, `dirty: false`, `tab: "structured"`).

The snapshots drive external-change detection (see EB1/EB2/EB3).
"""
import pathlib
import re
import tempfile

from app import create_app


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = (REPO_ROOT / "app" / "static" / "app.js").read_text()


# --- B1: tail script calls tmsBootEditor() -----------------------------
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

# Tail `<script>` block must call tmsBootEditor() guarded against the
# function being undefined (in case the partial is rendered out-of-band).
tail = re.search(r'<script>([\s\S]*?)</script>\s*$', html.strip())
assert tail, "B1: file_editor.html must include a tail <script> block"
tail_body = tail.group(1)
assert "tmsBootEditor()" in tail_body, (
    f"B1: tail <script> must call tmsBootEditor(); got body={tail_body!r}"
)


# --- B2: tmsEditor.boot() hydrates the state object --------------------
# Locate the file-editor's boot() body (not the run-editor's).
# Easiest disambiguation: the file-editor boot body reads `#editor-data`.
boot = None
for m in re.finditer(r'\bboot\s*\(\s*\)\s*\{', JS):
    start = m.end() - 1
    depth = 0
    for i in range(start, len(JS)):
        c = JS[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                body = JS[start:i + 1]
                if 'getElementById("editor-data")' in body:
                    boot = body
                break
    if boot:
        break
assert boot, "B2: tmsEditor.boot() reading #editor-data must exist"

# Required state shape literals.
for key in (
    "path: data.path",
    "file_name: data.file_name",
    "feature: data.feature",
    "raw: data.raw",
    "snapshotJson: JSON.stringify(data.feature)",
    "snapshotRaw: data.raw",
    "dirty: false",
    'tab: "structured"',
):
    assert key in boot, (
        f"B2: tmsEditor.boot() must hydrate state with {key!r}; "
        f"missing from boot() body"
    )

# JSON.parse drives the read.
assert "JSON.parse(dataEl.textContent)" in boot, (
    "B2: tmsEditor.boot() must read #editor-data via JSON.parse(textContent)"
)

print("PASS  B1 + B2: file_editor.html tail calls tmsBootEditor(); tmsEditor.boot() hydrates the documented state shape")
