"""Directory tree: every level lists all folders above all files.

Pins the "Test-case directory tree: folders above files within each folder"
item (IN-PROGRESS Must-have, Jun 16 2026). `_tree_children` now does a STABLE
partition (folders on top, files on the bottom) so a folder holding both
sub-folders and `.feature` files no longer interleaves them. Intra-group order
(iterdir order) is preserved — only the folder/file split is asserted here.
"""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s = Storage(root)
    # Alpha/Mod holds both sub-folders and feature files, created interleaved.
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    (root / "Alpha" / "Mod" / "b.feature").write_text("Feature: B\n")
    s.create_folder(["Alpha", "Mod", "Sub1"])
    (root / "Alpha" / "Mod" / "a.feature").write_text("Feature: A\n")
    s.create_folder(["Alpha", "Mod", "Sub2"])
    (root / "Alpha" / "Mod" / "notes.txt").write_text("x\n")

    tree = s.list_tree()
    alpha = next(c for c in tree["children"] if c["name"] == "Alpha")
    mod = next(c for c in alpha["children"] if c["name"] == "Mod")
    types = [c["type"] for c in mod["children"]]

    # All folders precede all files (feature + other) — no interleaving.
    folder_idxs = [i for i, t in enumerate(types) if t == "folder"]
    file_idxs = [i for i, t in enumerate(types) if t in ("feature", "other")]
    assert folder_idxs and file_idxs, f"fixture must mix folders + files: {types}"
    assert max(folder_idxs) < min(file_idxs), (
        f"all folders must sort above all files, got order: "
        f"{[(c['name'], c['type']) for c in mod['children']]}"
    )
    print("PASS folders hoisted above files at the Alpha/Mod level")

    # Both sub-folders land in the folders group (order-insensitive: iterdir
    # order within the group isn't guaranteed and is intentionally preserved).
    folder_names = {c["name"] for c in mod["children"] if c["type"] == "folder"}
    assert folder_names == {"Sub1", "Sub2"}, folder_names
    print("PASS both sub-folders present in the folders group")
