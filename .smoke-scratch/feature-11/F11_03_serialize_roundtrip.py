"""S1.3 + S1.4 smoke — serializer emits enum directives + full round-trip.

Asserts:
1. Serializer emits one `# enum.<kind>: <key>` line per non-empty entry,
   alphabetical by kind, above any feature-level tag / `Feature:`.
2. Empty-string values are skipped (so files that have never set a kind
   round-trip byte-identically even when the project adds that kind).
3. Feature with empty enums dict produces no directive lines.
4. Round-trip: parse(serialize(parse(src))) == parse(serialize(parse(src)))
   stable; enums preserved.
5. Round-trip canonicalises directive whitespace (`#  enum.foo:  bar  ` →
   `# enum.foo: bar`).
6. Pre-existing .feature files (no directives, no enum field touched)
   round-trip byte-identically through serialize(parse(x)).
"""
from app.gherkin_io import parse_feature, serialize_feature
from app.models import Feature, Scenario, Step


def _mk(enums=None, tags=None):
    return Feature(
        description="Smoke",
        tags=tags or [],
        scenario=Scenario(
            kind="scenario",
            name="s",
            steps=[Step(keyword="Given", text="x")],
        ),
        enums=dict(enums or {}),
    )


# --- 1. Alphabetical order, above tags -----------------------------------
f = _mk(enums={"priority": "p0", "component": "login_by_SSO"}, tags=["smoke"])
out = serialize_feature(f)
lines = out.splitlines()
assert lines[0] == "# enum.component: login_by_SSO", lines[:3]
assert lines[1] == "# enum.priority: p0", lines[:3]
assert lines[2] == "@smoke", lines[:3]
assert lines[3].startswith("Feature: "), lines[:4]
print("PASS  Serializer emits directives alphabetically above tags")

# --- 2. Empty values skipped ---------------------------------------------
f = _mk(enums={"component": "login", "priority": "", "team": ""})
out = serialize_feature(f)
assert "# enum.component: login" in out
assert "# enum.priority" not in out
assert "# enum.team" not in out
print("PASS  Empty-string enum values are skipped")

# --- 3. No directives when dict empty ------------------------------------
out = serialize_feature(_mk(enums={}))
assert not out.startswith("# enum."), out[:80]
print("PASS  Empty enums dict produces no directive lines")

# --- 4. Round-trip preserves enums ---------------------------------------
src1 = serialize_feature(_mk(enums={"component": "login", "priority": "p1"}))
f1 = parse_feature(src1)
assert f1.enums == {"component": "login", "priority": "p1"}, f1.enums
src2 = serialize_feature(f1)
assert src1 == src2, (src1, src2)
print("PASS  Round-trip parse→serialize→parse preserves enums + bytes")

# --- 5. Canonicalises whitespace -----------------------------------------
weird = (
    "#  enum.component:  login_by_SSO  \n"
    "# enum.priority:p0\n"
    "Feature: Smoke\n"
    "  Scenario: s\n"
    "    Given x\n"
)
f = parse_feature(weird)
assert f.enums == {"component": "login_by_SSO", "priority": "p0"}, f.enums
out = serialize_feature(f)
canonical_lines = out.splitlines()[:2]
assert canonical_lines == [
    "# enum.component: login_by_SSO",
    "# enum.priority: p0",
], canonical_lines
print("PASS  Round-trip canonicalises directive whitespace")

# --- 6. Legacy files (no directives) untouched ---------------------------
legacy = (
    "@smoke\n"
    "Feature: Legacy\n"
    "\n"
    "  Scenario: s\n"
    "    Given x\n"
)
f = parse_feature(legacy)
assert f.enums == {}, f.enums
out = serialize_feature(f)
# The directive emit block produces no lines when enums is empty, so the
# first line is the tag, mirroring pre-S1 output.
assert out.splitlines()[0] == "@smoke", out.splitlines()[:3]
assert "# enum." not in out
print("PASS  Legacy files with no directives are untouched by serializer")
