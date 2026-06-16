"""Test-run sidebar: group folder rows open their run listing; project
(depth-0) rows stay toggle-only.

Pins the "open a run group from the Test-run sidebar tree" change
(IN-PROGRESS Must-have, Jun 16 2026). The main-pane run listing
(/ui/folder/<p>/test-run/<g> -> folder_test_run_group.html) already exists
and is covered by F10_14; this asserts the sidebar now WIRES to it.

Decision (locked): groups clickable, project rows NOT navigable.
"""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s = Storage(pathlib.Path(td))
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_run_group("Alpha", "release-1")
    s.create_run(project="Alpha", group="release-1", name="Sprint A",
                 file_name="sprint-a", case_paths=["Alpha/Checkout/pay.feature"])

    html = app.test_client().get("/ui/test-run-tree").get_data(as_text=True)

    # Group (depth-1) row navigates to the existing run-listing view.
    assert 'hx-get="/ui/folder/Alpha/test-run/release-1"' in html, html
    print("PASS group folder row links to /ui/folder/<p>/test-run/<g>")

    # Project (depth-0) row is toggle-only: no nav to its module view.
    assert 'hx-get="/ui/folder/Alpha"' not in html, html
    print("PASS project row stays non-interactive (caret toggle only)")

    # Regression: run leaf still links to the editor.
    assert 'hx-get="/ui/run/Alpha/release-1/sprint-a.yaml"' in html, html
    print("PASS run leaf still links to /ui/run/...")
