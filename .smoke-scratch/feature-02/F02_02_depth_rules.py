# Pattern: see .smoke-scratch/README.md
"""feature-02 / storage-core / Depth rules (DR1, DR2, DR3a-d)."""
import pathlib
import tempfile

from app.storage import MAX_FOLDER_DEPTH, Storage


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)

    # --- DR1: create_folder requires 1 <= depth <= MAX_FOLDER_DEPTH ---
    try:
        s.create_folder([])
    except ValueError:
        pass
    else:
        raise AssertionError("DR1: depth 0 (empty parts) must raise ValueError")

    s.create_folder(["proj"])  # depth 1 OK
    # Build a chain to MAX_FOLDER_DEPTH.
    chain = ["proj"]
    for i in range(2, MAX_FOLDER_DEPTH + 1):
        chain.append(f"d{i}")
        s.create_folder(chain)  # depth i OK
    assert len(chain) == MAX_FOLDER_DEPTH, f"DR1: chain length {len(chain)} != MAX {MAX_FOLDER_DEPTH}"

    # depth MAX+1 must fail.
    too_deep = chain + ["overflow"]
    try:
        s.create_folder(too_deep)
    except ValueError:
        pass
    else:
        raise AssertionError(f"DR1: depth {MAX_FOLDER_DEPTH + 1} must raise ValueError")
    print(f"PASS  DR1: create_folder requires 1 <= depth <= {MAX_FOLDER_DEPTH}")


    # --- DR2: storage trusts — create_file succeeds at parent depth 1 ---
    # API layer requires parent depth >= 2; storage does NOT enforce.
    # parent = ["trust_proj"] (depth 1), file = ["trust_proj", "x.feature"].
    s.create_folder(["trust_proj"])
    s.create_file(["trust_proj", "x.feature"], "trust test")
    assert (root / "trust_proj" / "x.feature").is_file(), (
        "DR2: storage should TRUST and accept create_file at parent depth 1"
    )
    print("PASS  DR2: storage trusts — create_file succeeds at parent depth 1 (below API min)")


    # --- DR3a: list_folder at depth 0 returns root shape ---
    result = s.list_folder([])
    assert result["kind"] == "root", f"DR3a: kind, got {result.get('kind')!r}"
    assert "projects" in result, f"DR3a: must contain 'projects' key, got keys {list(result)}"
    assert isinstance(result["projects"], list), "DR3a: projects must be a list"
    print("PASS  DR3a: list_folder(depth 0) returns {kind: 'root', projects: [...]}")


    # --- DR3b: list_folder at depth 1 returns project shape ---
    result = s.list_folder(["proj"])
    assert result["kind"] == "project", f"DR3b: kind, got {result.get('kind')!r}"
    assert "modules" in result, f"DR3b: must contain 'modules' key, got keys {list(result)}"
    print("PASS  DR3b: list_folder(depth 1) returns {kind: 'project', modules: [...]}")


    # --- DR3c: list_folder at depth 2 returns module shape ---
    s.create_folder(["d3proj"])
    s.create_folder(["d3proj", "mod"])
    s.create_file(["d3proj", "mod", "a.feature"], "desc")
    s.create_folder(["d3proj", "mod", "sub"])
    result = s.list_folder(["d3proj", "mod"])
    assert result["kind"] == "module", f"DR3c: kind, got {result.get('kind')!r}"
    assert "folders" in result and "features" in result, (
        f"DR3c: must contain 'folders' and 'features', got keys {list(result)}"
    )
    assert "sub" in result["folders"], f"DR3c: missing sub folder, got {result['folders']}"
    assert any(f["file_name"] == "a.feature" for f in result["features"]), (
        f"DR3c: missing a.feature, got {result['features']}"
    )
    print("PASS  DR3c: list_folder(depth 2) returns {kind: 'module', folders, features}")


    # --- DR3d: list_folder at depth 3..MAX returns subfolder shape ---
    s.create_file(["d3proj", "mod", "sub", "b.feature"], "desc")
    result = s.list_folder(["d3proj", "mod", "sub"])
    assert result["kind"] == "subfolder", f"DR3d: kind, got {result.get('kind')!r}"
    assert "folders" in result and "features" in result, (
        f"DR3d: must contain 'folders' and 'features', got keys {list(result)}"
    )
    assert any(f["file_name"] == "b.feature" for f in result["features"]), (
        f"DR3d: missing b.feature, got {result['features']}"
    )
    print("PASS  DR3d: list_folder(depth 3..MAX) returns {kind: 'subfolder', folders, features}")
