"""T10-02 — active-tab derivation per item route (non-HX shell).

D4: file/folder -> tree; run -> test-run; report -> reports; enums -> enums;
folder under <p>/test-run -> test-run (the typed area is hidden from the
Directory tree). Report/enums non-HX GETs short-circuit to the shell before any
disk read, so no report/enums files are needed here.
"""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s = Storage(root)
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])
    s.create_file(["Alpha", "Mod", "x.feature"], scenario_name="does a thing")
    s.create_run_group("Alpha", "g1")
    s.create_run(project="Alpha", group="g1", name="R1", file_name="run",
                 case_paths=["Alpha/Mod/x.feature"])
    c = app.test_client()

    cases = {
        "/ui/folder/Alpha/Mod": "tree",
        "/ui/file/Alpha/Mod/x.feature": "tree",
        "/ui/folder/Alpha/test-run/g1": "test-run",
        "/ui/run/Alpha/g1/run.yaml": "test-run",
        "/ui/report/Alpha/whatever.yaml": "reports",
        "/ui/enums/Alpha": "enums",
    }
    NAV = {"Sec-Fetch-Mode": "navigate"}
    for url, tab in cases.items():
        h = c.get(url, headers=NAV).get_data(as_text=True)
        assert f'data-active-tab="{tab}"' in h, f"{url} -> data-active-tab {tab}"
        assert f'window.TMS_ACTIVE_TAB = "{tab}"' in h, f"{url} -> TMS_ACTIVE_TAB {tab}"
    print("PASS T10-02 active-tab derivation for all five item routes")
