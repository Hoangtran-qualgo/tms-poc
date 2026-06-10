# Pattern: see .smoke-scratch/README.md
"""tech-02 / E3 / run-editor Result select carries the data-status hook.

specs/tech/02 § E3: the run-editor `Result` <select> is coloured per status
via the shared single-source palette (app.css [data-status]) — never an
inline colour. The server renders `data-status="{{ r.result }}"` on each live
select, and 06_run_editor.js keeps it in lock-step on change + on clone.

Asserts:
1. A live run with a FAILED result renders a <select> with data-status="FAILED".
2. 06_run_editor.js sets `e.target.dataset.status = e.target.value` on change.
3. 06_run_editor.js sets the clone's `dataset.status` so added rows colour too.
"""
import tempfile, pathlib, re

from app import create_app
from app.storage import Storage

REPO = pathlib.Path(__file__).resolve().parents[2]

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "mod"])
    s.create_file(["Alpha", "mod", "a.feature"], "desc")
    s.create_run_group("Alpha", "g")
    s.create_run(project="Alpha", group="g", name="R1", file_name="r1",
                 case_paths=["Alpha/mod/a.feature"])
    tr = s.read_run("Alpha", "g", "r1.yaml")
    tr.results[0].result = "FAILED"
    s.write_run("Alpha", "g", "r1.yaml", tr)

    html = app.test_client().get("/ui/run/Alpha/g/r1.yaml").get_data(as_text=True)

# 1. Server renders the data-status hook on the live select.
m = re.search(r'<select class="run-result-select[^>]*>', html)
assert m, "run-result-select not found in rendered run editor"
assert 'data-status="FAILED"' in m.group(0), (
    f"live result select must carry data-status=result; got {m.group(0)!r}"
)

# 2 + 3. JS keeps the hook synced on change and on clone.
js = (REPO / "app" / "static" / "06_run_editor.js").read_text(encoding="utf-8")
assert "e.target.dataset.status = e.target.value" in js, (
    "06_run_editor.js must sync data-status on the select's change event (E3)"
)
assert "sel.dataset.status = sel.value" in js, (
    "06_run_editor.js must set data-status on a cloned result row (E3)"
)

print("PASS  T02_03: run-editor Result select carries the data-status palette hook")
