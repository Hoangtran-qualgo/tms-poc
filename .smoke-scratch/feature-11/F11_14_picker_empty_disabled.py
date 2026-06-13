# Pattern: see .smoke-scratch/README.md
"""feature-11 / enums / ED11 -- empty-list kind renders a disabled value picker.

ED11: a kind defined in `enums.yaml` but with no entries (e.g.
     `priorities: []`) renders its value `<select>` disabled with the hint
     "No <kind> entries defined yet — edit enums.yaml to add some."

tech-04 D5 reshaped the editor into a (kind, value) row grid; the ED11
contract now lives on the per-row value `<select>` built by
`tmsEditor._buildEnumRow`.
"""
import re
import pathlib

JS = "\n".join(_p.read_text() for _p in sorted(pathlib.Path("app/static").glob("*.js")))
m = re.search(r"_buildEnumRow\(row, vocab\)\s*\{.*?\n  \},", JS, re.DOTALL)
assert m, "_buildEnumRow must be defined"
fn = m.group(0)

# --- ED11: zero-entry branch disables the value control + appends the hint. ---
empty = re.search(r"else if\s*\(\s*keys\.length === 0\s*\)\s*\{.*?\}", fn, re.DOTALL)
assert empty, "must branch on keys.length === 0 for a kind with no entries"
assert "valSel.disabled = true" in empty.group(0), "empty-list value picker must be disabled"
assert "hint" in empty.group(0), "a hint element is appended in the empty branch"
assert '"No " + row.kind + " entries defined yet' in fn, "hint text must name the kind"
assert "edit enums.yaml to add some." in fn, "hint must point at enums.yaml"

print("PASS  ED11: empty-list kind renders a disabled value <select> + 'edit enums.yaml' hint")
