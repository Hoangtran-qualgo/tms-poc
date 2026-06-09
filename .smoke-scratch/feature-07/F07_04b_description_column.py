# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Features-table FT2 (Description column).

Description column shows the **first line only**, truncated; the full
description (with real newlines) goes into the `title=` attribute for
hover. Multi-line descriptions never expand the row.

Multi-line descriptions are encoded on the `Feature:` line via the
literal two-character sequence `\\n` (decoded by the parser to a real
newline). See `app.gherkin_io._encode_description` /
`_assemble_description`.
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
    # PUT-raw with a multi-line description (canonical create path only
    # accepts a single-line description string).
    raw = (
        "Feature: First line of description."
        "\\nSecond line should NOT appear in the column."
        "\\nThird line either.\n"
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
        f"FT2 setup: PUT raw with multi-line description must succeed, "
        f"got {r.status_code} {r.get_data(as_text=True)!r}"
    )

    html = client.get("/ui/folder/Alpha/Mod").get_data(as_text=True)

# Locate the file row.
row = re.search(
    r'<tr[^>]*hx-get="/ui/file/Alpha/Mod/case\.feature"[^>]*>(.*?)</tr>',
    html,
    re.DOTALL,
).group(1)

# Description cell: <td ... title="..." class="...truncate...">first line</td>.
desc_cell = re.search(r'<td([^>]*)>([^<]*)</td>', row, re.DOTALL)
# That regex catches the first <td> (filename); iterate to find the one with title=.
desc_cell = None
for m in re.finditer(r'<td([^>]*?)>([^<]*)</td>', row, re.DOTALL):
    attrs = m.group(1)
    if 'title="' in attrs:
        desc_cell = m
        break
assert desc_cell, (
    "FT2: features table row must contain a Description <td> with a title= attribute"
)
attrs = desc_cell.group(1)
body = desc_cell.group(2).strip()

# Title attribute carries the FULL multi-line description.
title_m = re.search(r'title="([^"]*)"', attrs)
assert title_m, "FT2: Description <td> must carry title= attribute"
title_value = title_m.group(1)
assert "First line of description." in title_value, (
    f"FT2: Description <td>'s title= must carry the first line of the full "
    f"description; got {title_value!r}"
)
# Jinja escapes real newlines in attribute context as the literal sequence
# `\n` characters? Actually Flask/Jinja autoescape only handles HTML special
# chars (& < > " '), so real newlines become real newlines inside the
# attribute. Browsers preserve them. We assert by looking for the second
# line's text content anywhere in the attribute.
assert "Second line should NOT appear in the column." in title_value, (
    f"FT2: Description <td>'s title= must carry the FULL multi-line description "
    f"(both lines for hover); got {title_value!r}"
)
assert "Third line either." in title_value, (
    f"FT2: Description <td>'s title= must carry ALL lines; got {title_value!r}"
)

# Cell body: first line only -- no second/third line, no row expansion.
assert "First line of description." in body, (
    f"FT2: Description cell body must show the first line; got {body!r}"
)
assert "Second line" not in body, (
    f"FT2: Description cell body must NOT contain the second line "
    f"(first-line-only rule); got {body!r}"
)
assert "Third line" not in body, (
    f"FT2: Description cell body must NOT contain the third line; got {body!r}"
)

# `truncate` class enforces single-line / no row expansion.
assert "truncate" in attrs, (
    f"FT2: Description <td> must carry the 'truncate' class so multi-line "
    f"descriptions never expand the row; got attrs {attrs!r}"
)
print("PASS  FT2: description first-line-only + full title=; truncate class prevents row expansion")
