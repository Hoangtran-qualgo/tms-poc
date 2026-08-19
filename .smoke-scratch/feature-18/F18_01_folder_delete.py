# Pattern: see .smoke-scratch/README.md
"""feature-18 / folder-delete / confirmed UI scope and flow."""
import pathlib
import tempfile
from urllib.parse import quote

from app import create_app


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = "\n".join(
    path.read_text()
    for path in sorted((REPO_ROOT / "app" / "static").glob("*.js"))
)
start = JS.index("function tmsDeleteFolder(")
end = JS.index("\nfunction tmsCreateFile(", start)
DELETE_HANDLER = JS[start:end]

# The confirm flow must name the target, warn about recursive loss, retain an
# API error in the modal, and only refresh both UI surfaces after success.
for expected in [
    'title: "Delete folder"',
    'confirmLabel: "Delete folder"',
    '"Permanently delete " + folderPath',
    '", including all sub-folders and test cases? This cannot be undone."',
    'encodeURIComponent(segment)',
    'fetch("/api/folders/" + encodedPath',
    'method: "DELETE"',
    '"Could not delete folder: " + e.message',
    'tmsRefreshFolder(parentPath)',
    'tmsRefreshTreePane("tree-pane")',
]:
    assert expected in DELETE_HANDLER, (
        f"FD1: tmsDeleteFolder must retain confirmed flow fragment {expected!r}"
    )
assert DELETE_HANDLER.index("close();") < DELETE_HANDLER.index(
    "tmsRefreshFolder(parentPath)"
), "FD1: successful deletion must close the modal before refreshing parent view"
print(
    "PASS  FD1: delete confirmation names recursive loss, retains errors, and "
    "refreshes parent/tree after DELETE"
)


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    storage = app.extensions["storage"]

    chain = [
        "Alpha", "Module", "Branch", "D4", "D5", "D6", "D7", "D8", "D9", "D10"
    ]
    for index, name in enumerate(chain):
        response = client.post(
            "/api/folders",
            json={"parent": "/".join(chain[:index]), "name": name},
        )
        assert response.status_code == 201, (
            f"FD2 setup: folder {name!r} at depth {index + 1} must create, "
            f"got {response.status_code}"
        )
    response = client.post(
        "/api/files",
        json={
            "parent": "Alpha/Module",
            "file_name": "module-case",
            "scenario_name": "Module case",
            "description": "",
        },
    )
    assert response.status_code == 201, "FD3 setup: module test case must create"
    response = client.post(
        "/api/files",
        json={
            "parent": "Alpha/Module/Branch",
            "file_name": "branch-case",
            "scenario_name": "Branch case",
            "description": "",
        },
    )
    assert response.status_code == 201, "FD3 setup: branch test case must create"
    storage.create_run_group("Alpha", "release")

    for path, expected_delete in [
        ("", False),
        ("Alpha", False),
        ("Alpha/Module", True),
        ("Alpha/Module/Branch", True),
        ("/".join(chain), True),
    ]:
        response = client.get("/ui/folder/" + path)
        html = response.get_data(as_text=True)
        assert response.status_code == 200, (
            f"FD2: {path or 'root'} folder view must render 200, got "
            f"{response.status_code}"
        )
        assert ("Delete folder" in html) is expected_delete, (
            f"FD2: delete control scope wrong for {path or 'root'}"
        )
        assert ("tmsDeleteFolder(" in html) is expected_delete, (
            f"FD2: delete handler scope wrong for {path or 'root'}"
        )

    typed_html = client.get("/ui/folder/Alpha/test-run").get_data(as_text=True)
    assert "Delete folder" not in typed_html, (
        "FD2: reserved test-run view must not expose generic folder deletion"
    )
    print(
        "PASS  FD2: only module/branch folder views expose delete; "
        "root/project/typed views do not"
    )

    response = client.post("/api/folders", json={"name": "O'Reilly"})
    assert response.status_code == 201, "FD2 setup: quoted project must create"
    response = client.post(
        "/api/folders", json={"parent": "O'Reilly", "name": "Module"}
    )
    assert response.status_code == 201, (
        "FD2 setup: quoted project module must create"
    )
    quoted_html = client.get(
        "/ui/folder/" + quote("O'Reilly", safe="") + "/Module"
    ).get_data(as_text=True)
    assert 'data-folder-path="O&#39;Reilly/Module"' in quoted_html, (
        "FD2: folder path must be HTML-escaped in the delete button data attribute"
    )
    assert (
        'onclick="tmsDeleteFolder(this.dataset.folderPath, this.dataset.parentPath)"'
        in quoted_html
    ), (
        "FD2: delete button must pass data attributes instead of interpolated "
        "JS values"
    )
    print("PASS  FD2: delete button safely carries escaped folder paths")

    response = client.delete("/api/folders/Alpha/Module")
    assert response.status_code == 204, (
        f"FD3: module DELETE must return 204, got {response.status_code}"
    )
    assert not (root / "Alpha" / "Module").exists(), (
        "FD3: delete must remove selected module, descendant branch, and test cases"
    )
    assert (root / "Alpha" / "enums.yaml").is_file(), (
        "FD3: module delete must preserve project-level enum configuration"
    )
    assert (root / "Alpha" / "test-run" / "release").is_dir(), (
        "FD3: module delete must preserve hidden project typed data"
    )
print(
    "PASS  FD3: selected module DELETE recursively removes its cases but "
    "preserves project siblings"
)
