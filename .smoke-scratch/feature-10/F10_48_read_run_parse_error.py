# Pattern: see .smoke-scratch/README.md
"""feature-10 / test-run / SC4 + SM6 -- malformed YAML surfaces as 422.

SC4/SM6: read_run raises RunParseError(line, column, message) on
     malformed YAML; the API blueprint maps it to HTTP 422 with code
     'run_parse_error'. read_run also raises FileNotFoundError (404)
     for a missing run (the 404 half is also covered by F10_17).

Writes a broken .yaml straight into the group folder (bypassing the
run-write path, which would reject it) so read_run hits a real parse
failure.
"""
import tempfile, pathlib
from app import create_app
from app.storage import Storage
from app.errors import RunParseError

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_run_group("Alpha", "release-1")

    broken = root / "Alpha" / "test-run" / "release-1" / "broken.yaml"
    broken.write_text("name: x\n  : : bad indent :\n\t- nope\n", encoding="utf-8")

    # --- SM6: storage raises RunParseError with locator fields. ---
    try:
        s.read_run("Alpha", "release-1", "broken.yaml")
        raise AssertionError("read_run must raise RunParseError on malformed YAML")
    except RunParseError as e:
        assert hasattr(e, "line") and hasattr(e, "column") and hasattr(e, "message")

    # --- SC4: the API surfaces it as 422 run_parse_error. ---
    client = app.test_client()
    r = client.get("/api/runs/Alpha/release-1/broken.yaml")
    assert r.status_code == 422, (r.status_code, r.get_data(as_text=True))
    env = r.get_json()["error"]
    assert env["code"] == "run_parse_error", env
    assert "line" in env["details"] and "column" in env["details"], env["details"]

print("PASS  SC4+SM6: malformed run YAML -> RunParseError -> HTTP 422 run_parse_error with line/column")
