"""T10-01 — content-negotiation: non-HX GET -> full shell, HX GET -> fragment.

tech-10 phase 10a (`specs/tech/10-tech-deep-linking-urls-NEW.md`). A top-level
(non-HTMX) GET to an item URL must return base.html (doctype + #main-pane
pointed at that URL); the same URL with HX-Request returns the bare fragment.
"""
import tempfile, pathlib
from app import create_app
from app.storage import Storage


def has_doctype(h: str) -> bool:
    return "<!doctype" in h.lower()


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

    NAV = {"Sec-Fetch-Mode": "navigate"}  # what a browser sends on navigation
    for url in ("/ui/folder/Alpha/Mod",
                "/ui/file/Alpha/Mod/x.feature",
                "/ui/run/Alpha/g1/run.yaml"):
        nav = c.get(url, headers=NAV).get_data(as_text=True)
        hx = c.get(url, headers={"HX-Request": "true"}).get_data(as_text=True)
        prog = c.get(url).get_data(as_text=True)  # headerless (test/programmatic)
        assert has_doctype(nav), f"browser-nav {url} must return the shell"
        assert not has_doctype(hx), f"HX {url} must return a bare fragment"
        assert not has_doctype(prog), (
            f"headerless {url} must stay a fragment (preserved contract)"
        )
        assert 'id="main-pane"' in nav and url in nav, (
            f"shell for {url} must point #main-pane at the same URL"
        )
    print("PASS T10-01 nav->shell, HX->fragment, headerless->fragment")
