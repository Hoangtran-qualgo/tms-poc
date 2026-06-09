# Pattern: see .smoke-scratch/README.md
"""feature-06 / tree-pane / listing hides atomic-write temp files (condition-coverage gap-closer).

`TEMP_FILE_RE` is well-covered for the boot sweep (`F02_03` AW4) and
the watcher (`F03_01` EF2), but no smoke had ever placed a temp-named
file *inside a listed directory* and asserted the directory listings
omit it. That left the `TEMP_FILE_RE.match(name)` leg of the listing
filters in `Storage._tree_children` (list_tree) and `Storage.list_folder`
unexercised (condition-coverage gap "Pattern B").

A temp file written AFTER `create_app` (so the boot-time
`cleanup_orphan_temp_files` doesn't sweep it) must be filtered out of
both `list_tree()` and `list_folder()` while the real `.feature`
sibling survives.
"""
import tempfile, pathlib
from app import create_app
from app.storage import TEMP_FILE_RE

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s = app.extensions["storage"]

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    s.create_file(["Alpha", "Mod", "real.feature"], "a real description")

    # Drop an atomic-write-style temp next to the real file, post-boot so
    # the orphan sweep can't remove it — the listing filter must hide it.
    temp_name = "real.feature.tmp.99999.deadbeefcafe1234"
    assert TEMP_FILE_RE.match(temp_name), "fixture name must match TEMP_FILE_RE"
    (root / "Alpha" / "Mod" / temp_name).write_bytes(b"partial write")

    # --- list_tree: temp leg True -> filtered; real sibling kept. ---
    tree = s.list_tree()
    alpha = next(c for c in tree["children"] if c["name"] == "Alpha")
    mod = next(c for c in alpha["children"] if c["name"] == "Mod")
    tree_names = {c["name"] for c in mod["children"]}
    assert "real.feature" in tree_names, tree_names
    assert temp_name not in tree_names, f"list_tree must hide the temp file, got {tree_names}"

    # --- list_folder (depth-2 module view): same filter, features list. ---
    listing = s.list_folder(["Alpha", "Mod"])
    feat_names = {f["file_name"] for f in listing["features"]}
    assert "real.feature" in feat_names, feat_names
    assert temp_name not in feat_names, f"list_folder must hide the temp file, got {feat_names}"
    assert temp_name not in listing["folders"], listing["folders"]

print("PASS  Pattern B: list_tree + list_folder filter out atomic-write temp files (real sibling survives)")
