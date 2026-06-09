"""Smoke k2: rendered HTML reflects the IN-PROGRESS → EXECUTING rename.

Tracks the "Rename run-result status IN-PROGRESS → EXECUTING" Must-have
item. End-to-end render via the Flask test client — exercises both
UI surfaces that mention the status string.

Two assertions:
1. GET `/ui/run/<project>/<group>/<file>.yaml` renders the result
   `<select>` with an `EXECUTING` option and no `IN-PROGRESS` option.
   The options come from `RUN_RESULTS` server-side, so this catches
   any future drift where a hardcoded literal sneaks back in.
2. GET `/ui/folder/<project>/test-run/<group>` renders the status-
   breakdown badge for a run whose case is `EXECUTING`: the
   `EXECUTING` count badge is visible; no `IN-PROGRESS` text appears
   anywhere in the partial.
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
    s.create_folder(["Alpha", "Mod"])
    s.create_file(["Alpha", "Mod", "case"], description="case")
    s.create_run_group("Alpha", "g1")
    s.create_run(
        project="Alpha", group="g1", name="Smoke", file_name="smoke",
        case_paths=["Alpha/Mod/case.feature"],
    )
    # Flip the row to EXECUTING so the badge has something to render.
    s.update_run_result(
        project="Alpha", group="g1", file_name="smoke.yaml",
        case_path="Alpha/Mod/case.feature",
        result="EXECUTING", remark="",
    )

    client = app.test_client()

    # --- 1. Run editor renders <option value="EXECUTING"> ------------
    editor_html = client.get("/ui/run/Alpha/g1/smoke.yaml").get_data(as_text=True)
    assert re.search(
        r'<option\s+value="EXECUTING"[^>]*>EXECUTING</option>',
        editor_html,
    ), "run editor should render <option value='EXECUTING'>EXECUTING</option>"
    assert "IN-PROGRESS" not in editor_html, (
        "run editor partial must contain no IN-PROGRESS string after the rename"
    )
    print("PASS  run editor renders EXECUTING option, no IN-PROGRESS string")

    # --- 2. Group folder view renders the EXECUTING badge ------------
    group_html = client.get("/ui/folder/Alpha/test-run/g1").get_data(as_text=True)
    # The badge shape is `<span ...>&#8943; 1</span>`; we don't pin the
    # exact class list (Tailwind reorder-resilient), only the count of
    # `EXECUTING` in `counts['EXECUTING']` rendering as `1` after the
    # &#8943; glyph in a single badge span.
    assert re.search(
        r'<span[^>]*>&#8943;\s*1</span>',
        group_html,
    ), "group folder should render the EXECUTING (⋯) badge with count=1"
    assert "IN-PROGRESS" not in group_html, (
        "group folder partial must contain no IN-PROGRESS string after the rename"
    )
    print("PASS  group folder renders EXECUTING badge, no IN-PROGRESS string")
