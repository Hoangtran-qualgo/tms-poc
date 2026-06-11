"""S4 smoke — GET /ui/enums/<project> renders the manager / Initialize state.

Asserts:
1. An initialised project renders the manager: title, Save + Clear controls,
   the embedded TMS_ENUMS payload (missing:false) and the booted controller.
2. A legacy project renders the Initialize state (missing:true + Initialize
   button), with no Save control.
3. The embedded vocab reflects the on-disk document.
"""
import json
import pathlib
import tempfile

from app import create_app
from app.storage import Storage


# --- 1 + 3. Initialised project → manager view ----------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["Alpha"])
    s.write_project_enums("Alpha", {"components": {"login": "Login"}})
    c = create_app(data_root=root).test_client()

    r = c.get("/ui/enums/Alpha")
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)
    assert "Enums" in html and "Alpha" in html, html
    assert 'id="enums-save-btn"' in html, html
    assert 'id="enums-clear-btn"' in html, html
    assert "tmsEnumsManager.boot()" in html, html
    # The boot guard must be a lexical check: `const tmsEnumsManager` never
    # attaches to window, so `window.tmsEnumsManager` would be undefined and
    # boot() would silently never run (the "+ Add kind" inert-button bug).
    assert "typeof tmsEnumsManager" in html, html
    assert "window.tmsEnumsManager" not in html, html
    assert "missing: false" in html, html
    assert '"login": "Login"' in html, html
    print("PASS  initialised project → manager view with Save/Clear + vocab")

# --- 2. Legacy project → Initialize state ---------------------------------
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    (root / "Legacy").mkdir()
    c = create_app(data_root=root).test_client()

    r = c.get("/ui/enums/Legacy")
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)
    assert 'id="enums-init-btn"' in html, html
    assert "Initialize enums file" in html, html
    assert "missing: true" in html, html
    assert 'id="enums-save-btn"' not in html, "legacy view must not offer Save"
    print("PASS  legacy project → Initialize state, no Save control")
