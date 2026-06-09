"""2.a-partial — Initial tab strip: 'Directory' tab is active (slate-800
border + bold text); 'Test run' tab is inactive (transparent border)."""
import re
import tempfile, pathlib
from app import create_app

with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    client = app.test_client()
    r = client.get("/")
    html = r.get_data(as_text=True)

    # Tab strip exists.
    assert 'id="sidebar-tabs"' in html

    # Directory tab is active.
    m_dir = re.search(r'<button[^>]*data-sidebar-tab="tree"[^>]*>', html)
    assert m_dir, "Directory tab button missing"
    dir_btn = m_dir.group(0)
    assert "border-slate-800" in dir_btn, f"Directory tab should be active: {dir_btn}"
    assert "font-medium" in dir_btn

    # Test-run tab is inactive.
    m_run = re.search(r'<button[^>]*data-sidebar-tab="test-run"[^>]*>', html)
    assert m_run, "Test-run tab button missing"
    run_btn = m_run.group(0)
    assert "border-transparent" in run_btn, f"Test-run tab should be inactive: {run_btn}"
    assert "border-slate-800" not in run_btn

    # Collapse button + resize handle wired.
    assert "tmsToggleSidebarCollapse()" in html
    assert "tmsStartSidebarResize" in html
    assert "tmsSwitchSidebarTab" in html

    print("PASS 2.a initial tab strip state correct")
