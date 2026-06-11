"""S1.1 smoke — Feature.enums field + to_dict/from_dict + validation.

Asserts:
1. Default is an empty dict.
2. to_dict carries the field; from_dict round-trips it.
3. validate_feature accepts empty dict + empty-string values.
4. validate_feature rejects an invalid kind name with field='enums'.
5. validate_feature rejects an invalid key with field='enums[<kind>]'.
"""
from app.errors import ValidationError
from app.models import (
    ENUM_IDENTIFIER_RE,
    ENUM_KEY_RE,
    Feature,
    Scenario,
    Step,
    validate_feature,
)


def _ok_feature(**enums):
    return Feature(
        description="Smoke",
        scenario=Scenario(
            kind="scenario",
            name="s",
            steps=[Step(keyword="Given", text="x")],
        ),
        enums=dict(enums),
    )


# --- 1. Default ------------------------------------------------------------
f = Feature()
assert f.enums == {}, f.enums
print("PASS  Feature().enums defaults to {}")

# --- 2. to_dict / from_dict round-trip ------------------------------------
f = _ok_feature(components="login_by_SSO", priorities="p0")
d = f.to_dict()
assert d["enums"] == {"components": "login_by_SSO", "priorities": "p0"}, d["enums"]
f2 = Feature.from_dict(d)
assert f2.enums == f.enums, (f2.enums, f.enums)
print("PASS  to_dict/from_dict round-trip preserves enums")

# from_dict tolerates missing/None enums for legacy payloads
assert Feature.from_dict({"description": "x"}).enums == {}
assert Feature.from_dict({"enums": None}).enums == {}
print("PASS  from_dict tolerates missing/None enums")

# --- 3. validate accepts empty + empty-string unset -----------------------
validate_feature(_ok_feature())  # empty dict
validate_feature(_ok_feature(components=""))  # unset is legal
validate_feature(_ok_feature(components="login", priorities=""))
print("PASS  validate_feature accepts empty enums and empty-string values")

# --- 4. validate rejects invalid kind name --------------------------------
for bad_kind in ["1priorities", "has-dash", "has space", "", "with.dot"]:
    f_bad = _ok_feature()
    f_bad.enums[bad_kind] = "x"
    try:
        validate_feature(f_bad)
    except ValidationError as e:
        assert e.field == "enums", (bad_kind, e.field)
        assert "Invalid enum kind" in e.message, (bad_kind, e.message)
    else:
        raise AssertionError(f"bad kind {bad_kind!r} should have been rejected")
print("PASS  validate_feature rejects invalid kind names")

# --- 5. validate rejects invalid key value --------------------------------
# NB: a dash is now legal in keys (see section 6) — only a leading digit,
# whitespace, dot, or symbol remain invalid.
for bad_key in ["1leading", "has space", "with.dot", "x@y"]:
    try:
        validate_feature(_ok_feature(components=bad_key))
    except ValidationError as e:
        assert e.field == "enums[components]", e.field
        assert "Invalid enum key" in e.message, e.message
    else:
        raise AssertionError(f"bad key {bad_key!r} should have been rejected")
print("PASS  validate_feature rejects invalid enum key values")

# --- 6. validate accepts a dashed key (knowledge-base); kinds stay strict -
validate_feature(_ok_feature(components="knowledge-base"))
f_bad = _ok_feature()
f_bad.enums["has-dash"] = "login"  # dash in a KIND is still rejected
try:
    validate_feature(f_bad)
except ValidationError as e:
    assert e.field == "enums" and "Invalid enum kind" in e.message, e.message
else:
    raise AssertionError("a dashed kind name must still be rejected")
print("PASS  validate_feature accepts dashed keys but still rejects dashed kinds")

# Sanity check the exported regexes
assert ENUM_IDENTIFIER_RE.fullmatch("login_by_SSO")
assert ENUM_IDENTIFIER_RE.fullmatch("_x9")
assert not ENUM_IDENTIFIER_RE.fullmatch("9x")
assert not ENUM_IDENTIFIER_RE.fullmatch("has-dash"), "kinds must not allow a dash"
assert ENUM_KEY_RE.fullmatch("knowledge-base")
assert ENUM_KEY_RE.fullmatch("_x9")
assert not ENUM_KEY_RE.fullmatch("9x"), "keys must still reject a leading digit"
assert not ENUM_KEY_RE.fullmatch("has space"), "keys must still reject whitespace"
print("PASS  ENUM_IDENTIFIER_RE (kinds, no dash) + ENUM_KEY_RE (keys, dash ok)")
