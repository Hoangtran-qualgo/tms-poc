# Pattern: see .smoke-scratch/README.md
"""feature-11 / enums / list_tree enums.yaml filter — is_file() leg (condition-coverage gap-closer).

`Storage._tree_children` hides the project-level enums file with:

    if depth == 1 and name == _ENUMS_FILE_NAME and entry.is_file():
        continue

VS1 (`F11_06`) covers the `is_file() == True` leg (the real
`enums.yaml` FILE is hidden). The `is_file() == False` leg — a
*directory* literally named `enums.yaml` sitting at depth 1 (a module
inside a project) — was never exercised, so the third condition's
False outcome was untested (condition-coverage gap "Pattern C").

A directory named `enums.yaml` must NOT be hidden (it's a folder, not
the project enums file), while the real enums FILE stays hidden.
"""
import tempfile, pathlib
from app import create_app

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s = app.extensions["storage"]

    # Project Beta keeps its auto-init enums.yaml FILE (is_file True leg).
    s.create_folder(["Beta"])
    assert (root / "Beta" / "enums.yaml").is_file()

    # Project Alpha: drop the auto-init FILE, then create a DIRECTORY named
    # enums.yaml at depth 1 (a module). Drives the is_file() leg to False.
    s.create_folder(["Alpha"])
    (root / "Alpha" / "enums.yaml").unlink()
    s.create_folder(["Alpha", "enums.yaml"])
    assert (root / "Alpha" / "enums.yaml").is_dir()

    tree = s.list_tree()
    beta = next(c for c in tree["children"] if c["name"] == "Beta")
    alpha = next(c for c in tree["children"] if c["name"] == "Alpha")

    # --- is_file() True leg: the project enums FILE is hidden (VS1 restated). ---
    assert "enums.yaml" not in {c["name"] for c in beta["children"]}, beta["children"]

    # --- is_file() False leg: a folder named enums.yaml is LISTED. ---
    enums_dir_nodes = [c for c in alpha["children"] if c["name"] == "enums.yaml"]
    assert len(enums_dir_nodes) == 1, alpha["children"]
    assert enums_dir_nodes[0]["type"] == "folder", enums_dir_nodes[0]

print("PASS  Pattern C: enums.yaml FILE hidden (is_file True) but a DIRECTORY named enums.yaml is listed (is_file False)")
