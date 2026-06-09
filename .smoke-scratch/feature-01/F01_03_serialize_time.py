# Pattern: see .smoke-scratch/README.md
"""feature-01 / gherkin-io / Serialize-time invariants (S1-S5)."""
from app.gherkin_io import serialize_feature
from app.models import (
    Background,
    ExamplesTable,
    Feature,
    Scenario,
    Step,
)


def _feat(**overrides) -> Feature:
    """Compose a minimally valid Feature; override only what differs."""
    defaults = dict(
        description="x",
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
    defaults.update(overrides)
    return Feature(**defaults)


# --- S1: tag dedup + '@' prepended (first-wins order preserved) -----------
out = serialize_feature(_feat(tags=["foo", "bar", "foo", "baz", "bar"]))
header = out.splitlines()[0]
assert header == "@foo @bar @baz", f"S1: tag dedup/order/@ failed, got {header!r}"
print("PASS  S1: tags de-duped (first-wins) and prepended with '@'")


# --- S2: Feature.description real \n encoded as literal '\\n' -------------
out = serialize_feature(_feat(description="line1\nline2"))
feat_lines = [ln for ln in out.splitlines() if ln.startswith("Feature:")]
assert len(feat_lines) == 1, f"S2: 'Feature:' line must stay single-line, got {len(feat_lines)}"
assert feat_lines[0] == "Feature: line1\\nline2", f"S2: \\n encoding wrong, got {feat_lines[0]!r}"
print("PASS  S2: Feature.description real \\n encoded as literal '\\\\n'")


# --- S3a: cell escape applies backslash before pipe -----------------------
# Input cell value: "\|"  (1 backslash + 1 pipe).
# Correct order:   \ -> \\ then | -> \|  =>  "\\\|"  (3 backslashes + 1 pipe).
# Reversed order:  | -> \| then \ -> \\  =>  "\\\\|" (4 backslashes + 1 pipe).
out = serialize_feature(_feat(
    scenario=Scenario(
        kind="outline",
        steps=[Step(keyword="Given", text="<col>")],
        examples=[ExamplesTable(header=["col"], rows=[["\\|"]])],
    ),
))
assert "\\\\\\|" in out, f"S3a: cell escape order wrong, output was:\n{out}"
assert "\\\\\\\\|" not in out, f"S3a: detected reversed-order escape, output was:\n{out}"
print("PASS  S3a: cell escape applies backslash before pipe")


# --- S3b: cell whitespace trimmed at write --------------------------------
out = serialize_feature(_feat(
    scenario=Scenario(
        kind="outline",
        steps=[Step(keyword="Given", text="<col>")],
        examples=[ExamplesTable(header=["col"], rows=[["  hello  "]])],
    ),
))
assert "  hello  " not in out, f"S3b: surrounding whitespace not trimmed, output:\n{out}"
assert "hello" in out, f"S3b: trimmed cell value missing, output:\n{out}"
print("PASS  S3b: cell whitespace trimmed at write time")


# --- S3c: empty cell renders as a single space (then column-padded) -------
out = serialize_feature(_feat(
    scenario=Scenario(
        kind="outline",
        steps=[Step(keyword="Given", text="<col>")],
        examples=[ExamplesTable(header=["col"], rows=[[""]])],
    ),
))
# Header col is "col" (width 3); empty cell becomes " " then pads to 3 spaces.
# Expected rendered empty row: "      |     |" (6-space indent + |+1+3+1+|).
empty_row = next(
    (ln for ln in out.splitlines()
     if ln.strip().startswith("|") and "col" not in ln and "Examples" not in ln),
    None,
)
assert empty_row == "      |     |", f"S3c: empty-cell row format wrong, got {empty_row!r}"
print("PASS  S3c: empty cell renders as a single space (then column-padded)")


# --- S3d: outline examples grid is column-aligned -------------------------
out = serialize_feature(_feat(
    scenario=Scenario(
        kind="outline",
        steps=[Step(keyword="Given", text="<a>")],
        examples=[ExamplesTable(
            header=["a", "bb"],
            rows=[["xx", "y"], ["z", "ww"]],
        )],
    ),
))
table_lines = [ln for ln in out.splitlines() if ln.strip().startswith("|")]
widths = {len(ln) for ln in table_lines}
assert len(widths) == 1, f"S3d: table lines must align, got widths {widths}, output:\n{out}"
print("PASS  S3d: outline examples grid is column-aligned")


# --- S4: empty Background omitted from output -----------------------------
out_with = serialize_feature(_feat(background=Background(
    steps=[Step(keyword="Given", text="setup")]
)))
assert "Background:" in out_with, "S4 (sanity): Background must appear when steps non-empty"
out_without = serialize_feature(_feat(background=Background(steps=[])))
assert "Background:" not in out_without, "S4: empty Background must be omitted"
print("PASS  S4: empty Background is omitted from serialised output")


# --- S5: UTF-8 + LF line endings only -------------------------------------
out = serialize_feature(_feat(description="multi\nline", tags=["a"]))
assert "\r" not in out, "S5: output must not contain CR (LF-only)"
assert out.encode("utf-8").decode("utf-8") == out, "S5: output is not UTF-8 round-trippable"
print("PASS  S5: serialised output is UTF-8 with LF line endings only")
