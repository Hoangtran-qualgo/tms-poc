# Pattern: see .smoke-scratch/README.md
"""feature-14 / import test cases / Phase 1 splitter (split_feature_source).

Pure-model smoke: exercises app.gherkin_io.split_feature_source directly.
Covers DO-1 CHECK scope: single scenario, N scenarios, outline survival,
shared Background, shared description / blank-when-synthesized, feature tags
shared + scenario tags kept per-case, Rule rejected, missing-Feature header
synthesis (blank description), header-but-no-Scenario -> [], enums dropped,
plus deep-copy independence of shared Background and corrected error line.
"""
from app.errors import GherkinParseError
from app.gherkin_io import split_feature_source


# --- S1: single scenario -> exactly one Feature ---------------------------
feats = split_feature_source("Feature: f\n\n  Scenario: a\n    Given x\n")
assert len(feats) == 1, f"S1: expected 1 feature, got {len(feats)}"
assert feats[0].scenario.name == "a", f"S1: scenario name, got {feats[0].scenario.name!r}"
assert feats[0].description == "f", f"S1: description, got {feats[0].description!r}"
print("PASS  S1: single-scenario source yields one Feature")


# --- S2: N scenarios -> one Feature each, document order ------------------
src = (
    "Feature: multi\n\n"
    "  Scenario: a\n    Given a1\n\n"
    "  Scenario: b\n    Given b1\n\n"
    "  Scenario: c\n    Given c1\n"
)
feats = split_feature_source(src)
assert [f.scenario.name for f in feats] == ["a", "b", "c"], (
    f"S2: expected [a,b,c] in order, got {[f.scenario.name for f in feats]!r}"
)
print("PASS  S2: N scenarios split into one Feature each, in document order")


# --- S3: scenario outline survives (kind, examples, tables) ---------------
src = (
    "Feature: f\n\n"
    "  Scenario Outline: o\n    Given <col>\n\n"
    "    Examples:\n"
    "      | col |\n"
    "      | v1  |\n"
    "      | v2  |\n"
)
feats = split_feature_source(src)
assert len(feats) == 1, f"S3: expected 1, got {len(feats)}"
sc = feats[0].scenario
assert sc.kind == "outline", f"S3: kind must be outline, got {sc.kind!r}"
assert sc.examples and sc.examples[0].rows == [["v1"], ["v2"]], (
    f"S3: examples rows lost, got {sc.examples and sc.examples[0].rows!r}"
)
print("PASS  S3: scenario outline kind + examples survive the split")


# --- S4: shared Background copied onto every case, independent objects -----
src = (
    "Feature: f\n\n"
    "  Background:\n    Given shared setup\n\n"
    "  Scenario: a\n    Given a1\n\n"
    "  Scenario: b\n    Given b1\n"
)
feats = split_feature_source(src)
assert len(feats) == 2, f"S4: expected 2, got {len(feats)}"
for f in feats:
    texts = [s.text for s in f.background.steps]
    assert texts == ["shared setup"], f"S4: background not shared, got {texts!r}"
# Deep-copy independence: mutating one case's background must not touch the other.
feats[0].background.steps[0].text = "MUTATED"
assert feats[1].background.steps[0].text == "shared setup", (
    "S4: shared Background steps are aliased between cases (must be independent)"
)
print("PASS  S4: Background shared onto every case as independent copies")


# --- S5: feature description shared across all cases -----------------------
src = (
    "Feature: shared title\n  body line\n\n"
    "  Scenario: a\n    Given a1\n\n"
    "  Scenario: b\n    Given b1\n"
)
feats = split_feature_source(src)
assert all(f.description.startswith("shared title") for f in feats), (
    f"S5: description not shared, got {[f.description for f in feats]!r}"
)
assert all("body line" in f.description for f in feats), "S5: body line lost"
print("PASS  S5: feature description shared across all split cases")


