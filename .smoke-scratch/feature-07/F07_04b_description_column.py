# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Features-table FT2 (Scenario-name column).

tech-04: the folder-detail test-case list's middle column shows the
SCENARIO NAME (not the feature description). The cell is `truncate`d so a
long name never expands the row (R2 / G3), and the full name rides along
in the `title=` attribute for hover.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    # A case whose scenario name differs from the feature description, so
    # the column content is unambiguous about which field it renders.
    r = client.post(
        "/api/files",
        json={
            "parent": "Alpha/Mod",
            "file_name": "case",
            "scenario_name": "Checkout with a saved card",
            "description": "DESCRIPTION-SHOULD-NOT-APPEAR",
        },
    )
    assert r.status_code in (200, 201), (
        f"FT2 setup: create must succeed, got {r.status_code} "
        f"{r.get_data(as_text=True)!r}"
    )

    html = client.get("/ui/folder/Alpha/Mod").get_data(as_text=True)

# Locate the file row.
row = re.search(
    r'<tr[^>]*hx-get="/ui/file/Alpha/Mod/case\.feature"[^>]*>(.*?)</tr>',
    html,
    re.DOTALL,
).group(1)

# The middle column cell carries title= (the scenario name); find it.
cell = None
for m in re.finditer(r'<td([^>]*?)>(.*?)</td>', row, re.DOTALL):
    if 'title="' in m.group(1):
        cell = m
        break
assert cell, (
    "FT2: features table row must contain a Scenario-name <td> with a title= attribute"
)
attrs = cell.group(1)
body = cell.group(2).strip()

# tech-04: the column shows the scenario name, NOT the feature description.
assert "Checkout with a saved card" in body, (
    f"FT2: middle column body must show the scenario name; got {body!r}"
)
assert "DESCRIPTION-SHOULD-NOT-APPEAR" not in row, (
    "FT2: the feature description must NOT appear in the folder list "
    "(the scenario name replaced it)"
)

# Title attribute carries the full scenario name for hover.
title_m = re.search(r'title="([^"]*)"', attrs)
assert title_m and "Checkout with a saved card" in title_m.group(1), (
    f"FT2: Scenario-name <td> title= must carry the full name; got {attrs!r}"
)

# `truncate` class keeps a long name from expanding the row (R2 / G3).
assert "truncate" in attrs, (
    f"FT2: Scenario-name <td> must carry the 'truncate' class; got {attrs!r}"
)
print("PASS  FT2: folder list middle column shows the scenario name (tech-04), truncated + title= hover")
