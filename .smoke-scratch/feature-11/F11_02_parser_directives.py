"""S1.2 smoke — parse_feature extracts `# enum.<kind>: <key>` directives.

Asserts:
1. Leading directives populate Feature.enums; non-directive comments are ignored.
2. Co-exists with `# language:` (gherkin-official consumes language separately).
3. Comments at/after the first feature-level tag are NOT extracted (cutoff
   = first_tag_line if tags else feature_line).
4. Comments after `Feature:` line are NOT extracted.
5. Duplicate `# enum.<kind>:` raises GherkinParseError on the second line.
6. Malformed kind name (e.g. `# enum.bad-kind: x`) raises GherkinParseError.
7. Malformed key (e.g. `# enum.priority: bad-key`) raises GherkinParseError.
8. Empty key (`# enum.priority:`) raises GherkinParseError.
9. Pre-existing files with no directives parse with enums == {}.
"""
from app.errors import GherkinParseError
from app.gherkin_io import parse_feature


def _parse(src: str):
    return parse_feature(src)


# --- 1. Basic extraction --------------------------------------------------
src = (
    "# enum.component: login_by_SSO\n"
    "# enum.priority: p0\n"
    "# todo: refactor\n"
    "Feature: F\n"
    "  Scenario: s\n"
    "    Given x\n"
)
f = _parse(src)
assert f.enums == {"component": "login_by_SSO", "priority": "p0"}, f.enums
print("PASS  Basic extraction; non-directive comment ignored")

# --- 2. Co-exists with `# language:` --------------------------------------
src = (
    "# language: en\n"
    "# enum.component: login\n"
    "Feature: F\n"
    "  Scenario: s\n"
    "    Given x\n"
)
f = _parse(src)
assert f.enums == {"component": "login"}, f.enums
print("PASS  Co-exists with `# language:` directive")

# --- 3. Cutoff at first tag (directive between tag and Feature: skipped) -
src = (
    "# enum.component: login\n"  # line 1 — before tag, captured
    "@smoke\n"  # line 2 — first tag, cutoff = 2
    "# enum.priority: p0\n"  # line 3 — at/after cutoff, NOT captured
    "Feature: F\n"
    "  Scenario: s\n"
    "    Given x\n"
)
f = _parse(src)
assert f.enums == {"component": "login"}, f.enums
print("PASS  Cutoff at first tag: directive between tag and Feature: skipped")

# --- 4. Directive after Feature: not extracted ----------------------------
src = (
    "Feature: F\n"
    "  # enum.late: bad\n"
    "  Scenario: s\n"
    "    Given x\n"
)
f = _parse(src)
assert f.enums == {}, f.enums
print("PASS  Directive after Feature: not extracted")

# --- 5. Duplicate kind raises --------------------------------------------
src = (
    "# enum.component: a\n"
    "# enum.component: b\n"
    "Feature: F\n"
    "  Scenario: s\n"
    "    Given x\n"
)
try:
    _parse(src)
except GherkinParseError as e:
    assert e.line == 2, e.line
    assert "Duplicate enum directive" in e.message, e.message
else:
    raise AssertionError("duplicate kind should have raised")
print("PASS  Duplicate kind raises GherkinParseError")

# --- 6. Malformed kind name raises ---------------------------------------
src = (
    "# enum.bad-kind: x\n"
    "Feature: F\n"
    "  Scenario: s\n"
    "    Given x\n"
)
try:
    _parse(src)
except GherkinParseError as e:
    assert e.line == 1, e.line
    assert "kind 'bad-kind'" in e.message, e.message
else:
    raise AssertionError("malformed kind should have raised")
print("PASS  Malformed kind name raises GherkinParseError")

# --- 7. Malformed key raises ----------------------------------------------
src = (
    "# enum.priority: bad-key\n"
    "Feature: F\n"
    "  Scenario: s\n"
    "    Given x\n"
)
try:
    _parse(src)
except GherkinParseError as e:
    assert e.line == 1, e.line
    assert "key 'bad-key'" in e.message, e.message
else:
    raise AssertionError("malformed key should have raised")
print("PASS  Malformed key raises GherkinParseError")

# --- 8. Empty key raises --------------------------------------------------
src = (
    "# enum.priority:\n"
    "Feature: F\n"
    "  Scenario: s\n"
    "    Given x\n"
)
try:
    _parse(src)
except GherkinParseError as e:
    assert e.line == 1, e.line
    assert "key ''" in e.message, e.message
else:
    raise AssertionError("empty key should have raised")
print("PASS  Empty key raises GherkinParseError")

# --- 9. Pre-existing files: no directives → enums == {} -------------------
src = (
    "@smoke\n"
    "Feature: F\n"
    "  # plain in-body comment\n"
    "  Scenario: s\n"
    "    Given x\n"
)
f = _parse(src)
assert f.enums == {}, f.enums
print("PASS  Pre-existing files parse with enums == {}")
