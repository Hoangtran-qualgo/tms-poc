# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / MV1-MV5 -- move flow.

Static inspection of tmsEditor.move() body:
  MV1: confirms with the spec literal when state.dirty.
  MV2: GET /api/tree, walks for folders with depth 2..10, opens
       tmsOpenModal with a <select>, current parent disabled, prompt
       option leaves Confirm disabled.
  MV3: PATCH /api/files/<p>/move with {parent: destParent}.
  MV4: success branch navigates via htmx.ajax to /ui/file/<newpath>.
  MV5: failure branch writes the error inline in the modal (modal NOT
       closed).
  MV6: a project <select> defaults to the source file's current project.
  MV7: the folder <select> is scoped to the selected project; option text
       is the project-relative path while the value stays the full path.
  MV8: success branch refreshes the directory tree deterministically
       (tmsRefreshTreePane), not only via the SSE `change` event.

Cross-credit (MV3): feature-05/F05_02_ui_triggers.py UI3 owns the
endpoint+verb+body shape.
"""
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(_p.read_text() for _p in sorted((REPO_ROOT / "app" / "static").glob("*.js")))


# --- Locate file-editor move() body. ---
BODY = None
for m in re.finditer(r"async\s+move\s*\(\s*\)\s*\{", JS):
    start = m.end() - 1
    depth = 0
    for i in range(start, len(JS)):
        c = JS[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                cand = JS[start:i + 1]
                if "/api/files/" in cand and "/move" in cand:
                    BODY = cand
                break
    if BODY:
        break
assert BODY, "MV-suite: tmsEditor.move() body must exist"


# --- MV1: dirty-buffer confirm with the spec literal. ---
assert re.search(
    r'if\s*\(\s*[\s\S]{0,80}?this\.state\.dirty\s*&&\s*[\s\S]{0,80}?window\.confirm\(\s*"Discard unsaved changes and move the file\?"',
    BODY,
), "MV1: move() must confirm with the spec literal when state.dirty"


# --- MV2: GET /api/tree + walker that filters depth 2..10. ---
assert re.search(r'fetch\(\s*"/api/tree"\s*\)', BODY), (
    "MV2: move() must GET /api/tree for the folder picker"
)
# Walker filters folders at depth >= 2 AND <= 10.
assert re.search(
    r'child\.type\s*!==?\s*"folder"', BODY
), "MV2: move() walker must skip non-folder children"
assert re.search(
    r'depth\s*=\s*child\.path\.split\(\s*"/"\s*\)\.length', BODY
), "MV2: move() walker must compute depth from child.path split('/')"
assert re.search(
    r'depth\s*>=?\s*2\s*&&\s*depth\s*<=?\s*10', BODY
), "MV2: move() walker must filter on depth >= 2 && depth <= 10"
# tmsOpenModal with confirmDisabled: true (prompt option keeps Confirm off).
assert "tmsOpenModal" in BODY, "MV2: move() must open via tmsOpenModal"
assert re.search(r'confirmDisabled:\s*true', BODY), (
    "MV2: tmsOpenModal call must set confirmDisabled: true so the prompt "
    "option leaves Confirm disabled until a real destination is picked"
)
# Current parent disabled in <option>.
assert re.search(
    r'if\s*\(\s*path\s*===?\s*currentParent\s*\)\s*opt\.disabled\s*=\s*true',
    BODY,
), "MV2: current parent <option> must be disabled in the picker"


# --- MV3: PATCH /api/files/<p>/move with {parent: destParent}. ---
assert re.search(
    r'fetch\(\s*\n?\s*"/api/files/"\s*\+\s*sourcePath\s*\+\s*"/move"', BODY
), "MV3: move() must target /api/files/<sourcePath>/move"
assert re.search(r'method:\s*"PATCH"', BODY), "MV3: move() must issue PATCH"
assert re.search(
    r'JSON\.stringify\(\s*\{\s*parent:\s*destParent\s*\}\s*\)', BODY
), "MV3: move() PATCH body must be JSON.stringify({parent: destParent})"


# --- MV4: success branch closes modal + navigates via htmx.ajax. ---
# In the onConfirm 2xx branch, close() is called first then htmx.ajax.
assert re.search(
    r'close\(\s*\)\s*;[\s\S]+?htmx\.ajax\(\s*"GET"\s*,\s*"/ui/file/"\s*\+\s*newPath',
    BODY,
), "MV4: success branch must close() then htmx.ajax('GET', '/ui/file/' + newPath, ...)"
assert re.search(
    r'newPath\s*=\s*destParent\s*\+\s*"/"\s*\+\s*segments\[\s*segments\.length\s*-\s*1\s*\]',
    BODY,
), "MV4: newPath must be destParent + '/' + leaf"


# --- MV5: failure branch writes inline; modal NOT closed. ---
# The non-ok branch sets error.textContent + un-hides; does NOT call close().
m_nonok = re.search(r'if\s*\(\s*!\s*r\.ok\s*\)\s*\{', BODY)
assert m_nonok, "MV5: move() must have non-ok branch `if (!r.ok) { ... }`"
i = m_nonok.end() - 1
depth = 0
for j in range(i, len(BODY)):
    c = BODY[j]
    if c == "{":
        depth += 1
    elif c == "}":
        depth -= 1
        if depth == 0:
            nonok = BODY[i:j + 1]
            break
assert "error.textContent" in nonok, (
    "MV5: failure branch must write to error.textContent inside the modal"
)
assert 'error.classList.remove("hidden")' in nonok, (
    "MV5: failure branch must un-hide the modal error region"
)
assert "close()" not in nonok, (
    "MV5: failure branch must NOT call close() (modal stays open for retry)"
)
assert "return" in nonok, (
    "MV5: failure branch must return after surfacing the error"
)

# --- MV6: project picker defaults to the current project. ---
assert re.search(r'currentProject\s*=\s*segments\[\s*0\s*\]', BODY), (
    "MV6: move() must derive currentProject from segments[0]"
)
# Walker also collects depth-1 folders (projects).
assert re.search(r'depth\s*===?\s*1\s*\)\s*projects\.push', BODY), (
    "MV6: walker must collect depth-1 folders as projects"
)
assert re.search(
    r'projects\.includes\(\s*currentProject\s*\)\s*\)\s*projectSelect\.value\s*=\s*currentProject',
    BODY,
), "MV6: the project <select> must default to the current project"


# --- MV7: folder options scoped to project; relative label, full value. ---
assert re.search(
    r'path\.split\(\s*"/"\s*\)\[\s*0\s*\]\s*!==?\s*proj', BODY
), "MV7: folder list must be filtered to the selected project"
assert re.search(
    r'rel\s*=\s*path\.split\(\s*"/"\s*\)\.slice\(\s*1\s*\)\.join\(\s*"/"\s*\)',
    BODY,
), "MV7: folder option label must be the project-relative path (prefix stripped)"
assert re.search(r'opt\.value\s*=\s*path', BODY), (
    "MV7: the folder option VALUE must stay the full path the PATCH needs"
)


# --- MV8: success branch refreshes the tree deterministically. ---
assert re.search(
    r'close\(\s*\)\s*;[\s\S]{0,400}?tmsRefreshTreePane\(\s*"tree-pane"\s*\)',
    BODY,
), "MV8: success branch must call tmsRefreshTreePane('tree-pane') after close()"


print("PASS  MV1-MV8: dirty-confirm; /api/tree walk depth 2..10 + modal; PATCH /move; success htmx.ajax to new path + tree refresh; failure stays in modal; project default + relative folder labels")
