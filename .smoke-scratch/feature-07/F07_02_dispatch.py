# Pattern: see .smoke-scratch/README.md
"""feature-07 / folder-views / Dispatch + Templates (DP1-DP5 + TP1-TP4).

Walks each depth (0, 1, 2, 3, 5, 10, 11) and asserts (a) the right
template fires for that depth via depth-unique markers in the
response HTML, and (b) the template's surface contract (heading,
breadcrumb, button label) is intact. DP5 (depth-11 -> 400) is also
covered in `F07_10_acceptance.py` AC3.
"""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    # Build a chain to depth 10 so we can probe 0, 1, 2, 3, 5, 10.
    chain = ["P", "M", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10"]
    for i in range(1, len(chain) + 1):
        client.post(
            "/api/folders",
            json={"parent": "/".join(chain[: i - 1]), "name": chain[i - 1]},
        )

    def _get(path: str) -> tuple[int, str]:
        r = client.get(path)
        return r.status_code, r.get_data(as_text=True)

    # --- DP1 / TP1: depth 0 -> folder_root.html. ------------------------
    status, html = _get("/ui/folder/")
    assert status == 200, f"DP1: GET /ui/folder/ must return 200, got {status}"
    assert ">Projects</h2>" in html, (
        "DP1 / TP1: depth-0 must render folder_root.html (heading 'Projects')"
    )
    assert "+ New project" in html, (
        "TP1: folder_root.html must render the `+ New project` button"
    )

    # --- DP2 / TP2: depth 1 -> folder_project.html. ---------------------
    status, html = _get("/ui/folder/P")
    assert status == 200, f"DP2: GET /ui/folder/P must return 200, got {status}"
    assert ">P</h2>" in html, (
        "DP2 / TP2: depth-1 must render folder_project.html (heading shows project name)"
    )
    # Breadcrumb back to root.
    assert 'hx-get="/ui/folder/"' in html and ">Projects</a>" in html, (
        "TP2: folder_project.html must render a breadcrumb anchor back to root "
        "('Projects' -> /ui/folder/)"
    )
    assert "+ New module" in html, (
        "TP2: folder_project.html must render the `+ New module` button"
    )

    # --- DP3 / TP3: depth 2 -> folder_module.html. ----------------------
    status, html = _get("/ui/folder/P/M")
    assert status == 200, f"DP3: GET /ui/folder/P/M must return 200, got {status}"
    assert ">M</h2>" in html, (
        "DP3 / TP3: depth-2 must render folder_module.html (heading shows module name)"
    )
    assert 'hx-get="/ui/folder/"' in html and 'hx-get="/ui/folder/P"' in html, (
        "TP3: folder_module.html must render breadcrumb 'Projects / P /' with both "
        "anchors carrying the right hx-get"
    )
    assert "+ Sub-folder" in html and "+ Create test case" in html, (
        "TP3: folder_module.html must render BOTH `+ Sub-folder` and "
        "`+ Create test case` buttons"
    )

    # --- DP4 / TP4: depth 3..10 -> folder_subfolder.html. ---------------
    for depth in (3, 5, 10):
        path = "/".join(chain[:depth])
        status, html = _get(f"/ui/folder/{path}")
        assert status == 200, (
            f"DP4 (depth {depth}): GET /ui/folder/{path} must return 200, got {status}"
        )
        leaf = chain[depth - 1]
        assert f">{leaf}</h2>" in html, (
            f"DP4 / TP4 (depth {depth}): folder_subfolder.html must render the "
            f"leaf {leaf!r} as the heading"
        )
        # Breadcrumb has one anchor per ancestor (depth-1 ancestors).
        for i in range(1, depth):
            ancestor_path = "/".join(chain[:i])
            assert f'hx-get="/ui/folder/{ancestor_path}"' in html, (
                f"DP4 / TP4 (depth {depth}): folder_subfolder.html breadcrumb must "
                f"carry an anchor to ancestor {ancestor_path!r}"
            )
        assert "+ Sub-folder" in html and "+ Create test case" in html, (
            f"TP4 (depth {depth}): folder_subfolder.html must render BOTH "
            f"`+ Sub-folder` and `+ Create test case` buttons"
        )

    # --- DP5: depth > MAX_FOLDER_DEPTH -> 400 bad_request. --------------
    status, html = _get("/ui/folder/" + "/".join(chain) + "/extra11")
    assert status == 400, (
        f"DP5: GET /ui/folder/<11 segments> must return 400, got {status}"
    )
print("PASS  DP1-DP5 + TP1-TP4: each depth dispatches to the right template with the documented surface")
