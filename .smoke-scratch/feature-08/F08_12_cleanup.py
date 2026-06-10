# Pattern: see .smoke-scratch/README.md
"""feature-08 / file-editor / CL1 + CL2 + CL3 + CL4 -- cleanupBuffer.

Static inspection of `tmsEditor.cleanupBuffer()` body:
  CL1: drops empty-text steps in BOTH background and scenario.
  CL2: drops examples rows whose cells are all-empty (header preserved).
  CL3: per-step data_table: all-empty -> null, else keep header + filter
       all-empty body rows.
  CL4: outline-only refusal -> returns the spec error string when there
       are zero examples blocks; save()'s caller turns that into an
       alert("Cannot save: ...").
"""
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(_p.read_text() for _p in sorted((REPO_ROOT / "app" / "static").glob("*.js")))


# --- Locate cleanupBuffer() body. ---
m = re.search(r'cleanupBuffer\s*\(\s*\)\s*\{', JS)
assert m, "CL-suite: tmsEditor.cleanupBuffer() must exist"
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


# --- CL1: background.steps + scenario.steps filtered on empty text. ---
for arr in ("f.background.steps", "f.scenario.steps"):
    pat = re.compile(
        rf'{re.escape(arr)}\s*=\s*{re.escape(arr)}\.filter\(\s*\(\s*s\s*\)\s*=>\s*\(\s*s\.text\s*\|\|\s*""\s*\)\.trim\(\s*\)\s*!==\s*""\s*\)'
    )
    assert pat.search(BODY), (
        f"CL1: cleanupBuffer must filter empty-text steps from {arr} "
        f"(missing `{arr} = {arr}.filter((s) => (s.text || '').trim() !== '')`)"
    )


# --- CL2: examples rows with all-empty cells dropped (header preserved). ---
# The body filters ex.rows on the row having at least one non-empty cell.
assert re.search(
    r'ex\.rows\s*=\s*ex\.rows\.filter\(\s*\(\s*r\s*\)\s*=>\s*r\.some\(\s*\(\s*c\s*\)\s*=>\s*\(\s*c\s*\|\|\s*""\s*\)\.trim\(\s*\)\s*!==\s*""\s*\)\s*\)',
    BODY,
), (
    "CL2: cleanupBuffer must filter all-empty examples rows "
    "(missing `ex.rows = ex.rows.filter(r => r.some(c => (c||'').trim() !== ''))`)"
)
# Header preserved: no slicing of ex.header or ex.rows.unshift in the body.
assert "ex.header" not in BODY or "ex.header =" not in BODY, (
    "CL2: cleanupBuffer must NOT mutate ex.header (header is preserved)"
)


# --- CL3: per-step data_table: all-empty -> null, else keep header. ---
# The body defines a `cleanStepDT` helper.
assert "cleanStepDT" in BODY, (
    "CL3: cleanupBuffer must define a `cleanStepDT` helper for data_table"
)
# All-empty -> null.
assert re.search(
    r'allEmpty\s*=\s*dt\.every\(\s*\(\s*r\s*\)\s*=>\s*r\.every\(\s*\(\s*c\s*\)\s*=>\s*\(\s*c\s*\|\|\s*""\s*\)\.trim\(\s*\)\s*===?\s*""\s*\)\s*\)',
    BODY,
), "CL3: data_table all-empty detection must check every row + every cell trim() === ''"
assert re.search(
    r'if\s*\(\s*allEmpty\s*\)\s*\{\s*step\.data_table\s*=\s*null', BODY
), "CL3: all-empty data_table must be set to null"
# Else: keep header (dt[0]) + filter body rows.
assert re.search(
    r'step\.data_table\s*=\s*\[\s*dt\[0\]\s*\]\.concat\(\s*dt\.slice\(\s*1\s*\)\.filter\(',
    BODY,
), (
    "CL3: non-all-empty data_table must rebuild as [header].concat(body.filter(...))"
)
# Both background + scenario steps run cleanStepDT.
for arr in ("f.background.steps", "f.scenario.steps"):
    assert re.search(
        rf'{re.escape(arr)}\.forEach\(\s*cleanStepDT\s*\)', BODY
    ), f"CL3: cleanupBuffer must run cleanStepDT over {arr}"


# --- CL4: outline-only refusal on zero examples blocks. ---
assert re.search(
    r'if\s*\(\s*f\.scenario\.kind\s*===?\s*"outline"\s*\)', BODY
), "CL4: cleanupBuffer must branch on scenario.kind === 'outline'"
assert re.search(
    r'blocks\s*=\s*f\.scenario\.examples\.length', BODY
), "CL4: outline branch must compute blocks = f.scenario.examples.length"
assert re.search(
    r'if\s*\(\s*blocks\s*===?\s*0\s*\)\s*\{\s*return\s*"An outline must have at least one Examples block\."',
    BODY,
), (
    "CL4: zero-blocks branch must return the spec error string "
    "'An outline must have at least one Examples block.'"
)

# Also verify save() turns the returned error into an alert("Cannot save: ...").
m_save = re.search(r"async\s+save\s*\(\s*\)\s*\{", JS)
# Pick the file-editor save (contains /api/files/).
SAVE = None
for m in re.finditer(r"async\s+save\s*\(\s*\)\s*\{", JS):
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
                if "/api/files/" in cand and "cleanupBuffer" in cand:
                    SAVE = cand
                break
    if SAVE:
        break
assert SAVE, "CL4: file-editor save() body must exist"
assert re.search(
    r'err\s*=\s*this\.cleanupBuffer\(\s*\)[\s\S]{0,80}?if\s*\(\s*err\s*\)\s*\{\s*alert\(\s*"Cannot save: "\s*\+\s*err',
    SAVE,
), "CL4: save() must convert cleanupBuffer's returned error to alert('Cannot save: ' + err)"

print("PASS  CL1 + CL2 + CL3 + CL4: cleanupBuffer drops empty steps + empty examples rows; data_table all-empty -> null; outline-only refusal returns the spec error -> alert")
