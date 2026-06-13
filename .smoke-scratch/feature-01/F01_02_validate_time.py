# Pattern: see .smoke-scratch/README.md
"""feature-01 / gherkin-io / Validate-time invariants (V1-V8).

Builds Feature instances directly so the parser's auto-fixes do
not mask validation failures.
"""
from app.errors import ValidationError
from app.models import (
    Background,
    ExamplesTable,
    Feature,
    Scenario,
    Step,
    validate_feature,
)


def _good() -> Feature:
    """Return a minimally valid Feature; tests mutate one field per case."""
    return Feature(
        description="ok",
        tags=[],
        background=Background(),
        scenario=Scenario(
            kind="scenario",
            name="",
            tags=[],
            steps=[Step(keyword="Given", text="step")],
            examples=[],
        ),
    )


def _expect(f: Feature, field_prefix: str, rule_id: str) -> None:
    try:
        validate_feature(f)
    except ValidationError as e:
        assert e.field.startswith(field_prefix), (
            f"{rule_id}: field {e.field!r} should start with {field_prefix!r}"
        )
        return
    raise AssertionError(f"{rule_id}: expected ValidationError on field starting {field_prefix!r}")


# Sanity: the baseline must validate cleanly.
validate_feature(_good())


# --- V1: empty Feature.description now ACCEPTED (tech-04 D1) ---------------
# The case identity moved to scenario.name, so an empty/whitespace-only
# feature description is legal and must validate cleanly.
f = _good(); f.description = ""
validate_feature(f)
f = _good(); f.description = "   "
validate_feature(f)
print("PASS  V1: empty/whitespace-only Feature.description accepted (tech-04 D1)")


# --- V2: invalid tag values rejected --------------------------------------
bad_tags = [
    ("",          "empty"),
    ("foo bar",   "whitespace"),
    ("\x01tag",   "non-printable"),
    ("foo@bar",   "contains @"),
    ("foo,bar",   "contains ,"),
]
for tag, label in bad_tags:
    f = _good(); f.tags = [tag]
    _expect(f, "tags[0]", f"V2[{label}]")
print(f"PASS  V2: invalid tag values rejected ({len(bad_tags)} sub-cases)")


# --- V3: non-canonical Step.keyword rejected ------------------------------
f = _good()
f.scenario.steps = [Step(keyword="Foo", text="x")]
_expect(f, "scenario.steps[0].keyword", "V3")
print("PASS  V3: non-canonical Step.keyword rejected")


# --- V4: empty or multi-line Step.text rejected ---------------------------
f = _good()
f.scenario.steps = [Step(keyword="Given", text="")]
_expect(f, "scenario.steps[0].text", "V4 (empty)")
f = _good()
f.scenario.steps = [Step(keyword="Given", text="line1\nline2")]
_expect(f, "scenario.steps[0].text", "V4 (multi-line)")
print("PASS  V4: empty or multi-line Step.text rejected")


# --- V5: multi-line Scenario.name rejected; empty allowed -----------------
f = _good(); f.scenario.name = "line1\nline2"
_expect(f, "scenario.name", "V5")
f = _good(); f.scenario.name = ""
validate_feature(f)
print("PASS  V5: multi-line Scenario.name rejected; empty name allowed")


# --- V6: outline with no examples rejected --------------------------------
f = _good()
f.scenario.kind = "outline"
f.scenario.examples = []
_expect(f, "scenario.examples", "V6")
print("PASS  V6: outline with len(examples) < 1 rejected")


# --- V7: plain scenario with examples rejected ----------------------------
f = _good()
f.scenario.kind = "scenario"
f.scenario.examples = [ExamplesTable(header=["a"], rows=[["1"]])]
_expect(f, "scenario.examples", "V7")
print("PASS  V7: plain scenario with non-empty examples rejected")


# --- V8: empty examples header / row-width mismatch rejected --------------
f = _good()
f.scenario.kind = "outline"
f.scenario.examples = [ExamplesTable(header=[], rows=[])]
_expect(f, "scenario.examples[0].header", "V8 (empty header)")

f = _good()
f.scenario.kind = "outline"
f.scenario.examples = [ExamplesTable(header=["a", "b"], rows=[["1"]])]
_expect(f, "scenario.examples[0].rows[0]", "V8 (row width)")
print("PASS  V8: empty examples header and row-width mismatch rejected")
