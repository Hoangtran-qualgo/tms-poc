# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / RN1 + RN2 + RN3 -- rename flow.

RN1: rename() uses window.prompt (legacy v1 affordance per spec).
RN2: PATCH /api/files/<state.path>/rename with {file_name: next}.
RN3: On success, navigates to /ui/file/<newpath> via htmx.ajax(...).

Per Step-1 sign-off: RN1 is STRICT -- if rename is migrated to
tmsOpenModal, this smoke fails loudly and surfaces the drift.

Cross-credit (RN2): feature-05/F05_02_ui_triggers.py UI2 already
asserts the endpoint+verb+body shape. This smoke owns the controller-
side flow (prompt + navigation).
"""
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(_p.read_text() for _p in sorted((REPO_ROOT / "app" / "static").glob("*.js")))


# --- Locate file-editor rename() body. ---
# Multiple async rename() may exist; pick the one referencing /api/files/.
BODY = None
for m in re.finditer(r"async\s+rename\s*\(\s*\)\s*\{", JS):
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
                if "/api/files/" in cand:
                    BODY = cand
                break
    if BODY:
        break
assert BODY, "RN-suite: tmsEditor.rename() body must exist"


# --- RN1: uses window.prompt (legacy v1 affordance). ---
# Strict per Step-1 sign-off Q5. A future migration to tmsOpenModal must
# fail loudly here so the drift is surfaced and reviewed.
assert re.search(
    r'window\.prompt\(\s*"Rename file to:"', BODY
), (
    "RN1 (strict): rename() must use window.prompt('Rename file to:', current). "
    "If the team migrates to tmsOpenModal, this smoke must be updated."
)
assert "tmsOpenModal" not in BODY, (
    "RN1 (strict): rename() must NOT use tmsOpenModal yet "
    "(spec flags this as a follow-up migration target)"
)


# --- RN2: PATCH /api/files/<state.path>/rename with {file_name: next}. ---
assert re.search(
    r'fetch\(\s*\n?\s*"/api/files/"\s*\+\s*this\.state\.path\s*\+\s*"/rename"',
    BODY,
), "RN2: rename must target /api/files/<state.path>/rename"
assert re.search(r'method:\s*"PATCH"', BODY), (
    "RN2: rename must issue PATCH"
)
assert re.search(
    r'JSON\.stringify\(\s*\{\s*file_name:\s*next\s*\}\s*\)', BODY
), "RN2: rename PATCH body must be JSON.stringify({file_name: next})"


# --- RN3: success branch navigates via htmx.ajax to /ui/file/<newpath>. ---
# The success branch computes the new path (appends `.feature` if missing)
# and issues htmx.ajax('GET', '/ui/file/' + newPath, {target: '#main-pane'}).
assert re.search(
    r'htmx\.ajax\(\s*"GET"\s*,\s*"/ui/file/"\s*\+\s*newPath', BODY
), "RN3: rename success branch must call htmx.ajax('GET', '/ui/file/' + newPath, ...)"
assert re.search(
    r'target:\s*"#main-pane"', BODY
), "RN3: htmx.ajax target must be '#main-pane'"
# Empty-input / no-op guard: empty trim() OR same-name short-circuits.
assert re.search(
    r'if\s*\(\s*!\s*next\s*\|\|\s*next\s*===?\s*current\s*\)\s*return',
    BODY,
), "RN3: rename must early-return when prompt is empty or unchanged"

print("PASS  RN1 + RN2 + RN3: rename uses window.prompt (legacy); PATCH /api/files/<p>/rename; htmx.ajax to /ui/file/<newpath> on success")
