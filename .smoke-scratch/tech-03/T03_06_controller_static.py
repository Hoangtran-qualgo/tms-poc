# Pattern: see .smoke-scratch/README.md
"""tech-03 / folder bulk-actions / controller static inspection.

The fan-out logic is client-side JS that the Flask test client cannot
exercise, so guard its key invariants by static inspection of
`08_bulk_actions.js`:

1. It is referenced by base.html (so it ships to the page).
2. It defines all four action handlers (move / delete / retag / run).
3. It calls the existing single-item endpoints (no new batch route) and
   the three pre-flight listing endpoints.
4. It binds idempotently via a `data-bulk-bound` guard on htmx swaps (U3).
5. Re-tag overwrites feature-level `tags` only (D1) — it does not touch
   `scenario.tags`.
"""
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
js = (REPO / "app" / "static" / "08_bulk_actions.js").read_text(encoding="utf-8")
base_html = (REPO / "app" / "templates" / "base.html").read_text(encoding="utf-8")

# 1. Shipped to the page.
assert "08_bulk_actions.js" in base_html, (
    "base.html must reference 08_bulk_actions.js"
)

# 2. All four action handlers exist.
for action in ("move", "delete", "retag", "run"):
    assert f"async {action}(" in js, (
        f"controller must define the '{action}' action handler"
    )

# 3. Uses the existing single-item endpoints (fan-out, no batch route) ...
for needle in (
    '/move',                      # Move PATCH
    '"DELETE", "/api/files/"',    # Delete
    '"PATCH", "/api/files/"',     # Re-tag write
    '/cases',                     # Run add-case
):
    assert needle in js, f"controller must call endpoint fragment {needle!r}"
# ... and the three pre-flight listing endpoints.
for needle in ("/api/tree", "/api/folders/", "/api/runs/"):
    assert needle in js, f"controller must read pre-flight endpoint {needle!r}"

# 4. Idempotent bind guard (no double-binding on unrelated swaps).
assert "data-bulk-bound" in js, (
    "U3: controller must guard binding with a data-bulk-bound marker"
)
assert "htmx:load" in js, "controller must (re)bind on htmx:load (swapped-in content)"

# 5. D1: re-tag sets feature-level tags only.
assert "feature.tags = tags" in js, (
    "D1: re-tag must overwrite feature-level tags"
)
assert "scenario.tags" not in js, (
    "D1: re-tag must NOT touch scenario-level tags"
)

# All-or-nothing: pre-flight failures abort before writes (sequential fan-out).
assert "_tmsBulkFanout" in js, "controller must fan out via the sequential helper"
print("PASS  T03_06: controller shipped; 4 actions + pre-flight endpoints + idempotent bind + D1 tags")
