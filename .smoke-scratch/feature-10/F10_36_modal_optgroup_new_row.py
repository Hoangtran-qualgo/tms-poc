"""Smoke 7b: modal renders `<optgroup>` per project + `+ Create new group...` row.

The agreed dropdown shape (Q1 + Q2): one `<optgroup label="proj">` per
existing project that has groups, with each group as a child `<option>`,
and a trailing non-grouped `+ Create new group...` option. Verifies the
JS issues the right DOM-construction calls; visual rendering still needs
a browser smoke.
"""
import pathlib

APP_JS = "\n".join(_p.read_text() for _p in sorted(pathlib.Path("app/static").glob("*.js")))

# `<optgroup>` is created via document.createElement and labelled with the
# project name; one of the assertions should reference both.
assert 'createElement("optgroup")' in APP_JS, "missing createElement('optgroup')"
assert "og.label = proj" in APP_JS, "optgroup label should be the project name"
print("PASS  one <optgroup> per project, labelled by project name")

# Each row is an <option> whose value encodes 'proj|grp' so the submit
# handler can split it back.
assert 'opt.value = proj + "|" + grp' in APP_JS, "missing proj|grp option value"
print("PASS  group rows use 'proj|grp' option values")

# The trailing `+ Create new group...` row must be present with the
# sentinel value `__new__`.
assert '"+ Create new group' in APP_JS, "missing '+ Create new group' label"
assert 'newOpt.value = "__new__"' in APP_JS, "missing __new__ sentinel value"
print("PASS  trailing '+ Create new group...' row uses __new__ sentinel")
