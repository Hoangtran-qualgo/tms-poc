# Pattern: see .smoke-scratch/README.md
"""feature-12 / quality-report / S2 -- report/ is a hidden reserved area.

Asserts:
- The report/ folder never appears in the Directory tree nor the project
  module listing (it joins test-run in RESERVED_DEPTH2_NAMES).
- The generic folder API cannot create/collide with report/ (409).
- list_report_tree surfaces the report via its dedicated channel.
"""
import tempfile, pathlib

from app import create_app
from app.storage import Storage
from app.models import Report
from app.errors import NameConflictError


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]

    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "mod"])
    s.create_report("Alpha", "inv", Report(type="tag_inventory", title="smoke",
                                            tag="smoke", scope="Alpha/mod"))

    # 1. Hidden from the Directory tree.
    tree = s.list_tree()
    alpha = next(c for c in tree["children"] if c["name"] == "Alpha")
    names = [c["name"] for c in alpha["children"]]
    assert "report" not in names, names
    assert "mod" in names, names

    # 2. Hidden from the project module listing.
    modules = s.list_folder(["Alpha"])["modules"]
    assert "report" not in modules, modules

    # 3. Generic folder API rejects the reserved name (409).
    try:
        s.create_folder(["Alpha", "report"])
        raise AssertionError("create_folder must reject the reserved 'report' area")
    except NameConflictError:
        pass

    # 4. Surfaced via the dedicated report tree.
    rtree = s.list_report_tree()
    ralpha = next(c for c in rtree["children"] if c["name"] == "Alpha")
    leaves = {leaf["file_name"]: leaf for leaf in ralpha["children"]}
    assert "inv.yaml" in leaves, leaves
    assert leaves["inv.yaml"]["report_type"] == "tag_inventory"
    assert leaves["inv.yaml"]["title"] == "smoke"

print("PASS  F12_11: report/ hidden from tree + modules; 409 on generic create; report tree lists it")
