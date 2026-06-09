# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / CR2 + CR6 + CR8 -- tmsCreateRun gating.

CR2: bootstrap does a single GET /api/run-groups; on fetch failure it
     alert()s and returns WITHOUT opening a modal.
CR6: the Confirm gate requires (slug non-empty) AND (path resolved),
     where "path resolved" means an existing proj|group pick OR both
     project + group-name inputs filled in the new-group branch.
CR8: per-input listeners drive slug/reveal/error-clear (change on the
     selects, input on the text fields) and inline errors are cleared
     (the modal stays open on error so the user can fix one input).

Static JS inspection of app/static/app.js.
"""
import re
import pathlib

JS = pathlib.Path("app/static/app.js").read_text()

# Scope to the tmsCreateRun() body via brace matching.
start = JS.index("async function tmsCreateRun()")
i = JS.index("{", start)
depth, j = 1, i + 1
while j < len(JS) and depth:
    depth += {"{": 1, "}": -1}.get(JS[j], 0)
    j += 1
fn = JS[start:j]

# --- CR2: single run-groups fetch + alert/return on failure. ---
assert fn.count('fetch("/api/run-groups"') == 1, "exactly one /api/run-groups fetch"
assert re.search(r'alert\("Could not load run groups: "[\s\S]*?return;', fn), (
    "fetch failure must alert + return (no modal opened)"
)

# --- CR6: confirm gate = nameOk AND pathOk. ---
gate = re.search(r"const refreshGate = \(\) => \{.*?\};", fn, re.DOTALL).group(0)
assert "tmsSlugifyForFilename(nameInput.value).length > 0" in gate, "slug non-empty check"
assert 'whereSel.value === "__new__"' in gate
assert "newProjSel.value.length > 0" in gate and "newGrpInput.value.trim().length > 0" in gate
assert re.search(r"setConfirmDisabled\(!\(nameOk && pathOk\)\)", gate), (
    "Confirm must be gated on (nameOk && pathOk)"
)

# --- CR8: per-input listeners drive reveal / slug / error-clear. ---
assert 'whereSel.addEventListener("change", updateNewGroupVisibility)' in fn
assert 'newProjSel.addEventListener("change", refreshGate)' in fn
assert re.search(r'newGrpInput\.addEventListener\("input",\s*\(\)\s*=>\s*\{', fn)
assert 'nameInput.addEventListener("input", updateSlugPreview)' in fn

# --- CR8: inline errors are cleared (modal stays open on error). ---
assert fn.count('classList.add("hidden")') >= 3, "error <p>s are hidden/cleared reactively"
assert "updateSlugPreview" in fn and "updateNewGroupVisibility" in fn

print("PASS  CR2+CR6+CR8: single run-groups fetch (alert+return on fail); Confirm gate = slug AND path; per-input listeners + error-clear")
