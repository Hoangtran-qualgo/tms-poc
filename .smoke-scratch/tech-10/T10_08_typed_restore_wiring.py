"""T10-08 — typed-tab tree restore wiring (tech-10 phase 10b, static).

The Directory-tree restore is generalised so the typed sidebar trees
(test-run / reports) reuse it: a `tmsTypedExpand` set seeded at boot for a
non-tree active tab, re-applied on every typed-pane swap (lazy mount + SSE).
"""
import pathlib
import re

TREE = pathlib.Path("app/static/01_tree.js").read_text()
BOOT = pathlib.Path("app/static/09_bootstrap.js").read_text()

# 01_tree.js: generalized helper + typed set/restore.
assert "function tmsApplyTreeExpansion(" in TREE, "shared expansion helper missing"
assert "const tmsTypedExpand = new Set()" in TREE, "typed expand set missing"
assert "function tmsRestoreTypedTree(" in TREE, "typed restore missing"
m = re.search(r"function tmsRestoreTreeState\(\)\s*\{[\s\S]*?\n\}", TREE)
assert m and "tmsApplyTreeExpansion" in m.group(0), (
    "tmsRestoreTreeState must delegate to tmsApplyTreeExpansion"
)
print("PASS 01_tree.js: shared expansion + typed set/restore")

# 09_bootstrap.js: seed typed set for a non-tree tab + restore typed panes.
assert "tmsTypedExpand.add" in BOOT, "bootstrap must seed tmsTypedExpand"
assert "tmsRestoreTypedTree(e.target)" in BOOT, "afterSwap must restore typed panes"
for pane in ("test-run-pane", "reports-pane", "enums-pane"):
    assert pane in BOOT, f"afterSwap must handle {pane}"
print("PASS 09_bootstrap.js: typed seed + afterSwap restore for typed panes")
