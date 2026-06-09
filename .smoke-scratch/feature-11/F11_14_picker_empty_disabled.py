# Pattern: see .smoke-scratch/README.md
"""feature-11 / enums / ED11 -- empty-list kind renders a disabled picker.

ED11: a kind defined in `enums.yaml` but with no entries (e.g.
     `priorities: []`) renders its `<select>` disabled with the hint
     "No <kind> entries defined yet — edit enums.yaml to add some."

Static JS inspection of `tmsEditor._buildEnumPicker` in app/static/app.js.
"""
import re
import pathlib

JS = pathlib.Path("app/static/app.js").read_text()
m = re.search(r"_buildEnumPicker\(kind, entries\)\s*\{.*?\n  \},", JS, re.DOTALL)
assert m, "_buildEnumPicker must be defined"
fn = m.group(0)

# --- ED11: zero-entry branch disables the control + appends the hint. ---
empty = re.search(r"if\s*\(\s*keys\.length === 0\s*\)\s*\{.*?\}\s*else\s*\{", fn, re.DOTALL)
assert empty, "must branch on keys.length === 0"
assert "select.disabled = true" in empty.group(0), "empty-list picker must be disabled"
assert 'hint' in empty.group(0), "a hint element is appended in the empty branch"
assert '"No " + kind + " entries defined yet' in fn, "hint text must name the kind"
assert "edit enums.yaml to add some." in fn, "hint must point at enums.yaml"

print("PASS  ED11: empty-list kind renders a disabled <select> + 'edit enums.yaml' hint")
