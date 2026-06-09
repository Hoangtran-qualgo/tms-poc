# Pattern: see .smoke-scratch/README.md
"""feature-05 / testcase-crud / Filename normalisation (FN1).

Route-layer assertions; the storage-half of FN1 (`_normalize_filename`
behaviour at the storage primitive level) lives in feature-02's
F02_01_path_discipline.py (PD4).
"""
import pathlib
import tempfile

from app import create_app


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})

    # --- FN1 on CREATE: auto-append .feature when extension omitted --------
    r = client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "no_ext", "description": "seed"},
    )
    assert r.status_code == 201, (
        f"FN1 create: extension-less file_name must succeed with auto-append, "
        f"got {r.status_code} body={r.get_data(as_text=True)!r}"
    )
    assert (root / "Alpha" / "Mod" / "no_ext.feature").is_file(), (
        "FN1 create: extension-less file_name='no_ext' must land as 'no_ext.feature'"
    )

    # --- FN1 on CREATE: case-insensitive .feature extension accepted -------
    for variant in ("Upper.FEATURE", "Mixed.FeAtUrE"):
        r = client.post(
            "/api/files",
            json={"parent": "Alpha/Mod", "file_name": variant, "description": "seed"},
        )
        assert r.status_code == 201, (
            f"FN1 create: case-insensitive extension {variant!r} must succeed, "
            f"got {r.status_code}"
        )
        assert (root / "Alpha" / "Mod" / variant).is_file(), (
            f"FN1 create: case-insensitive ext must preserve case verbatim on disk; "
            f"expected {variant!r}"
        )

    # --- FN1 on CREATE: non-.feature extension rejected with 400 -----------
    for bad in ("bad.txt", "bad.yaml", "bad.md", "bad.feature.txt"):
        r = client.post(
            "/api/files",
            json={"parent": "Alpha/Mod", "file_name": bad, "description": "seed"},
        )
        assert r.status_code == 400, (
            f"FN1 create: non-.feature extension {bad!r} must return 400, "
            f"got {r.status_code}"
        )
        assert r.get_json()["error"]["code"] == "bad_request", (
            f"FN1 create: rejection of {bad!r} must carry error.code='bad_request'"
        )
        # Confirm nothing landed on disk.
        assert not (root / "Alpha" / "Mod" / bad).exists(), (
            f"FN1 create: rejected name {bad!r} must NOT appear on disk"
        )
print("PASS  FN1 (create): auto-append on no-ext; case-insensitive .feature accepted; non-.feature -> 400")


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "source", "description": "seed"},
    )

    # --- FN1 on RENAME: auto-append, case-insensitive accept, non-.feature reject ---
    r = client.patch(
        "/api/files/Alpha/Mod/source.feature/rename",
        json={"file_name": "renamed_no_ext"},
    )
    assert r.status_code == 200, (
        f"FN1 rename: extension-less new_name must succeed with auto-append, got {r.status_code}"
    )
    assert (root / "Alpha" / "Mod" / "renamed_no_ext.feature").is_file(), (
        "FN1 rename: extension-less new_name must land as '<name>.feature'"
    )
    assert not (root / "Alpha" / "Mod" / "source.feature").exists(), (
        "FN1 rename: source must be gone after rename"
    )

    # Non-.feature rejected.
    r = client.patch(
        "/api/files/Alpha/Mod/renamed_no_ext.feature/rename",
        json={"file_name": "no.txt"},
    )
    assert r.status_code == 400, (
        f"FN1 rename: non-.feature new_name must return 400, got {r.status_code}"
    )
    # Source preserved on rejection.
    assert (root / "Alpha" / "Mod" / "renamed_no_ext.feature").is_file(), (
        "FN1 rename: source must be preserved when rename is rejected"
    )

    # Case-insensitive accept.
    r = client.patch(
        "/api/files/Alpha/Mod/renamed_no_ext.feature/rename",
        json={"file_name": "Cased.FEATURE"},
    )
    assert r.status_code == 200, (
        f"FN1 rename: case-insensitive .feature must succeed, got {r.status_code}"
    )
    assert (root / "Alpha" / "Mod" / "Cased.FEATURE").is_file(), (
        "FN1 rename: case-insensitive ext must preserve case verbatim"
    )
print("PASS  FN1 (rename): same normalisation rules as create")


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    client = app.test_client()
    client.post("/api/folders", json={"name": "Alpha"})
    client.post("/api/folders", json={"parent": "Alpha", "name": "Mod"})
    client.post(
        "/api/files",
        json={"parent": "Alpha/Mod", "file_name": "source", "description": "seed"},
    )

    # --- FN1 on DUPLICATE: same three rules --------------------------------
    r = client.post(
        "/api/files/Alpha/Mod/source.feature/duplicate",
        json={"file_name": "dup_no_ext"},
    )
    assert r.status_code == 201, (
        f"FN1 duplicate: extension-less new_name must succeed with auto-append, got {r.status_code}"
    )
    assert (root / "Alpha" / "Mod" / "dup_no_ext.feature").is_file(), (
        "FN1 duplicate: extension-less new_name must land as '<name>.feature'"
    )
    # Source preserved (duplicate is a COPY, not a move).
    assert (root / "Alpha" / "Mod" / "source.feature").is_file(), (
        "FN1 duplicate: source must remain after duplicate"
    )

    # Non-.feature rejected.
    r = client.post(
        "/api/files/Alpha/Mod/source.feature/duplicate",
        json={"file_name": "dup.txt"},
    )
    assert r.status_code == 400, (
        f"FN1 duplicate: non-.feature new_name must return 400, got {r.status_code}"
    )

    # Case-insensitive accept.
    r = client.post(
        "/api/files/Alpha/Mod/source.feature/duplicate",
        json={"file_name": "Cased.FEATURE"},
    )
    assert r.status_code == 201, (
        f"FN1 duplicate: case-insensitive .feature must succeed, got {r.status_code}"
    )
    assert (root / "Alpha" / "Mod" / "Cased.FEATURE").is_file()
print("PASS  FN1 (duplicate): same normalisation rules as create")
