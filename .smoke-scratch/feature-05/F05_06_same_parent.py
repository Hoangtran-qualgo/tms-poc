# Pattern: see .smoke-scratch/README.md
"""feature-05 / testcase-crud / Same-parent / cross-parent (SP1-SP3)."""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "ModA"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "ModB"})  # decoy
    client.post(
        "/api/files",
        json={"parent": "Alpha/ModA", "file_name": "src", "scenario_name": "s", "description": "x"},
    )

    # --- SP1: rename is same-parent by construction ------------------------
    # PATCH /rename body shape contains only `file_name`; a stray `parent`
    # field must be silently ignored -- the renamed file MUST land in the
    # source's parent, not in any caller-supplied parent.
    r = client.patch(
        "/api/files/Alpha/ModA/src.feature/rename",
        json={"file_name": "renamed", "parent": "Alpha/ModB"},  # bogus parent
    )
    assert r.status_code == 200, (
        f"SP1: rename must succeed even with extra body fields, got {r.status_code}"
    )
    assert (root / "Alpha" / "ModA" / "renamed.feature").is_file(), (
        "SP1: rename target must land in the SOURCE parent (Alpha/ModA), "
        "not in the caller-supplied bogus parent (Alpha/ModB)"
    )
    assert not (root / "Alpha" / "ModB" / "renamed.feature").exists(), (
        "SP1: rename must NOT honour a caller-supplied parent field"
    )
print("PASS  SP1: rename is same-parent by construction; bogus parent in body is ignored")


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "ModA"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "ModB"})  # decoy
    client.post(
        "/api/files",
        json={"parent": "Alpha/ModA", "file_name": "src", "scenario_name": "s", "description": "x"},
    )

    # --- SP2: duplicate is same-parent only --------------------------------
    # POST /duplicate body shape contains only `file_name`; a stray `parent`
    # field must be silently ignored -- the copy MUST land in the source's
    # parent, not in any caller-supplied parent.
    r = client.post(
        "/api/files/Alpha/ModA/src.feature/duplicate",
        json={"file_name": "copy", "parent": "Alpha/ModB"},  # bogus parent
    )
    assert r.status_code == 201, (
        f"SP2: duplicate must succeed even with extra body fields, got {r.status_code}"
    )
    assert (root / "Alpha" / "ModA" / "copy.feature").is_file(), (
        "SP2: duplicate copy must land in the SOURCE parent (Alpha/ModA), "
        "not in the caller-supplied bogus parent (Alpha/ModB)"
    )
    assert not (root / "Alpha" / "ModB" / "copy.feature").exists(), (
        "SP2: duplicate must NOT honour a caller-supplied parent field"
    )
    assert (root / "Alpha" / "ModA" / "src.feature").is_file(), (
        "SP2: duplicate must preserve the source file (it's a copy, not a move)"
    )
print("PASS  SP2: duplicate is same-parent only; bogus parent in body is ignored")


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "ModA"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "ModB"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/ModA", "file_name": "src", "scenario_name": "s", "description": "x"},
    )

    # --- SP3: move dest parent MUST differ from source parent --------------
    # Cross-parent move -> 200.
    r = client.patch(
        "/api/files/Alpha/ModA/src.feature/move",
        json={"parent": "Alpha/ModB"},
    )
    assert r.status_code == 200, (
        f"SP3 setup: cross-parent move must succeed, got {r.status_code}"
    )
    assert (root / "Alpha" / "ModB" / "src.feature").is_file()

    # Same-parent move -> 400 bad_request (rejected as no-op intent).
    r = client.patch(
        "/api/files/Alpha/ModB/src.feature/move",
        json={"parent": "Alpha/ModB"},
    )
    assert r.status_code == 400, (
        f"SP3: same-parent move must return 400, got {r.status_code}"
    )
    body = r.get_json()
    assert body and body.get("error", {}).get("code") == "bad_request", (
        f"SP3: same-parent move must carry error.code='bad_request', got {body!r}"
    )
    # The error message names the same-parent reason for caller clarity.
    assert "same as the source" in body["error"]["message"].lower() or (
        "same-parent" in body["error"]["message"].lower()
    ) or ("rename" in body["error"]["message"].lower()), (
        f"SP3: error message should explain the same-parent rejection, "
        f"got {body['error']['message']!r}"
    )
    # File still in source parent (rejection had no side-effects).
    assert (root / "Alpha" / "ModB" / "src.feature").is_file(), (
        "SP3: rejected same-parent move must leave source file untouched"
    )
print("PASS  SP3: move requires distinct destination parent; same-parent -> 400 bad_request")
