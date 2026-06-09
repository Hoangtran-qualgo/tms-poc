"""3.E — tmsRunEditor exposes Add-case / Remove-row wiring.

End-to-end clicks need a browser; this verifies the controller's
new methods exist and are tied to the template's hooks."""
import pathlib

APP_JS = pathlib.Path("app/static/app.js").read_text()
TPL = pathlib.Path("app/templates/run_editor.html").read_text()

# Controller methods + the picker reuse.
for sym in [
    "_onAddCaseClicked()",
    "_createResultRow(",
    "_afterRowsChanged()",
]:
    assert sym in APP_JS, f"missing JS method: {sym}"

# Toolbar wiring of the + Add test case button.
assert 'getElementById("btn-run-add-case")' in APP_JS, "+ Add test case button not wired"
print("PASS 3.E controller methods + button wired")

# Per-row remove is delegated on the tbody (matches .run-row-remove).
assert 'e.target.matches(".run-row-remove")' in APP_JS, "remove delegation missing"
# Same delegation pattern for remark + select changes (so dynamically
# added rows are dirty-tracked without per-row hookup).
assert 'e.target.matches(".run-remark")' in APP_JS, "remark delegation missing"
assert 'e.target.matches(".run-result-select")' in APP_JS, "select delegation missing"
print("PASS 3.E remove + dirty tracking use event delegation")

# Add-case modal reuses tmsBuildCasePicker with the picker's exclude option.
assert "tmsBuildCasePicker(features, {" in APP_JS, "picker reuse missing"
assert "exclude: existing" in APP_JS, "exclude set wiring missing"
print("PASS 3.E + Add test case modal reuses tmsBuildCasePicker with exclude set")

# New rows go through htmx.process so their hx-get link works.
assert "htmx.process(tbody)" in APP_JS, "htmx.process call missing"
print("PASS 3.E newly-cloned rows are passed through htmx.process")

# Template carries the row prototype.
assert 'id="run-result-row-template"' in TPL, "row template missing"
print("PASS 3.E template exposes <template id=run-result-row-template>")
