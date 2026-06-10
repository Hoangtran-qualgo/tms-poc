# Pattern: see .smoke-scratch/README.md
"""tech-01 / restructure / JS script-load order + completeness.

Guards the slice-4 split of `app.js` into ordered global-scope files
(specs/tech/01-tech-restructure-NEW.md). The files are classic globals
with no build step, so the ONLY correctness constraint is load order:
`09_bootstrap.js` runs `tmsBootShell` + registers listeners that call
functions defined in the earlier files, so it MUST load last (risk R1).

Asserts, by static inspection of base.html + the static dir:

1. base.html references the app JS files in ascending `NN_` order.
2. `09_bootstrap.js` is the LAST app script tag.
3. Every `app/static/NN_*.js` file is referenced (no orphan / missing),
   so a newly-added split file can't silently drop out of the page.
4. The sorted glob order (used by the static-inspection smokes to
   reconstruct the original source order) matches the load order.
"""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
base_html = (REPO / "app" / "templates" / "base.html").read_text(encoding="utf-8")
static_dir = REPO / "app" / "static"

# Ordered list of NN_-prefixed JS files referenced in base.html.
referenced = re.findall(r"filename='(\d{2}_[A-Za-z_]+\.js)'", base_html)
assert referenced, "base.html must reference the NN_-prefixed split JS files"

# 1. Ascending NN_ order.
assert referenced == sorted(referenced), (
    f"base.html script tags must be in ascending NN_ order; got {referenced}"
)

# 2. bootstrap last.
assert referenced[-1] == "09_bootstrap.js", (
    f"09_bootstrap.js must be the last app script; got {referenced[-1]!r}"
)

# 3 + 4. Every NN_*.js on disk is referenced exactly once, and disk order
# (sorted glob) == load order.
on_disk = sorted(p.name for p in static_dir.glob("[0-9][0-9]_*.js"))
assert on_disk == referenced, (
    f"static NN_*.js files {on_disk} must match base.html references {referenced} "
    "(a split file is missing from the page, or an extra tag points nowhere)"
)

# The old monolith must be gone (its content now lives in the split files).
assert not (static_dir / "app.js").exists(), (
    "app/static/app.js should have been removed by the slice-4 split"
)

print(f"PASS  T01_01: {len(referenced)} JS files load in NN_ order, bootstrap last")
