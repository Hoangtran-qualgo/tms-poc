# Pattern: see .smoke-scratch/README.md
"""feature-11 / enums / ED12 -- value picker options: not-set + key/label split.

ED12: each row's value `<select>` leads with a `— not set —` option whose
     value is the empty string (the default when the row has no value yet),
     followed by one `<option value="<key>">` per entry whose visible text
     is the **label** — so the editor submits the key while the user sees
     the label. The stored key is pre-selected.

tech-04 D5 moved this onto the per-row value `<select>` built by
`tmsEditor._buildEnumRow` (the row's selected value is `row.value`).
"""
import re
import pathlib

JS = "\n".join(_p.read_text() for _p in sorted(pathlib.Path("app/static").glob("*.js")))
m = re.search(r"_buildEnumRow\(row, vocab\)\s*\{.*?\n  \},", JS, re.DOTALL)
assert m, "_buildEnumRow must be defined"
fn = m.group(0)

# --- ED12: leading `— not set —` option with empty value, default-selected. ---
assert "valNone.value = \"\"" in fn, "the leading value option's value must be the empty string"
assert "\\u2014 not set \\u2014" in fn or "— not set —" in fn, "leading option text '— not set —'"
assert re.search(r"if\s*\(\s*!row\.value\s*\)\s*valNone\.selected = true", fn), (
    "the not-set option is selected when the row has no value"
)

# --- ED12: per-entry options carry value=<key>, text=<label>, key pre-selected. ---
assert "opt.value = key" in fn, "option value must be the key (submitted on save)"
assert "opt.textContent = entries[key]" in fn, "option text must be the label (displayed)"
assert re.search(r"if\s*\(\s*key === row\.value\s*\)\s*opt\.selected = true", fn), (
    "the stored key must be pre-selected"
)

print("PASS  ED12: value picker leads with empty-value '— not set —'; options submit key, display label; stored key pre-selected")
