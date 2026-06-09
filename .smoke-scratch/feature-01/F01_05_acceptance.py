# Pattern: see .smoke-scratch/README.md
"""feature-01 / gherkin-io / Acceptance criteria (AC1-AC4).

AC1 / AC2 / AC3 / AC4 partially restate P-/V-/S-/I- rules with
slightly stronger claims (CRLF survival, byte-identical fixed
point, line > 0, field-name in error).
"""
from app.errors import GherkinParseError, ValidationError
from app.gherkin_io import parse_feature, serialize_feature
from app.models import (
    Background,
    Feature,
    Scenario,
    Step,
    validate_feature,
)


# --- AC1: CRLF + multi-line desc + tags survive one round-trip ------------
hand_written_crlf = (
    "@one @two\r\n"
    "Feature: title\r\n"
    "  body extra line\r\n"
    "\r\n"
    "  Scenario: x\r\n"
    "    Given a step\r\n"
)
feat = parse_feature(hand_written_crlf)
assert feat.tags == ["one", "two"], f"AC1: tags lost, got {feat.tags!r}"
assert feat.description.startswith("title"), f"AC1: description lost name, got {feat.description!r}"
assert "body extra line" in feat.description, f"AC1: description lost body, got {feat.description!r}"
assert len(feat.scenario.steps) == 1 and feat.scenario.steps[0].text == "a step", (
    f"AC1: scenario step lost, got {feat.scenario.steps!r}"
)

out = serialize_feature(feat)
assert "\r" not in out, "AC1: CRLF must not survive serialisation (LF-only output)"

feat2 = parse_feature(out)
assert feat2.tags == feat.tags, f"AC1: tags drifted on re-parse, {feat.tags!r} -> {feat2.tags!r}"
assert feat2.description == feat.description, (
    f"AC1: description drifted on re-parse, {feat.description!r} -> {feat2.description!r}"
)
assert feat2.scenario.steps[0].text == "a step", "AC1: step text drifted on re-parse"
print("PASS  AC1: CRLF + multi-line description + tags survive round-trip")


# --- AC2: serialise chain is a byte-identical fixed point -----------------
src = "Feature: y\n\n  Scenario: s\n    Given alpha\n"
once = serialize_feature(parse_feature(src))
twice = serialize_feature(parse_feature(once))
thrice = serialize_feature(parse_feature(twice))
assert once == twice == thrice, (
    "AC2: serialise chain not a fixed point\n"
    f"once:   {once!r}\ntwice:  {twice!r}\nthrice: {thrice!r}"
)
print("PASS  AC2: serialise chain is a byte-identical fixed point after canonicalisation")


# --- AC3: parser rejections raise GherkinParseError with line > 0 ---------
ac3_cases = [
    ("no Feature:", "Scenario: x\n"),
    (
        "Rule:",
        "Feature: x\n\n  Rule: r\n    Scenario: y\n",
    ),
    (
        "multi-scenario",
        (
            "Feature: x\n\n"
            "  Scenario: a\n    Given s1\n\n"
            "  Scenario: b\n    Given s2\n"
        ),
    ),
]
for label, src in ac3_cases:
    try:
        parse_feature(src)
    except GherkinParseError as e:
        assert e.line > 0, f"AC3[{label}]: line must be > 0, got {e.line}"
    else:
        raise AssertionError(f"AC3[{label}]: must raise GherkinParseError")
print(f"PASS  AC3: parser-rejection cases raise GherkinParseError with line > 0 ({len(ac3_cases)} sub-cases)")


# --- AC4: invalid tag raises ValidationError with the offending field name
f = Feature(
    description="ok",
    tags=["bad tag"],
    background=Background(),
    scenario=Scenario(
        kind="scenario",
        steps=[Step(keyword="Given", text="step")],
    ),
)
try:
    validate_feature(f)
except ValidationError as e:
    assert e.field == "tags[0]", f"AC4: field must name the offending tag index, got {e.field!r}"
else:
    raise AssertionError("AC4: invalid tag must raise ValidationError")
print("PASS  AC4: invalid tag raises ValidationError with the offending field name")
