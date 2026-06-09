# Pattern: see .smoke-scratch/README.md
"""feature-11 / enums / PR4 -- duplicate kind directive rejected.

PR4: two `# enum.<kind>: <key>` lines for the SAME kind in the leading
     header block raise GherkinParseError (the directive scan rejects a
     repeated kind rather than silently last-wins).
"""
from app.gherkin_io import parse_feature
from app.errors import GherkinParseError


def _parse(src):
    return parse_feature(src)


# --- PR4: duplicate kind in the leading block raises. ---
src = (
    "# enum.component: login\n"
    "# enum.component: user_base\n"
    "Feature: F\n"
    "  Scenario: s\n"
    "    Given x\n"
)
try:
    _parse(src)
    raise AssertionError("duplicate enum kind must raise GherkinParseError")
except GherkinParseError as e:
    assert e.line == 2, e.line
    assert "Duplicate" in e.message and "component" in e.message, e.message

# --- PR4 control: two DIFFERENT kinds are fine (no false positive). ---
ok = _parse(
    "# enum.component: login\n"
    "# enum.priority: p0\n"
    "Feature: F\n"
    "  Scenario: s\n"
    "    Given x\n"
)
assert ok.enums == {"component": "login", "priority": "p0"}, ok.enums

print("PASS  PR4: duplicate enum kind in the header -> GherkinParseError (distinct kinds still OK)")
