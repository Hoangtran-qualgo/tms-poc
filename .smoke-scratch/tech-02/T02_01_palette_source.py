# Pattern: see .smoke-scratch/README.md
"""tech-02 / UI styling / status palette is a single source of truth.

specs/tech/02-tech-ui-styling-enhancement-NEW.md § Status palette: the five
run-result statuses each have exactly ONE canonical colour, defined once in
`app/static/app.css` as `[data-status="..."]` selectors. Consumers (E3 run
editor, E4 report detail) only attach the `data-status` hook — never a colour.

Asserts, by static inspection of app.css:
1. All five RUN_RESULTS statuses have a `[data-status="X"]` colour rule.
2. The canonical hex values match the spec (SKIPPED = purple, decision D1).
3. No colour is duplicated across statuses (each status is distinct).
"""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
css = (REPO / "app" / "static" / "app.css").read_text(encoding="utf-8")

# Canonical palette per the spec (the source of truth).
EXPECTED = {
    "PASSED": "#059669",
    "FAILED": "#e11d48",
    "EXECUTING": "#0284c7",
    "SKIPPED": "#9333ea",  # purple — decision D1
    "PENDING": "#d97706",
}

found = dict(re.findall(r'\[data-status="(\w+)"\]\s*\{\s*color:\s*(#[0-9a-fA-F]{6})', css))

# 1 + 2. Every status present with its canonical colour.
for status, hexval in EXPECTED.items():
    assert status in found, f"app.css missing [data-status={status!r}] colour rule"
    assert found[status].lower() == hexval, (
        f"[data-status={status!r}] must be {hexval} (got {found[status]})"
    )

# SKIPPED is purple, explicitly (D1 regression guard).
assert found["SKIPPED"].lower() == "#9333ea", "SKIPPED must be purple (#9333ea) per D1"

# 3. No two statuses share a colour.
colours = [v.lower() for v in found.values()]
assert len(colours) == len(set(colours)), f"status colours must be distinct; got {found}"

print(f"PASS  T02_01: {len(EXPECTED)} statuses in single-source palette, SKIPPED=purple")
