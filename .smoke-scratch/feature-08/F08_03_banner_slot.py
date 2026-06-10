# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / TP2 -- editor banner slot.

Two halves:
  - render-and-grep: `#editor-banner` is present, initially empty +
    `hidden`.
  - static `_showBanner` body: the tmsEditor method that populates the
    banner targets `#editor-banner` AND honours the `{kind, message,
    actions}` contract from the spec.
"""
import pathlib
import re
import tempfile

from app import create_app


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(_p.read_text() for _p in sorted((REPO_ROOT / "app" / "static").glob("*.js")))


# --- Render half --------------------------------------------------------
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

m = re.search(
    r'<div[^>]*id="editor-banner"[^>]*class="([^"]*)"[^>]*>([\s\S]*?)</div>',
    html,
)
assert m, "TP2: rendered template must include <div id='editor-banner'>"
cls, body = m.group(1), m.group(2).strip()
assert "hidden" in cls, (
    f"TP2: #editor-banner must render with the `hidden` class initially; "
    f"got class={cls!r}"
)
assert body == "", (
    f"TP2: #editor-banner must be EMPTY by default (populated by "
    f"tmsEditor._showBanner); got body={body!r}"
)


# --- Static _showBanner half --------------------------------------------
# Two `_showBanner` definitions exist (run editor + file editor). Pick
# the file-editor one by requiring `editor-banner` in the body.
def _extract_body(js: str, sig: str, contains: str | None = None) -> str:
    for m in re.finditer(sig, js, flags=re.DOTALL):
        start = js.index("{", m.end() - 1)
        depth = 0
        for i in range(start, len(js)):
            c = js[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    body = js[start:i + 1]
                    if contains is None or contains in body:
                        return body
                    break
    raise AssertionError(f"signature {sig!r} not found (contains={contains!r})")


body = _extract_body(JS, r"_showBanner\s*\(\s*\{\s*kind\s*,\s*message\s*,\s*actions\s*\}\s*\)",
                      contains='"editor-banner"')
assert 'getElementById("editor-banner")' in body, (
    "TP2: file-editor `_showBanner` body must target `#editor-banner`"
)
# Honours actions: each action becomes a <button> with its label.
assert "actions.forEach" in body, (
    "TP2: `_showBanner` must iterate `actions` to render one button per action"
)
assert "btn.textContent = a.label" in body, (
    "TP2: each action button's textContent must come from `action.label`"
)
assert "btn.addEventListener(\"click\", a.action)" in body, (
    "TP2: each action button must wire click -> `action.action`"
)

print("PASS  TP2: #editor-banner empty/hidden by default; _showBanner populates it from {kind, message, actions}")
