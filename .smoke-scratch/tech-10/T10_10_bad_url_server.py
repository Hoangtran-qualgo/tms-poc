"""T10-10 — deep-linking a missing item (tech-10 phase 10c, server half).

A browser navigation to a valid /ui route with a MISSING item returns the shell
(200) so the app frame loads; the #main-pane HX fetch of the same URL then
404s with the `_ui_error_html` snippet, which the client injects (see T10-11).
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
    c = app.test_client()
    NAV = {"Sec-Fetch-Mode": "navigate"}
    HX = {"HX-Request": "true"}

    # Missing run / file / folder under valid routes.
    bad = [
        "/ui/run/Alpha/g1/missing.yaml",
        "/ui/file/Alpha/Mod/missing.feature",
        "/ui/folder/Alpha/Mod/does-not-exist",
    ]
    for url in bad:
        nav = c.get(url, headers=NAV)
        assert nav.status_code == 200 and has_doctype(nav.get_data(as_text=True)), (
            f"browser-nav to {url} must still return the shell (frame loads)"
        )
        hx = c.get(url, headers=HX)
        assert hx.status_code == 404, f"HX fetch of {url} must 404"
        body = hx.get_data(as_text=True)
        assert not has_doctype(body), "404 must be a bare snippet (no shell)"
        assert 'text-red-700' in body, (
            f"404 must carry the _ui_error_html snippet to inject; got {body[:120]!r}"
        )
    print("PASS T10-10 bad item URL: navigate -> shell 200; HX -> 404 error snippet")
