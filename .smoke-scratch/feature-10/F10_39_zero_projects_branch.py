"""Smoke 7e: zero-projects branch renders an info modal with no Confirm.

Q6 decision: when `/api/run-groups` returns `projects: []`, open the
modal with a single message and a Cancel-only footer. Verifies the JS
guards on `projects.length === 0`, renders the documented message, and
invokes `tmsOpenModal` with `confirmLabel: null` (the helper extension
that suppresses the Confirm button).
"""
import re, pathlib

APP_JS = "\n".join(_p.read_text() for _p in sorted(pathlib.Path("app/static").glob("*.js")))

# Guard on the empty-projects shape.
assert re.search(
    r"projects\.length\s*===\s*0", APP_JS
), "missing `projects.length === 0` guard"
print("PASS  zero-projects branch keyed on projects.length === 0")

# The documented copy is surfaced verbatim.
assert "No projects yet" in APP_JS, "missing 'No projects yet' copy"
print("PASS  branch renders 'No projects yet — create one first.' copy")

# Confirm button is suppressed via confirmLabel: null (the tmsOpenModal
# extension introduced for information-only modals).
assert re.search(
    r"confirmLabel\s*:\s*null", APP_JS
), "missing `confirmLabel: null` for the info-only modal"
print("PASS  branch passes confirmLabel: null so Confirm is not rendered")
