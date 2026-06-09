# Pattern: see .smoke-scratch/README.md
"""feature-11 / enums / PR7 -- directives past the cutoff are NOT extracted.

PR7: only comments BEFORE the cutoff line
     (`min(feature.line, first_tag.line)`) are lifted into
     `Feature.enums`. A `# enum.<kind>: <key>` line that lives inside a
     scenario / docstring (well past the cutoff) stays an ordinary
     comment and is discarded by gherkin-official — it never pollutes
     the structured enums map.
"""
from app.gherkin_io import parse_feature


# --- PR7: a directive-looking line INSIDE a docstring is not extracted. ---
src = (
    "# enum.component: login\n"
    "Feature: F\n"
    "  Scenario: s\n"
    "    Given a step with a docstring\n"
    '      """\n'
    "      # enum.priority: p0\n"
    "      not a directive — lives past the cutoff\n"
    '      """\n'
)
f = parse_feature(src)
# Only the leading directive is captured; the docstring-internal one is not.
assert f.enums == {"component": "login"}, f.enums
assert "priority" not in f.enums, f.enums

# --- PR7: a directive-looking comment AFTER the Feature: line is ignored. ---
src2 = (
    "Feature: F\n"
    "  # enum.component: login\n"
    "  Scenario: s\n"
    "    Given x\n"
)
f2 = parse_feature(src2)
assert f2.enums == {}, f2.enums

print("PASS  PR7: enum directives past the cutoff (docstring / below Feature:) are NOT extracted")
