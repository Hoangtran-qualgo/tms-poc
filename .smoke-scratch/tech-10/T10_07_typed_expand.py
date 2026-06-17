"""T10-07 — typed-tab tree auto-expand path derivation (tech-10 phase 10b).

A browser navigation to a run/report (or a test-run area/group folder) emits
the TYPED tree's folder `data-path` nodes in TMS_EXPAND_PATHS:
  run    /ui/run/<p>/<g>/<f>        -> [<p>, <p>/test-run/<g>]  (test-run tab)
  report /ui/report/<p>/<f>         -> [<p>]                    (reports tab)
  area   /ui/folder/<p>/test-run    -> [<p>]                    (test-run tab)
Non-HX shell short-circuits before any disk read, so no run/report files are
needed.
"""
import tempfile, pathlib, re, json
from app import create_app
from app.storage import Storage


def expand_paths(h: str):
    m = re.search(r"window\.TMS_EXPAND_PATHS = (\[[^\]]*\]);", h)
    assert m, "TMS_EXPAND_PATHS global missing"
    return json.loads(m.group(1))


with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    Storage(pathlib.Path(td)).create_folder(["Alpha"])
    c = app.test_client()
    NAV = {"Sec-Fetch-Mode": "navigate"}

    h = c.get("/ui/run/Alpha/g1/run.yaml", headers=NAV).get_data(as_text=True)
    assert 'window.TMS_ACTIVE_TAB = "test-run"' in h
    assert expand_paths(h) == ["Alpha", "Alpha/test-run/g1"], expand_paths(h)
    print("PASS run -> test-run tab + [project, group-node]")

    h = c.get("/ui/report/Alpha/r.yaml", headers=NAV).get_data(as_text=True)
    assert 'window.TMS_ACTIVE_TAB = "reports"' in h
    assert expand_paths(h) == ["Alpha"], expand_paths(h)
    print("PASS report -> reports tab + [project]")

    h = c.get("/ui/folder/Alpha/test-run", headers=NAV).get_data(as_text=True)
    assert 'window.TMS_ACTIVE_TAB = "test-run"' in h
    assert expand_paths(h) == ["Alpha"], expand_paths(h)
    print("PASS test-run area folder -> test-run tab + [project]")
