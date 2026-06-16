# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Acceptance criteria -- AC6.

tech-04: the folder list's middle column shows the SCENARIO NAME, not the
feature description. Strengthens FT2 by exercising the full PUT-raw ->
render round-trip: a scenario name written via the raw route surfaces in
the list cell, while the feature description does not.
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
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "case", "scenario_name": "s", "description": "seed"},
    )
    # Raw source carries a feature description AND a named scenario. The
    # folder list renders the scenario name; the description must not show.
    raw = (
        "Feature: AC6 DESCRIPTION that must hide.\n"
        "\n"
        "  Scenario: AC6 the visible scenario name\n"
        "    Given a step\n"
    )
    r = client.put(
        "/api/files/Alpha/Mod/case.feature/raw",
        data=raw.encode("utf-8"),
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    assert r.status_code == 200, (
        f"AC6 setup: PUT raw must succeed, got {r.status_code} "
        f"{r.get_data(as_text=True)!r}"
    )
    html = client.get("/ui/folder/Alpha/Mod").get_data(as_text=True)

# Locate the file row.
row = re.search(
    r'<tr[^>]*hx-get="/ui/file/Alpha/Mod/case\.feature"[^>]*>(.*?)</tr>',
    html,
    re.DOTALL,
).group(1)

# Find the scenario-name cell (the <td> with title=).
cell = None
for m in re.finditer(r'<td([^>]*?)>(.*?)</td>', row, re.DOTALL):
    if 'title="' in m.group(1):
        cell = m
        break
assert cell, "AC6 setup: row must have a Scenario-name <td> with title="
attrs = cell.group(1)
body = cell.group(2).strip()

# The scenario name (written via raw PUT) is the visible cell content.
assert "AC6 the visible scenario name" in body, (
    f"AC6: visible cell must show the scenario name; got body {body!r}"
)
# The feature description must NOT leak into the folder list.
assert "DESCRIPTION that must hide" not in row, (
    "AC6: the feature description must NOT appear in the folder list"
)

# The full scenario name rides along in title= for hover.
title_value = re.search(r'title="([^"]*)"', attrs).group(1)
assert "AC6 the visible scenario name" in title_value, (
    f"AC6: title= must carry the full scenario name for hover; "
    f"got title {title_value!r}"
)
print("PASS  AC6: PUT-raw scenario name -> folder list cell (tech-04); description does not leak")
