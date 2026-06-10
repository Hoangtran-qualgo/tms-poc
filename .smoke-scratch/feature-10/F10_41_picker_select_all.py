"""Smoke i1: tmsBuildCasePicker grows a tri-state select-all header.

Tracks the "Investigate: `+ Add test case` modal — select-all
affordance" Must-have item. Static wiring only — the actual tri-state
click behaviour requires a browser per the standing Phase-2 lock-in.

Three assertions:
1. The picker's table header now hosts an `<input type="checkbox">`
   with `data-role="select-all"` (the sentinel the picker uses to
   address the header from JS).
2. The picker exposes the agreed accessible label
   `aria-label="Select all visible"` (Q5 decision: aria-label only,
   no `title=` tooltip — matches the unlabelled per-row checkboxes
   one column over for visual consistency).
3. The select-all feature stayed inside the picker: the sole
   remaining caller (`_onAddCaseClicked` on `tmsRunEditor`) must
   not reference the `select-all` sentinel anywhere in its body.
   This guards against the feature leaking into the caller, which
   would re-couple the picker contract.
"""
import re
import pathlib

APP_JS = "\n".join(_p.read_text() for _p in sorted(pathlib.Path("app/static").glob("*.js")))

# --- 1. Header hosts the select-all checkbox --------------------------
# Match the actual <input> string literal the picker emits via
# innerHTML so a stray rename of `data-role="select-all"` is caught
# even if the surrounding markup is rearranged.
assert re.search(
    r'<input\s+type="checkbox"[^>]*data-role="select-all"', APP_JS
), "picker header should contain <input type='checkbox' data-role='select-all'>"
print("PASS  select-all checkbox present in picker <thead>")

# --- 2. Accessible label is the agreed copy ---------------------------
assert (
    'aria-label="Select all visible"' in APP_JS
), "picker header checkbox should carry aria-label='Select all visible'"
print("PASS  aria-label='Select all visible' wired (no title= tooltip)")

# --- 3. Caller (`_onAddCaseClicked`) does not reference select-all ---
# Carve out the function body via the consistent method-indent +
# `\n  },` closer used by the rest of the tmsRunEditor methods.
m = re.search(
    r"async\s+_onAddCaseClicked\s*\(\s*\)\s*\{[\s\S]*?\n  \},",
    APP_JS,
)
assert m, "could not locate _onAddCaseClicked function body in app.js"
caller_body = m.group(0)
assert "select-all" not in caller_body, (
    "_onAddCaseClicked must not reference the 'select-all' sentinel — "
    "the feature should stay inside tmsBuildCasePicker"
)
print("PASS  _onAddCaseClicked stays clean of select-all wiring")
