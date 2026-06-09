# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / CP6 -- picker empty states.

CP6: when nothing is selectable the picker replaces the whole <table>
     with an empty-state message:
       - "No .feature files in this project yet." when the project has
         no features at all;
       - "All test cases are already in this run." when every feature
         is in the exclude set.
     The empty-state path leaves headerBox null so no select-all
     checkbox is rendered and the header-state helpers short-circuit.

Static JS inspection of app/static/app.js.
"""
import re
import pathlib

JS = pathlib.Path("app/static/app.js").read_text()
picker = re.search(r"function tmsBuildCasePicker\(features, opts = \{\}\)\s*\{.*?\n\}",
                   JS, re.DOTALL).group(0)

# --- CP6: empty-state branch keyed on no visible rows. ---
assert re.search(r"if\s*\(\s*visible\.length === 0\s*\)", picker), "empty-state branch must exist"

# --- CP6: the two distinct messages, chosen by features.length. ---
assert "No .feature files in this project yet." in picker
assert "All test cases are already in this run." in picker
assert "features.length === 0" in picker, "message choice must branch on total feature count"

# --- CP6: the empty state replaces the table content. ---
assert 'scroll.innerHTML = "";' in picker, "empty state must replace the <table>"

# --- CP6: select-all is wired only when a real header exists. ---
assert "let headerBox = null;" in picker
assert re.search(r"if\s*\(\s*headerBox\s*\)\s*\{\s*\n\s*headerBox\.addEventListener", picker), (
    "the select-all listener must be guarded so empty states render no header checkbox"
)

print("PASS  CP6: empty picker replaces the table with the right message; no select-all header in empty state")
