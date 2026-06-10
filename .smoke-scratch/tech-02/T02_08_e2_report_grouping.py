# Pattern: see .smoke-scratch/README.md
"""tech-02 / E2 (extended) / ranking-report bucket cases group by folder.

Follow-up to the run-editor E2 grouping: a ranking report's bucket case list
was flat (full paths, no grouping). Per user feedback (Jun 10, 2026) the same
folder-grouping idiom now applies to the shared ranking bucket template
(enum_ranking / tag_ranking / tag_inventory): each bucket groups its cases by
folder (first-seen order) with a muted folder heading + filename-only items;
the full path stays on the <a hx-get>.

Fixture: two folders (foo, bar) both carrying tag "smoke", failed in one run,
so a tag_ranking(status=FAILED) "smoke" bucket holds cases from both folders.

Asserts:
1. The bucket renders a folder heading per folder (data-group-folder).
2. foo precedes bar (first-seen folder order).
3. Items are filename-only (a.feature shown), full path on <a hx-get>.
"""
import tempfile, pathlib

from app import create_app
from app.storage import Storage
from app.models import Report

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "foo"])
    s.create_folder(["Alpha", "bar"])
    for folder, name in [("foo", "a"), ("bar", "b")]:
        s.create_file(["Alpha", folder, name], description=name)
        f = s.read_feature(f"Alpha/{folder}/{name}.feature")
        f.tags = ["smoke"]
        s.write_feature(f"Alpha/{folder}/{name}.feature", f)

    s.create_run_group("Alpha", "g")
    s.create_run(project="Alpha", group="g", name="R1", file_name="r1",
                 case_paths=["Alpha/foo/a.feature", "Alpha/bar/b.feature"])
    tr = s.read_run("Alpha", "g", "r1.yaml")
    for r in tr.results:
        r.result = "FAILED"
    s.write_run("Alpha", "g", "r1.yaml", tr)

    s.create_report("Alpha", "tag", Report(type="tag_ranking", title="Tag R",
                    status="FAILED", run_paths=["Alpha/test-run/g/r1.yaml"]))

    html = app.test_client().get("/ui/report/Alpha/tag.yaml").get_data(as_text=True)

# 1. Folder heading per folder.
assert 'data-group-folder="Alpha/foo"' in html, "missing foo folder heading in bucket"
assert 'data-group-folder="Alpha/bar"' in html, "missing bar folder heading in bucket"

# 2. First-seen folder order: foo before bar.
assert html.index('data-group-folder="Alpha/foo"') < html.index('data-group-folder="Alpha/bar"'), (
    "bucket folder grouping must preserve first-seen order (foo before bar)"
)

# 3. Filename-only items; full path preserved on the link.
assert 'hx-get="/ui/file/Alpha/foo/a.feature"' in html, "full path preserved on <a hx-get>"
assert '>a.feature</a>' in html, "bucket items must render filename-only"

print("PASS  T02_08: ranking-report bucket cases group by folder (filename-only items)")
