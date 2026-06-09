"""3.C — GET /ui/run/<project>/<group>/<file_name> renders run_editor.html
read-only with breadcrumb, header buttons, name / description, results
rows, and the + Add test case button."""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s: Storage = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_run_group("Alpha", "release-1")
    s.create_run(
        project="Alpha", group="release-1", name="Smoke A",
        file_name="smoke-a",
        case_paths=["Alpha/Checkout/pay.feature", "Alpha/Checkout/refund.feature"],
        description="Sanity sweep before deploy.",
    )
    # Flip one row so the select's `selected` attribute is observable.
    s.update_run_result(
        project="Alpha", group="release-1", file_name="smoke-a.yaml",
        case_path="Alpha/Checkout/pay.feature",
        result="PASSED", remark="green",
    )

    client = app.test_client()
    r = client.get("/ui/run/Alpha/release-1/smoke-a.yaml")
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)

    # Editor root + data-* identity
    assert 'id="run-editor"' in html
    assert 'data-project="Alpha"' in html
    assert 'data-group="release-1"' in html
    assert 'data-file-name="smoke-a.yaml"' in html

    # Breadcrumb segments
    assert 'hx-get="/ui/folder/Alpha"' in html
    assert 'hx-get="/ui/folder/Alpha/test-run"' in html
    assert 'hx-get="/ui/folder/Alpha/test-run/release-1"' in html

    # Header controls
    assert 'id="btn-run-reload"' in html
    assert 'id="btn-run-save"' in html
    assert 'id="run-dirty-indicator"' in html
    assert 'id="run-saved-indicator"' in html

    # Name / description / created_at
    assert 'value="Smoke A"' in html
    assert "Sanity sweep before deploy." in html
    assert "Created " in html  # plus the timestamp

    # Both results rows present, with file_path link to /ui/file/...
    assert 'data-file-path="Alpha/Checkout/pay.feature"' in html
    assert 'data-file-path="Alpha/Checkout/refund.feature"' in html
    assert 'hx-get="/ui/file/Alpha/Checkout/pay.feature"' in html

    # Add-case button
    assert 'id="btn-run-add-case"' in html
    print("PASS 3.C run editor renders shell + rows")
