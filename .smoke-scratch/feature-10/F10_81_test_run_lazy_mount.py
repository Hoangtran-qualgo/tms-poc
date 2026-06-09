"""2.h-partial — Initial DOM: #test-run-pane has NO hx-get / hx-trigger
yet (those are added by tmsActivateTestRunPane on first tab click), but
its placeholder text is rendered and it carries the 'hidden' class so the
Directory tree is the default-active panel."""
import re
import tempfile, pathlib
from app import create_app

with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    client = app.test_client()
    r = client.get("/")
    html = r.get_data(as_text=True)

    # Extract the <aside id="test-run-pane" ...> opening tag.
    m = re.search(r'<aside\s+id="test-run-pane"[^>]*>', html)
    assert m, "test-run-pane element missing"
    tag = m.group(0)

    assert "hidden" in tag, f"test-run-pane should start hidden: {tag}"
    assert "hx-get" not in tag, f"test-run-pane must not preload (lazy mount): {tag}"
    assert "hx-trigger" not in tag, f"test-run-pane must not subscribe yet: {tag}"

    # Tree pane is the active one: visible (no 'hidden' class on its <aside>).
    m_tree = re.search(r'<aside\s+id="tree-pane"[^>]*>', html)
    assert m_tree, "tree-pane element missing"
    tree_tag = m_tree.group(0)
    assert "hidden" not in tree_tag, f"tree-pane should be visible by default: {tree_tag}"

    # Placeholder text rendered.
    assert "Loading test runs" in html, "placeholder text missing"

    # JS helper present (function definitions in app.js are not in base.html,
    # so we just check the script tag wiring is present).
    assert 'src="/static/app.js"' in html or "static/app.js" in html

    print("PASS 2.h initial DOM: test-run-pane lazy-mount stub correct")
