"""3.A.ii — GET /ui/folder/<project>/test-run/<group> renders the runs
table sorted by created_at DESC, with status-breakdown badges.

Note: as of the "Relocate + simplify the `+ New run` flow" change, the
`+ New run` button no longer lives in this view; the assertion below
inversely verifies its absence. Coverage of the new sidebar-only
button location lives in F10_23 / F10_24 / F10_25 / F10_26."""
import time
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_run_group("Alpha", "release-1")
    s.create_run(project="Alpha", group="release-1", name="Sprint 1",
                 file_name="sprint-1", case_paths=["Alpha/Checkout/a.feature"])
    # created_at is stamped with seconds precision; sleep over 1 s to
    # guarantee Sprint 2's timestamp is observably later than Sprint 1's.
    time.sleep(1.05)
    s.create_run(project="Alpha", group="release-1", name="Sprint 2",
                 file_name="sprint-2", case_paths=["Alpha/Checkout/a.feature",
                                                    "Alpha/Checkout/b.feature"])
    # Mark one as PASSED to verify the badge renders.
    s.update_run_result(project="Alpha", group="release-1",
                        file_name="sprint-2.yaml",
                        case_path="Alpha/Checkout/a.feature",
                        result="PASSED", remark="ok")

    client = app.test_client()
    r = client.get("/ui/folder/Alpha/test-run/release-1")
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)

    # Breadcrumb includes the test-run link.
    assert "hx-get=\"/ui/folder/Alpha/test-run\"" in html

    # Heading shows the group name.
    assert ">release-1<" in html

    # + New run button no longer rendered here; the sidebar tab now
    # owns the run-creation affordance (see F10_23 / F10_24 / F10_25).
    assert "tmsCreateRun" not in html

    # Both runs appear; Sprint 2 (newer) before Sprint 1.
    i2 = html.find("Sprint 2")
    i1 = html.find("Sprint 1")
    assert i2 != -1 and i1 != -1
    assert i2 < i1, "newer run should sort above older one"

    # Sprint 2 has one PASSED and one PENDING (the b.feature case).
    # Find the Sprint 2 row segment and check both badges appear in order.
    s2_row_start = html.find("sprint-2.yaml")
    s2_row_end = html.find("</tr>", s2_row_start)
    s2_row = html[s2_row_start:s2_row_end]
    assert "&#10003; 1" in s2_row, f"PASSED badge missing in Sprint 2 row: {s2_row}"
    assert "? 1" in s2_row, f"PENDING badge missing in Sprint 2 row: {s2_row}"

    # Case counts reflect the configured cases.
    assert ">2<" in s2_row  # Sprint 2 case_count == 2
    print("PASS 3.A.ii group view: sort, badges, case_count, no + New run button")
