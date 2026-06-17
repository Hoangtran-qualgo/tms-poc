"""T10-06 — tree auto-expand path derivation (D6, phase 10a).

file -> ancestor folders excl. the leaf; folder -> prefixes incl. self; typed
folder under <p>/test-run -> test-run tab + empty directory-tree expand.
"""
import tempfile, pathlib, re, json
from app import create_app
from app.storage import Storage


def expand_paths(h: str):
    m = re.search(r"window\.TMS_EXPAND_PATHS = (\[[^\]]*\]);", h)
    assert m, "TMS_EXPAND_PATHS global missing"
    return json.loads(m.group(1))


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s = Storage(root)
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    s.create_file(["Alpha", "Mod", "x.feature"], scenario_name="does a thing")
    s.create_run_group("Alpha", "g1")
    c = app.test_client()
    NAV = {"Sec-Fetch-Mode": "navigate"}

    h = c.get("/ui/file/Alpha/Mod/x.feature", headers=NAV).get_data(as_text=True)
    assert expand_paths(h) == ["Alpha", "Alpha/Mod"], expand_paths(h)
    print("PASS file -> parent ancestor prefixes (leaf dropped)")

    h = c.get("/ui/folder/Alpha/Mod", headers=NAV).get_data(as_text=True)
    assert expand_paths(h) == ["Alpha", "Alpha/Mod"], expand_paths(h)
    print("PASS folder -> prefixes incl. self")

    # 10b: a typed folder now carries the TYPED tree's ancestors (consumed by
    # tmsTypedExpand, not the directory tree).
    h = c.get("/ui/folder/Alpha/test-run/g1", headers=NAV).get_data(as_text=True)
    assert 'window.TMS_ACTIVE_TAB = "test-run"' in h
    assert expand_paths(h) == ["Alpha", "Alpha/test-run/g1"], expand_paths(h)
    print("PASS typed test-run group folder -> test-run tab + typed expand (10b)")
