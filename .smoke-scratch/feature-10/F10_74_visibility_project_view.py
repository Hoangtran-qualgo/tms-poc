# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / SV2 + SV3 -- project view hides typed area.

SV2: Storage.list_folder(project) filters `test-run` from the project's
     module list (len(parts)==1), and the rendered project view does
     not link to it.
SV3: the only UI entry points to the typed area are the Test-run
     sidebar tab and the run-editor / group breadcrumb's clickable
     `test-run` segment -- NOT the project module table.
"""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_run_group("Alpha", "release-1")
    s.create_run(project="Alpha", group="release-1", name="Smoke",
                 file_name="smoke", case_paths=[])
    client = app.test_client()

    # --- SV2: storage project listing excludes test-run. ---
    listing = s.list_folder("Alpha")
    assert listing["kind"] == "project", listing
    assert "Checkout" in listing["modules"], listing
    assert "test-run" not in listing["modules"], listing

    # --- SV2 + SV3: the project view does NOT link to the typed area. ---
    proj_html = client.get("/ui/folder/Alpha").get_data(as_text=True)
    assert "/ui/folder/Alpha/test-run" not in proj_html, (
        "project module table must not surface a test-run entry point"
    )

    # --- SV3: the sidebar tab IS an entry point (run leaf links). ---
    sidebar = client.get("/ui/test-run-tree").get_data(as_text=True)
    assert "/ui/run/Alpha/release-1/smoke.yaml" in sidebar, (
        "the Test-run sidebar tab must link run leaves"
    )

    # --- SV3: the group-view breadcrumb IS an entry point (clickable segment). ---
    group_html = client.get("/ui/folder/Alpha/test-run/release-1").get_data(as_text=True)
    assert 'hx-get="/ui/folder/Alpha/test-run"' in group_html, (
        "the breadcrumb's test-run segment must be a clickable entry point"
    )

print("PASS  SV2+SV3: project view hides/omits test-run; entry points are the sidebar tab + breadcrumb only")
