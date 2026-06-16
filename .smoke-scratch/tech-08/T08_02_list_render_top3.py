# Pattern: see .smoke-scratch/README.md
"""tech-08 / test-case list revamp / render (DO-2).

The folder-detail features table caps BOTH the Tags and the new Enums
column to the first 3 chips + a `+N more…` overflow, with the full set in
the cell `title`. Empty cells render an em-dash. Decisions: LR-2 enum chip
text = `key : label`; cap = top 3 (raised from 2 per USER request).
"""
import pathlib
import re
import tempfile

from app import create_app


def _row(html: str, file_name: str) -> str:
    m = re.search(
        rf'<tr[^>]*hx-get="/ui/file/P/mod/{re.escape(file_name)}"[^>]*>(.*?)</tr>',
        html,
        re.DOTALL,
    )
    assert m, f"row for {file_name!r} must render"
    return m.group(1)


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    s = app.extensions["storage"]
    client = app.test_client()
    s.create_folder(["P"])
    s.create_folder(["P", "mod"])
    s.write_project_enums(
        "P",
        {
            "a": {"a1": "A One"},
            "b": {"b1": "B One"},
            "c": {"c1": "C One"},
            "d": {"d1": "D One"},
        },
    )

    # Case with 4 enums (kind-sorted a,b,c,d -> first 3 shown).
    s.create_file(["P", "mod", "many_enums.feature"], "d", scenario_name="ME")
    fe = s.read_feature(["P", "mod", "many_enums.feature"])
    fe.enums = {"a": "a1", "b": "b1", "c": "c1", "d": "d1"}
    s.write_feature(["P", "mod", "many_enums.feature"], fe)

    # Case with 4 tags (union order t1..t4 -> first 3 shown).
    s.create_file(["P", "mod", "many_tags.feature"], "d", scenario_name="MT")
    ft = s.read_feature(["P", "mod", "many_tags.feature"])
    ft.tags = ["t1", "t2", "t3", "t4"]
    s.write_feature(["P", "mod", "many_tags.feature"], ft)

    # Case with neither tags nor enums (em-dash in both columns).
    s.create_file(["P", "mod", "empty.feature"], "d", scenario_name="E")

    html = client.get("/ui/folder/P/mod").get_data(as_text=True)

# --- Tags: 3 chips + "+1 more…"; full union in title --------------------
tags_row = _row(html, "many_tags.feature")
tag_chips = re.findall(r"<span[^>]*>@(\w+)</span>", tags_row)
assert tag_chips == ["t1", "t2", "t3"], tag_chips
assert "+1 more…" in tags_row, tags_row
assert re.search(r'title="@t1 @t2 @t3 @t4"', tags_row), tags_row

# --- Enums: 3 `key : label` chips + "+1 more…"; full list in title ------
enums_row = _row(html, "many_enums.feature")
enum_chips = re.findall(r'bg-indigo-100[^>]*>([^<]+)</span>', enums_row)
assert enum_chips == ["a1 : A One", "b1 : B One", "c1 : C One"], enum_chips
assert "+1 more…" in enums_row, enums_row
assert "d1 : D One" in enums_row, enums_row  # full set in title

# --- Empty case: em-dash in both Tags and Enums cells -------------------
empty_row = _row(html, "empty.feature")
assert empty_row.count("—") >= 2, empty_row

print(
    "PASS  T08_02: Tags + Enums columns show first 3 chips + '+N more…' "
    "(full set in title); enum chips read 'key : label'; empty -> em-dash"
)
