"""base.html renders 200 with the new sidebar shell elements."""
import tempfile, pathlib
from app import create_app

with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    client = app.test_client()
    r = client.get("/")
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)

    # Sidebar shell elements present.
    for needle in [
        'id="sidebar"',
        'id="sidebar-tabs"',
        'id="sidebar-collapse-btn"',
        'data-sidebar-tab="tree"',
        'data-sidebar-tab="test-run"',
        'id="tree-pane"',
        'id="test-run-pane"',
        'id="sidebar-resize-handle"',
        'tmsSwitchSidebarTab',
        'tmsToggleSidebarCollapse',
        'tmsStartSidebarResize',
    ]:
        assert needle in html, f"missing: {needle}"

    # Tree pane still server-side included (first paint).
    assert "Tree" in html, "tree.html partial missing"

    print("PASS p2-s7 base.html renders with sidebar shell intact")
