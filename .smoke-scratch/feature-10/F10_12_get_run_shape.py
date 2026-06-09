"""3.G — GET /api/runs/<project>/<group>/<file_name> exposes the exact
shape the SSE comparator needs.

The client's diskJson is built from { name, description, results: [
{file_path, result, remark} ] } — same projection used for the
baseline. This smoke confirms the JSON response carries those fields
verbatim so the equality compare works."""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    app = create_app(data_root=root)
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_file(["Alpha", "Checkout", "a"], description="a")
    s.create_run_group("Alpha", "release-1")
    s.create_run(
        project="Alpha", group="release-1", name="Smoke", file_name="smoke",
        case_paths=["Alpha/Checkout/a.feature"],
        description="hello",
    )
    s.update_run_result(
        project="Alpha", group="release-1", file_name="smoke.yaml",
        case_path="Alpha/Checkout/a.feature",
        result="PASSED", remark="green",
    )

    client = app.test_client()
    r = client.get("/api/runs/Alpha/release-1/smoke.yaml")
    assert r.status_code == 200, r.status_code
    body = r.get_json()
    # Required keys for the comparator.
    for k in ("name", "description", "results", "created_at"):
        assert k in body, f"missing key: {k}"
    assert body["name"] == "Smoke"
    assert body["description"] == "hello"
    assert isinstance(body["results"], list) and len(body["results"]) == 1
    r0 = body["results"][0]
    for k in ("file_path", "result", "remark"):
        assert k in r0, f"missing result key: {k}"
    assert r0["file_path"] == "Alpha/Checkout/a.feature"
    assert r0["result"] == "PASSED"
    assert r0["remark"] == "green"
    # `missing` is a UI-only concern; the JSON API must NOT leak it.
    assert "missing" not in r0, "JSON API should not expose tombstone flag"
    print("PASS 3.G GET /api/runs returns the shape the comparator depends on")