# --- S6: feature tags shared; scenario tags kept per-case ------------------
src = (
    "@feat1 @feat2\n"
    "Feature: f\n\n"
    "  @only_a\n"
    "  Scenario: a\n    Given a1\n\n"
    "  @only_b\n"
    "  Scenario: b\n    Given b1\n"
)
feats = split_feature_source(src)
assert all(f.tags == ["feat1", "feat2"] for f in feats), (
    f"S6: feature tags not shared, got {[f.tags for f in feats]!r}"
)
assert feats[0].scenario.tags == ["only_a"], f"S6: case a tags, got {feats[0].scenario.tags!r}"
assert feats[1].scenario.tags == ["only_b"], f"S6: case b tags, got {feats[1].scenario.tags!r}"
print("PASS  S6: feature tags shared; scenario tags kept per-case (not mixed)")


# --- S7: Rule: block rejected (same as parse_feature) ----------------------
try:
    split_feature_source("Feature: f\n\n  Rule: r\n    Scenario: y\n    Given x\n")
except GherkinParseError as e:
    assert "Rule" in e.message, f"S7: message must mention Rule, got {e.message!r}"
else:
    raise AssertionError("S7: 'Rule:' block must raise GherkinParseError")
print("PASS  S7: 'Rule:' block raises GherkinParseError")


# --- S8: missing Feature: header -> synthesized, blank description ----------
src = (
    "  Scenario: a\n    Given a1\n\n"
    "  Scenario: b\n    Given b1\n"
)
feats = split_feature_source(src)
assert len(feats) == 2, f"S8: expected 2 after header synthesis, got {len(feats)}"
assert all(f.description == "" for f in feats), (
    f"S8: synthesized header must give blank description, got {[f.description for f in feats]!r}"
)
assert [f.scenario.name for f in feats] == ["a", "b"], "S8: scenarios lost after synthesis"
print("PASS  S8: missing 'Feature:' header synthesized with blank description")


# --- S8b: header synthesis still skips leading tags / comments -------------
src = (
    "# enum.priority: high\n"
    "@toplevel\n"
    "  Scenario: a\n    Given a1\n"
)
feats = split_feature_source(src)
assert len(feats) == 1, f"S8b: expected 1, got {len(feats)}"
assert feats[0].description == "", "S8b: must synthesize blank description past tags/comments"
assert feats[0].scenario.tags == ["toplevel"], (
    f"S8b: leading tag should attach to the scenario, got {feats[0].scenario.tags!r}"
)
print("PASS  S8b: pre-scan skips leading comments/tags before synthesizing header")


# --- S9: header but zero scenarios -> [] -----------------------------------
assert split_feature_source("Feature: f\n") == [], "S9: header-only must return []"
assert split_feature_source("Feature: f\n\n  Background:\n    Given setup\n") == [], (
    "S9: Feature + Background but no Scenario must return []"
)
print("PASS  S9: header with zero scenarios returns []")


# --- S10: enums always dropped --------------------------------------------
src = (
    "# enum.priority: high\n"
    "Feature: f\n\n"
    "  Scenario: a\n    Given a1\n\n"
    "  Scenario: b\n    Given b1\n"
)
feats = split_feature_source(src)
assert all(f.enums == {} for f in feats), (
    f"S10: enums must be dropped, got {[f.enums for f in feats]!r}"
)
print("PASS  S10: enum directives always dropped from split cases")


# --- S11: parse error on a real syntax error still raises (not masked) -----
try:
    split_feature_source("Feature: f\n\n  Scenario: a\n    Given x\n  Rule\n")
except GherkinParseError:
    pass
else:
    raise AssertionError("S11: a genuine syntax error must still raise")
print("PASS  S11: genuine syntax errors are not masked by header pre-scan")


# --- S12: empty / whitespace / comment-only sources -> [] ------------------
for blank in ("", "   ", "\n\n", "# just a comment\n"):
    assert split_feature_source(blank) == [], f"S12: {blank!r} must return []"
print("PASS  S12: empty/whitespace/comment-only sources return []")


# --- S13: CRLF normalized like parse_feature ------------------------------
feats = split_feature_source("Feature: f\r\n\r\n  Scenario: a\r\n    Given x\r\n")
assert len(feats) == 1 and feats[0].scenario.name == "a", "S13: CRLF source not normalised"
print("PASS  S13: CRLF source normalised before split")
