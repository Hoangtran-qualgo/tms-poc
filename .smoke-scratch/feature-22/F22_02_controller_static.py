"""feature-22 / table controller keeps approved client-side semantics."""

from pathlib import Path


js = (
    Path(__file__).resolve().parents[2] / "app" / "static" / "08_bulk_actions.js"
).read_text(encoding="utf-8")

assert 'data-role="scenario-filter"' in js
assert 'data-role="file-sort"' in js
assert 'data-role="file-sort-header"' in js
assert 'filterInput.value.trim().toLowerCase()' in js
assert 'data-scenario-name' in js
assert 'row.classList.toggle("hidden"' in js
assert 'data-sort-direction' in js
assert 'aria-sort' in js
assert 'tr[data-file-name]' in js
assert 'a.dataset.fileName.toLowerCase().localeCompare' in js
assert 'Number(a.dataset.sortIndex) - Number(b.dataset.sortIndex)' in js
assert 'visibleBoxes().forEach' in js, "Select all must change visible rows only"
assert 'const paths = selected();' in js, "bulk actions must retain hidden selections"
assert '" shown · " + n + " selected"' in js

print("PASS  F22_02: client sort/filter and visible-only Select all are wired")
