"""tech-05 SN4/SN5 — folder-group colspan bump + remark height cap.

Verifies (spec `specs/tech/05-tech-run-detail-scenario-name-NEW.md`):
  1. SN4: with the extra Scenario name column, the folder-group heading
     row spans all 5 columns (`colspan="5"`) — both the server-rendered
     heading and the JS clone <template>.
  2. SN5: the remark <textarea> stands ~1.5 lines tall (`h-10`) and scrolls
     (`overflow-y-auto`) so a 2nd line peeks (cueing "there's more") — in the
     live row and the add-row template.
"""
import re
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_file(["Alpha", "Checkout", "pay"], scenario_name="User pays with card")
    s.create_run_group("Alpha", "release-1")
    s.create_run(
        project="Alpha", group="release-1", name="Smoke", file_name="smoke",
        case_paths=["Alpha/Checkout/pay.feature"],
    )

    client = app.test_client()
    html = client.get("/ui/run/Alpha/release-1/smoke.yaml").get_data(as_text=True)

    # 1) Server-rendered folder-group heading spans 5 columns.
    head = re.search(r'<tr class="run-group-head[^>]*>(.*?)</tr>', html, re.S)
    assert head, "folder-group heading row missing"
    assert 'colspan="5"' in head.group(1), head.group(1)
    assert 'colspan="4"' not in html, "stale colspan=4 still present in server render"
    print("PASS SN4 server folder-group heading spans 5 columns")

    # 1b) The JS clone <template> for new group heads also spans 5.
    tpl = re.search(
        r'<template id="run-group-head-template">(.*?)</template>', html, re.S
    )
    assert tpl and 'colspan="5"' in tpl.group(1), "group-head clone template not colspan=5"
    print("PASS SN4 group-head clone template spans 5 columns")

    # 2) Remark textarea: ~1.5-line height + scroll (live + template).
    remarks = re.findall(r'<textarea class="run-remark[^"]*"[^>]*>', html)
    assert remarks, "no run-remark textarea found"
    for ta in remarks:
        assert "h-10" in ta, ta
        assert "overflow-y-auto" in ta, ta
        assert "max-h-[3.25rem]" not in ta, f"stale 2-line cap still present: {ta}"
    print("PASS SN5 remark textarea stands ~1.5 lines tall + scrolls")
