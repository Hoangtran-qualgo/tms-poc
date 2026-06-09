"""Smoke 7a: `tmsCreateRun` is exported as a no-arg async function.

The Phase-3 contract was `tmsCreateRun(project, group)`; the rewrite
drops both params because the sidebar caller lives outside any project
context. Sanity-check the signature in app.js so the sidebar template
keeps matching it.
"""
import re, pathlib

APP_JS = pathlib.Path("app/static/app.js").read_text()

# Match exactly: `async function tmsCreateRun() {`. The empty parens
# guard against accidental future re-parameterisation.
m = re.search(r"async function tmsCreateRun\(\s*\)\s*\{", APP_JS)
assert m, "tmsCreateRun should be `async function tmsCreateRun()` (no args)"
print("PASS  tmsCreateRun is async + no-arg")
