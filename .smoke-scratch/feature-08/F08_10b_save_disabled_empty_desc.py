# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / D3 -- Save disabled when description empty.

Hybrid: static `updateSaveButton` body + end-to-end render check.

Static: `updateSaveButton` reads `state.feature.description`, trims,
and sets `btn-save.disabled = !desc`.

End-to-end: file_editor.html renders <button id='btn-save'> with the
Tailwind `disabled:bg-slate-400 disabled:cursor-not-allowed` classes
so the visual disabled state survives a renderer regression. The
controller-side initial state is asserted via the static body (the
`disabled` attribute is set by JS at boot, not by the template).
"""
import pathlib
import re
import tempfile

from app import create_app


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(_p.read_text() for _p in sorted((REPO_ROOT / "app" / "static").glob("*.js")))


# --- Static: updateSaveButton body. ---
m = re.search(r'\bupdateSaveButton\s*\(\s*\)\s*\{', JS)
assert m, "D3: tmsEditor.updateSaveButton() must exist"
start = m.end() - 1
depth = 0
for i in range(start, len(JS)):
    c = JS[i]
    if c == "{":
        depth += 1
    elif c == "}":
        depth -= 1
        if depth == 0:
            BODY = JS[start:i + 1]
            break

assert 'getElementById("btn-save")' in BODY, (
    "D3: updateSaveButton must target #btn-save"
)
assert re.search(
    r'this\.state\?\.\s*feature\?\.\s*description\s*\|\|\s*""', BODY
), "D3: updateSaveButton must read state.feature.description with || '' fallback"
assert ".trim()" in BODY, (
    "D3: updateSaveButton must trim() the description before the empty check"
)
assert re.search(r'btn\.disabled\s*=\s*!\s*desc', BODY), (
    "D3: updateSaveButton must set `btn.disabled = !desc` "
    "(disabled when description is empty / whitespace-only)"
)


# --- End-to-end: rendered template includes the disabled-state styling. ---
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

m_btn = re.search(
    r'<button[^>]*id="btn-save"[^>]*class="([^"]*)"', html
)
assert m_btn, "D3: rendered template must include <button id='btn-save'>"
btn_cls = m_btn.group(1)
assert "disabled:bg-slate-400" in btn_cls, (
    "D3: #btn-save must carry `disabled:bg-slate-400` so the visual disabled "
    "state survives once JS sets the `disabled` attribute"
)
assert "disabled:cursor-not-allowed" in btn_cls, (
    "D3: #btn-save must carry `disabled:cursor-not-allowed` for affordance"
)

print("PASS  D3: Save button disabled when description empty (updateSaveButton body + Tailwind disabled-state classes on the rendered button)")
