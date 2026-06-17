"""Run editor JS: the result summary is recomputed live from the DOM.

Pins the live-update half of the "result summary below the description" item:
_updateResultSummary counts the live .run-result-select values (not stale
server data), hides zero-count chips, toggles the empty em-dash, and is wired
into _refreshDirty so result-select changes / add / remove all refresh it.
Static-wiring (source grep) only — no JS runtime.
"""
import pathlib
import re

JS = pathlib.Path("app/static/06_run_editor.js").read_text()

assert "_updateResultSummary" in JS, "must define _updateResultSummary"

# Counts the LIVE result selects in the table (not a stale server snapshot).
assert re.search(
    r'querySelectorAll\(\s*\n?\s*"#run-results tbody tr\[data-file-path\] '
    r'\.run-result-select"',
    JS,
), "must count live .run-result-select values"
print("PASS _updateResultSummary counts live result selects")

# Hides zero-count chips + toggles the empty em-dash.
assert 'classList.toggle("hidden", n === 0)' in JS, "zero-count chips must hide"
assert "run-summary-empty" in JS, "must toggle the empty em-dash placeholder"
print("PASS zero-count chips hidden; empty em-dash toggled")

# Wired into the universal change hook so every mutation refreshes the summary.
assert re.search(
    r"_refreshDirty\(\)\s*\{[\s\S]*?_updateResultSummary\(\)[\s\S]*?\n  \},",
    JS,
), "_updateResultSummary must be called from _refreshDirty"
print("PASS _updateResultSummary wired into _refreshDirty")
