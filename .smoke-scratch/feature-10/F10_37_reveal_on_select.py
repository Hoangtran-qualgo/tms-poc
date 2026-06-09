"""Smoke 7c: reveal-on-select branch is keyed on the `__new__` value.

When the user picks `+ Create new group...` the modal reveals an inline
sub-form (project select + group name input). Sanity-check that the JS
toggles a hidden container based on the `__new__` sentinel and that the
sub-form references both expected inputs.
"""
import re, pathlib

APP_JS = pathlib.Path("app/static/app.js").read_text()

# The reveal helper must compare `whereSel.value` against `"__new__"`.
assert re.search(
    r"whereSel\.value\s*===\s*\"__new__\"", APP_JS
), "missing __new__ comparison on whereSel.value"
print("PASS  reveal-on-select branch comparator is whereSel.value === '__new__'")

# The hidden container has id `tms-cr-newgroup` and the JS toggles its
# `hidden` class via classList.toggle.
assert 'id="tms-cr-newgroup"' in APP_JS, "missing #tms-cr-newgroup container"
assert "newGroupBlock.classList.toggle" in APP_JS, (
    "missing classList.toggle on the new-group sub-form"
)
print("PASS  sub-form container is #tms-cr-newgroup and toggled via classList")

# The sub-form must include both a project <select> and a group name input.
assert 'id="tms-cr-newproj"' in APP_JS, "missing #tms-cr-newproj (project select)"
assert 'id="tms-cr-newgrp"' in APP_JS, "missing #tms-cr-newgrp (group name input)"
print("PASS  sub-form contains project <select> + group name input")
