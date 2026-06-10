# Pattern: see .smoke-scratch/README.md
"""tech-02 / E2 / run editor groups results by folder (server render).

specs/tech/02 § E2: results are grouped by folder. The server emits one plain
`run-group-head` heading row per folder (first-seen folder order, within-folder
order preserved) and renders each result row filename-only — full path stays on
`<tr data-file-path>` / `<td title>` / `<a hx-get>`.

Fixture interleaves two folders so a flat list would NOT be contiguous:
  foo/a, bar/b, foo/c  ->  [foo: a, c] then [bar: b].

Asserts:
1. A heading row exists for each folder, keyed by data-group-folder.
2. First-seen folder order: foo's heading precedes bar's.
3. Within foo, row a precedes row c (within-folder order preserved).
4. Rows are filename-only (no data-role="folder"), full path preserved.
"""
import tempfile, pathlib, re

from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "foo"])
    s.create_folder(["Alpha", "bar"])
    for folder, name in [("foo", "a"), ("bar", "b"), ("foo", "c")]:
        s.create_file(["Alpha", folder, name], description=name)
    s.create_run_group("Alpha", "g")
    s.create_run(
        project="Alpha", group="g", name="R1", file_name="r1",
        case_paths=["Alpha/foo/a.feature", "Alpha/bar/b.feature", "Alpha/foo/c.feature"],
    )

    html = app.test_client().get("/ui/run/Alpha/g/r1.yaml").get_data(as_text=True)

# 1. A heading row per folder.
assert 'data-group-folder="Alpha/foo"' in html, "missing foo folder heading"
assert 'data-group-folder="Alpha/bar"' in html, "missing bar folder heading"

# 2. First-seen folder order: foo heading before bar heading.
assert html.index('data-group-folder="Alpha/foo"') < html.index('data-group-folder="Alpha/bar"'), (
    "E2: first-seen folder order must be preserved (foo before bar)"
)

# 3. Within foo, a before c.
assert html.index('data-file-path="Alpha/foo/a.feature"') < html.index('data-file-path="Alpha/foo/c.feature"'), (
    "E2: within-folder order must be preserved (a before c)"
)
# ...and the bar row sits after the foo group started but the c row (foo) comes
# after the bar heading only if grouping really happened. Assert c (foo) renders
# before bar's heading — i.e. foo's rows are contiguous under foo's heading.
assert html.index('data-file-path="Alpha/foo/c.feature"') < html.index('data-group-folder="Alpha/bar"'), (
    "E2: foo's rows must be grouped together under foo's heading, not interleaved"
)

# 4. Filename-only rows; full path preserved on the three surfaces.
assert 'data-role="folder"' not in html, "E2: folder span must be dropped from rows"
assert 'data-role="filename"' in html, "rows must keep the filename span"
assert 'hx-get="/ui/file/Alpha/foo/a.feature"' in html, "full path preserved on <a hx-get>"
assert 'title="Alpha/foo/a.feature"' in html, "full path preserved on <td title>"

print("PASS  T02_05: run editor groups results by folder (first-seen + within-folder order)")
