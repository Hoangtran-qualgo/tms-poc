# Pattern: see .smoke-scratch/README.md
"""tech-09 / Scenario-Outline in test runs / DO-1 suffix parser.

Pure-model smoke: exercises app.allure_io.split_example_suffix directly.

Covers:
- S1: synthetic names -> (base, {table,row}) with 1-based ints, whitespace
  tolerated; plain names -> (stripped, None).
- S2: the real bundled sample's two outline rows trim to ONE shared base with
  {1,1}/{1,2}; non-suffixed rows return None (no false positives).
- S3: edges -- a name that merely contains ' -- ' or has a non-anchored token
  is returned whole (not mis-split).
"""
from pathlib import Path

from app.allure_io import parse_allure_report, split_example_suffix

SAMPLE = Path("specs/sample-data/allure-report-single/index.html")


# --- S1: synthetic happy-path + whitespace tolerance -----------------------
cases = {
    "a -- @1.2 ": ("a", {"table": 1, "row": 2}),     # real format: trailing space
    "a -- @1.2": ("a", {"table": 1, "row": 2}),       # no trailing space
    "a -- @10.3": ("a", {"table": 10, "row": 3}),     # multi-digit
    "  spaced name -- @2.5  ": ("spaced name", {"table": 2, "row": 5}),
    "plain name": ("plain name", None),
    "  padded plain  ": ("padded plain", None),
}
for raw, expected in cases.items():
    got = split_example_suffix(raw)
    assert got == expected, f"S1: {raw!r} -> {got!r}, expected {expected!r}"
print("PASS  S1: suffix parsed to (base, {table,row}); plain names -> None")


# --- S2: real sample -> two rows share one base, distinct rows -------------
report = parse_allure_report(SAMPLE.read_text(encoding="utf-8"))
split = [split_example_suffix(s.name) for s in report.scenarios]

suffixed = [(b, ex) for (b, ex) in split if ex is not None]
assert len(suffixed) == 2, f"S2: expected 2 suffixed rows, got {suffixed!r}"
bases = {b for (b, _ex) in suffixed}
assert bases == {"Verify retrieve agent conversations count"}, (
    f"S2: both rows must trim to ONE shared base, got {bases!r}"
)
assert sorted((ex["table"], ex["row"]) for (_b, ex) in suffixed) == [(1, 1), (1, 2)], (
    f"S2: rows must be distinct {{1,1}}/{{1,2}}, got {suffixed!r}"
)
# Non-suffixed sample rows must not be mis-split, and bases keep no trailing space.
for (b, ex) in split:
    if ex is None:
        assert b == b.strip() and " -- @" not in b, f"S2: plain base looks wrong: {b!r}"
print("PASS  S2: real sample's outline rows share one base with {1,1}/{1,2}")


# --- S3: non-anchored / natural '--' is NOT a suffix -----------------------
for raw in (
    "Login -- admin path",        # natural ' -- ' but no @n.m
    "count -- @1.1 extra",        # token not anchored at end
    "count -- @1",                # missing .<row>
    "count --@1.1",               # missing space after --
    "count @1.1",                 # missing -- token
):
    base, ex = split_example_suffix(raw)
    assert ex is None, f"S3: {raw!r} must NOT split, got example {ex!r}"
    assert base == raw.strip(), f"S3: {raw!r} base must be whole, got {base!r}"
print("PASS  S3: names without an anchored ' -- @n.m' token are returned whole")
