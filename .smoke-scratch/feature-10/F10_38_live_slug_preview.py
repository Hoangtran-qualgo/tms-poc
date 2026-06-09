"""Smoke 7d: live slug preview wired under the run-name input.

Q3 decision: render `will save as <slug>.yaml` reactively as the user
types. Verifies (a) a preview node exists, (b) `updateSlugPreview`
listens on the run-name `input` event, and (c) the visible text uses
the existing `tmsSlugifyForFilename` helper.
"""
import re, pathlib

APP_JS = pathlib.Path("app/static/app.js").read_text()

# Preview node with the expected data-role.
assert 'data-role="slug-preview"' in APP_JS, "missing data-role='slug-preview' node"
print("PASS  slug-preview node present in modal body")

# `updateSlugPreview` is the callback wired to the run-name input.
assert "updateSlugPreview" in APP_JS, "missing updateSlugPreview helper"
assert re.search(
    r"nameInput\.addEventListener\(\s*\"input\"\s*,\s*updateSlugPreview\s*\)",
    APP_JS,
), "nameInput input event should call updateSlugPreview"
print("PASS  run-name input is wired to updateSlugPreview")

# The preview uses tmsSlugifyForFilename and renders the .yaml suffix.
assert "tmsSlugifyForFilename(nameInput.value)" in APP_JS, (
    "preview should slug via tmsSlugifyForFilename"
)
assert "will save as" in APP_JS, "preview text should read 'will save as ...'"
print("PASS  preview renders `will save as <slug>.yaml` via tmsSlugifyForFilename")
