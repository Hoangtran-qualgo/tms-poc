# Pattern: see .smoke-scratch/README.md
"""feature-01 / gherkin-io / Parse-time invariants (P1-P9)."""
from app.errors import GherkinParseError
from app.gherkin_io import parse_feature


# --- P1: \r\n and lone \r -> \n before parsing ----------------------------
feat = parse_feature("Feature: hello\r\n\r\n  Scenario: x\r\n")
assert feat.description == "hello", f"P1: CRLF source not normalised, got {feat.description!r}"
feat = parse_feature("Feature: world\r\r  Scenario: x\r")
assert feat.description == "world", f"P1: lone-CR source not normalised, got {feat.description!r}"
print("PASS  P1: CRLF and lone CR normalised to LF before parsing")


# --- P2: missing `Feature:` header -> GherkinParseError -------------------
try:
    parse_feature("Scenario: x\n")
except GherkinParseError as e:
    assert e.line > 0, f"P2: error line must be > 0, got {e.line}"
    assert "Feature" in e.message, f"P2: message must mention 'Feature', got {e.message!r}"
else:
    raise AssertionError("P2: missing Feature: header must raise GherkinParseError")
print("PASS  P2: file without 'Feature:' header raises GherkinParseError")


# --- P3: `Rule:` block -> GherkinParseError -------------------------------
src = "Feature: x\n\n  Rule: r\n    Scenario: y\n"
try:
    parse_feature(src)
except GherkinParseError as e:
    assert "Rule" in e.message, f"P3: message must mention 'Rule', got {e.message!r}"
else:
    raise AssertionError("P3: 'Rule:' block must raise GherkinParseError")
print("PASS  P3: 'Rule:' block raises GherkinParseError")


# --- P4: more than one scenario -> GherkinParseError ----------------------
src = (
    "Feature: x\n\n"
    "  Scenario: a\n    Given step1\n\n"
    "  Scenario: b\n    Given step2\n"
)
try:
    parse_feature(src)
except GherkinParseError as e:
    assert "scenario" in e.message.lower(), f"P4: message must mention 'scenario', got {e.message!r}"
else:
    raise AssertionError("P4: multi-scenario file must raise GherkinParseError")
print("PASS  P4: multi-scenario file raises GherkinParseError")


# --- P5: zero-scenario file auto-fixed with placeholder -------------------
feat = parse_feature("Feature: solo\n")
assert feat.scenario.kind == "scenario", f"P5: placeholder kind, got {feat.scenario.kind!r}"
assert feat.scenario.name == "", f"P5: placeholder name, got {feat.scenario.name!r}"
assert feat.scenario.steps == [], f"P5: placeholder steps, got {feat.scenario.steps!r}"
print("PASS  P5: zero-scenario file auto-fixed with placeholder Scenario")


# --- P6: description decoding ---------------------------------------------
feat = parse_feature("Feature: line1\\nline2\n\n  Scenario: x\n")
assert feat.description == "line1\nline2", (
    f"P6 (literal-\\n decode): expected 'line1\\nline2', got {feat.description!r}"
)
feat = parse_feature("Feature: title\n  body line\n\n  Scenario: x\n")
assert feat.description.startswith("title"), f"P6: must start with name, got {feat.description!r}"
assert "body line" in feat.description, f"P6: description missing body, got {feat.description!r}"
print("PASS  P6: description decodes literal \\n and concatenates multi-line body")


# --- P7a: tag parser strips leading `@` -----------------------------------
feat = parse_feature("@foo @bar\nFeature: x\n\n  Scenario: y\n")
assert feat.tags == ["foo", "bar"], f"P7a: leading @ must be stripped, got {feat.tags!r}"
print("PASS  P7a: tag parser strips leading '@'")


# --- P7b: cell parser unescapes `\\` and `\|` -----------------------------
src = (
    "Feature: x\n\n"
    "  Scenario Outline: y\n    Given <col>\n\n"
    "    Examples:\n"
    "      | col   |\n"
    "      | a\\|b |\n"
    "      | c\\\\d |\n"
)
feat = parse_feature(src)
rows = feat.scenario.examples[0].rows
assert rows == [["a|b"], ["c\\d"]], f"P7b: cell unescape failed, got {rows!r}"
print("PASS  P7b: cell parser unescapes backslash and pipe")


# --- P8: non-canonical step keywords silently dropped ---------------------
src = (
    "Feature: x\n\n"
    "  Scenario: y\n"
    "    Given valid step\n"
    "    * bullet step\n"
)
feat = parse_feature(src)
keywords = [s.keyword for s in feat.scenario.steps]
assert keywords == ["Given"], f"P8: non-canonical '* bullet' must be dropped, got {keywords!r}"
print("PASS  P8: non-canonical step keywords are silently dropped")


# --- P9: docstrings, comments, blank lines, `# language:` discarded -------
src = (
    "# language: en\n"
    "# stray non-directive comment\n"
    "\n"
    "Feature: x\n\n"
    "  Scenario: y\n"
    "    Given step\n"
    '      """\n'
    "      docstring body\n"
    '      """\n'
)
feat = parse_feature(src)
assert feat.description == "x", f"P9: stray description content, got {feat.description!r}"
assert feat.tags == [], f"P9: stray tags, got {feat.tags!r}"
assert feat.enums == {}, f"P9: comments must not populate enums, got {feat.enums!r}"
assert len(feat.scenario.steps) == 1, f"P9: expected 1 step, got {len(feat.scenario.steps)}"
assert feat.scenario.steps[0].text == "step", f"P9: docstring leaked into step.text: {feat.scenario.steps[0].text!r}"
assert feat.scenario.steps[0].data_table is None, "P9: docstring leaked into data_table"
print("PASS  P9: docstrings, comments, blank lines and '# language:' headers are discarded")
