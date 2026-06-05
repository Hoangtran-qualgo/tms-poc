"""list_folder([project]) modules listing must not include 'test-run'."""
import tempfile, pathlib
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    s = Storage(pathlib.Path(td))
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_run_group("Alpha", "release-1")

    result = s.list_folder(["Alpha"])
    assert result["kind"] == "project", result
    modules = result["modules"]
    assert "Checkout" in modules, modules
    assert "test-run" not in modules, modules
    print("PASS p2-s2 list_folder hides test-run in project view")
