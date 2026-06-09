# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Button gaps (BD5).

**No rename / delete / move buttons at any folder-view depth.** Those
operations either don't have UI (`04-folder-crud`) or live inside the
file editor (`05-testcase-crud` rename + move). Tested at every depth
0, 1, 2, 3, 10.
"""
import pathlib
import re
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td).resolve())
    client = app.test_client()
    chain = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
    for i in range(1, len(chain) + 1):
        client.post(
            "/api/folders",
            json={"parent": "/".join(chain[: i - 1]), "name": chain[i - 1]},
        )
    client.post(
        "/api/files",
        json={"parent": "A/B", "file_name": "case", "description": "x"},
    )

    forbidden_handlers = [
        # Folder ops -- per feature-04 spec, no UI.
        "tmsRenameFolder",
        "tmsDeleteFolder",
        "tmsMoveFolder",
        # File ops -- rename + move live inside the file editor
        # (feature-05), NOT inside folder views.
        "tmsRenameFile",
        "tmsDeleteFile",
        "tmsMoveFile",
        "tmsDuplicateFile",
    ]
    forbidden_labels = [
        "Rename folder", "Delete folder", "Move folder",
        "Rename file", "Delete file", "Move file", "Duplicate file",
    ]

    for depth in (0, 1, 2, 3, 10):
        if depth == 0:
            path = ""
        else:
            path = "/".join(chain[:depth])
        url = f"/ui/folder/{path}" if path else "/ui/folder/"
        html = client.get(url).get_data(as_text=True)

        for handler in forbidden_handlers:
            assert handler not in html, (
                f"BD5 (depth {depth}, url {url!r}): the rendered folder view "
                f"must NOT carry a call to {handler}() -- folder views are "
                f"navigation + create-only; rename/delete/move/duplicate live "
                f"elsewhere"
            )
        for label in forbidden_labels:
            assert label not in html, (
                f"BD5 (depth {depth}, url {url!r}): the rendered folder view "
                f"must NOT carry the literal button label {label!r}"
            )
print("PASS  BD5: no rename/delete/move/duplicate buttons or JS handlers at any folder-view depth (0,1,2,3,10)")
