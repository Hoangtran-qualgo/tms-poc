# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / CP3 -- picker live filter + counter copy.

CP3: a live-filter input sits above the table and the counter reads one
     of three forms depending on filter / selection state:
       - "N cases"               (nothing selected, no active filter)
       - "K of N selected"       (selection, no active filter)
       - "K shown - M selected"  (active filter narrowing the set)
     Filtering toggles row visibility without mutating selection.

Static JS inspection of app/static/app.js.
"""
import re
import pathlib

JS = "\n".join(_p.read_text() for _p in sorted(pathlib.Path("app/static").glob("*.js")))
picker = re.search(r"function tmsBuildCasePicker\(features, opts = \{\}\)\s*\{.*?\n\}",
                   JS, re.DOTALL).group(0)

# --- CP3: the filter input + count span exist. ---
assert 'data-role="case-filter"' in picker, "live-filter input must render"
assert 'data-role="case-count"' in picker, "counter span must render"

# --- CP3: a filter listener toggles `hidden` per-row by folder/file match. ---
filt = re.search(r'filterInput\.addEventListener\("input",.*?\}\);', picker, re.DOTALL).group(0)
assert "tr.dataset.folder.includes(q)" in filt and "tr.dataset.file.includes(q)" in filt
assert 'tr.classList.toggle("hidden", !hit)' in filt, "filter must hide non-matching rows"

# --- CP3: the three documented counter formats. ---
assert "${visible.length} cases" in picker
assert "${checked} of ${visible.length} selected" in picker
assert "${shown} shown \u00b7 ${checked} selected" in picker  # \u00b7 = middle dot

print("PASS  CP3: live filter toggles row visibility; counter shows N cases / K of N selected / K shown - M selected")
