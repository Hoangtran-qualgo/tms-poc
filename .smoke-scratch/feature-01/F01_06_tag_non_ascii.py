# Pattern: see .smoke-scratch/README.md
"""feature-01 / gherkin-io / tag char range — cp > 0x7E leg (condition-coverage gap-closer).

`models._is_valid_tag` rejects any character outside ASCII-printable:

    if cp < 0x21 or cp > 0x7E:
        return False

The existing tag tests drive the `cp < 0x21` leg (space / control) and
the `@`/`,` exclusions, but never the `cp > 0x7E` leg (a non-ASCII
character), leaving that condition's True outcome untested
(condition-coverage gap "Pattern C"). This pins both the unit-level
predicate and the public `validate_feature` rejection.
"""
from app.errors import ValidationError
from app.models import Feature, _is_valid_tag, validate_feature

# --- Unit: each leg of the char-range decision independently. ---
assert _is_valid_tag("café") is False, "cp > 0x7E (é) must reject the tag"
assert _is_valid_tag("naïve") is False, "cp > 0x7E (ï) must reject the tag"
assert _is_valid_tag("a b") is False, "cp < 0x21 (space) must reject the tag"
assert _is_valid_tag("smoke") is True, "all-ASCII-printable tag must be valid"

# --- Public: a non-ASCII scenario tag is rejected by validate_feature. ---
feat = Feature.from_dict(
    {
        "description": "desc",
        "tags": [],
        "background": {"steps": []},
        "scenario": {
            "kind": "scenario",
            "name": "S",
            "tags": ["café"],
            "steps": [{"keyword": "Given", "text": "a step"}],
            "examples": [],
        },
        "enums": {},
    }
)
try:
    validate_feature(feat)
    raise AssertionError("a non-ASCII scenario tag must raise ValidationError")
except ValidationError as e:
    assert e.field == "scenario.tags[0]", e.field
    assert "Invalid tag value" in e.message, e.message

print("PASS  Pattern C: non-ASCII tag char (cp > 0x7E) rejected by _is_valid_tag + validate_feature")
