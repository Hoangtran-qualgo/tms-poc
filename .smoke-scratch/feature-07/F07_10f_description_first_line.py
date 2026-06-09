# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Acceptance criteria -- AC6.

Multi-line feature descriptions render only their first line in the
table; full text appears on hover (`title=` attribute). Strengthens
FT2 by exercising the full PUT-raw -> render round-trip.
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
        json={"parent": "Alpha/Mod", "file_name": "case", "description": "seed"},
    )
    # Multi-line description encoded on the Feature: line via `\n`
    # (literal two-char). See `app.gherkin_io._encode_description`.
    raw = (
        "Feature: AC6 first line of description."
        "\\nAC6 SECOND LINE that must hide."
        "\\nAC6 THIRD LINE that must hide too.\n"
        "\n"
        "  Scenario: s\n"
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

# Find the description cell (the <td> with title=).
desc_cell = None
for m in re.finditer(r'<td([^>]*)>([^<]*)</td>', row, re.DOTALL):
    attrs = m.group(1)
    if 'title="' in attrs:
        desc_cell = m
        break
assert desc_cell, "AC6 setup: row must have a Description <td> with title="
attrs = desc_cell.group(1)
body = desc_cell.group(2).strip()

# First line ONLY in the visible cell.
assert "AC6 first line of description." in body, (
    f"AC6: visible cell must show the first line of the description; "
    f"got body {body!r}"
)
assert "SECOND LINE" not in body, (
    f"AC6: visible cell must NOT contain the second line; got body {body!r}"
)
assert "THIRD LINE" not in body, (
    f"AC6: visible cell must NOT contain the third line; got body {body!r}"
)

# Full multi-line text in the title= attribute (for hover).
title_value = re.search(r'title="([^"]*)"', attrs).group(1)
for needle in (
    "AC6 first line of description.",
    "AC6 SECOND LINE that must hide.",
    "AC6 THIRD LINE that must hide too.",
):
    assert needle in title_value, (
        f"AC6: title= attribute must carry all lines of the full description "
        f"for hover; expected {needle!r} in title; got title {title_value!r}"
    )
print("PASS  AC6: multi-line description -> first line in cell + full text in title= (hover)")
