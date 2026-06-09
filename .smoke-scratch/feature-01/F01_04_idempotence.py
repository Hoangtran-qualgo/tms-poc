# Pattern: see .smoke-scratch/README.md
"""feature-01 / gherkin-io / Idempotence target (I1).

Asserts:  serialize(parse(serialize(parse(x)))) == serialize(parse(x))
The first round-trip may canonicalise; the second must be byte-identical.

Uses a non-trivial hand-written input (multi-line description, tags at
every level, background, outline with multi-row examples) so the
round-trip exercises every serializer branch.
"""
from app.gherkin_io import parse_feature, serialize_feature


HAND_WRITTEN = (
    "@feature_tag @other\n"
    "Feature: title\n"
    "  body line 1\n"
    "  body line 2\n"
    "\n"
    "  Background:\n"
    "    Given background step\n"
    "\n"
    "  @scenario_tag\n"
    "  Scenario Outline: outline name\n"
    "    Given a step with <col_a>\n"
    "    When  another with <col_b>\n"
    "\n"
    "    @examples_tag\n"
    "    Examples: sample\n"
    "      | col_a | col_b |\n"
    "      |  v1   |  v2   |\n"
    "      | empty |       |\n"
)


# --- I1: second round-trip is byte-identical to the first -----------------
once = serialize_feature(parse_feature(HAND_WRITTEN))
twice = serialize_feature(parse_feature(once))
assert once == twice, (
    "I1: second round-trip diverged from the first.\n"
    f"--- once ---\n{once}\n--- twice ---\n{twice}"
)
print("PASS  I1: serialize(parse(serialize(parse(x)))) == serialize(parse(x))")
