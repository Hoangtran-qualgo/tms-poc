"""Spike: folder table has direct-row data; no current feature sort/filter.

Run: PYTHONPATH=. .venv/bin/python \
  .smoke-scratch/_investigate/folder-table-sort-filter/01_current_contract.py
"""

from pathlib import Path


root = Path(__file__).resolve().parents[3]
listing = (root / "app" / "storage" / "_listing.py").read_text()
table = (root / "app" / "templates" / "_folder_feature_table.html").read_text()
bulk = (root / "app" / "static" / "08_bulk_actions.js").read_text()

start = listing.index("features: list[dict[str, Any]] = []")
end = listing.index("kind = \"module\"", start)
listing_block = listing[start:end]

assert "features.append(" in listing_block
assert "features.sort(" not in listing_block
assert "data-bulk-root" in table
assert 'data-role="select"' in table
assert "rowBoxes" in bulk and "select-all" in bulk

print("PASS  folder table receives direct rows unsorted; bulk selection owns every row")
