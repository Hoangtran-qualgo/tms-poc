# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Features-table FT3 (Tags column).

Tags rendered as chips with `@` prefix, on a single (truncated) line.
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
    # PUT-raw with SCENARIO-level tags. `Storage.list_folder` extracts
    # `feature.scenario.tags` (not `feature.tags`) for the Tags column,
    # so the tags must sit on the Scenario line, not the Feature line.
    # See `app.storage.Storage.list_folder` ~line 568.
    raw = (
        "Feature: tagged case\n"
        "\n"
        "  @smoke @critical\n"
        "  Scenario: s\n"
        "    Given a step\n"
    )
    r = client.put(
        "/api/files/Alpha/Mod/case.feature/raw",
        data=raw.encode("utf-8"),
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    assert r.status_code == 200, (
        f"FT3 setup: PUT raw with scenario-level tags must succeed, "
        f"got {r.status_code} {r.get_data(as_text=True)!r}"
    )

    # Sanity-check the parser preserved both scenario tags.
    body = client.get("/api/files/Alpha/Mod/case.feature").get_json()
    scn_tags = body.get("scenario", {}).get("tags", [])
    assert set(scn_tags) >= {"smoke", "critical"}, (
        f"FT3 setup: parsed feature.scenario must carry both tags; "
        f"got scenario.tags={scn_tags!r}"
    )

    html = client.get("/ui/folder/Alpha/Mod").get_data(as_text=True)

# Locate the file row.
row = re.search(
    r'<tr[^>]*hx-get="/ui/file/Alpha/Mod/case\.feature"[^>]*>(.*?)</tr>',
    html,
    re.DOTALL,
).group(1)

# FT3: each tag rendered as a `<span ...>@<tag></span>` chip.
chips = re.findall(r"<span[^>]*>@(\w+)</span>", row)
assert set(chips) >= {"smoke", "critical"}, (
    f"FT3: tag chips must render with '@' prefix; expected @smoke + @critical, "
    f"got {chips!r} from row {row[:300]!r}"
)

# FT3: Tags <td> carries the 'truncate' class for single-line containment.
tags_td = re.search(r'<td[^>]*class="[^"]*truncate[^"]*"[^>]*>\s*<span', row)
assert tags_td, (
    f"FT3: Tags <td> must carry the 'truncate' class so the chip row stays "
    f"on a single line; row body {row[:300]!r}"
)
print("PASS  FT3: tag chips render with '@' prefix; Tags <td> truncates to single line")
