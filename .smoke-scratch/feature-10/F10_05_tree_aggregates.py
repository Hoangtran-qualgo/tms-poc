"""2.d — Test run tab aggregates across projects; projects without
test-run/ are omitted."""
import tempfile, pathlib
from app import create_app
from app.storage import Storage

with tempfile.TemporaryDirectory() as td:
    app = create_app(data_root=pathlib.Path(td))
    s = Storage(pathlib.Path(td))
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    s.create_run_group("Alpha", "release-1")
    s.create_run(project="Alpha", group="release-1", name="Sprint A",
                 file_name="sprint-a", case_paths=["Alpha/Checkout/pay.feature"])

    s.create_folder(["Beta"])
    s.create_folder(["Beta", "Login"])
    s.create_run_group("Beta", "qa-cycle")
    s.create_run(project="Beta", group="qa-cycle", name="Cycle 1",
                 file_name="cycle-1", case_paths=["Beta/Login/sso.feature"])

    s.create_folder(["Gamma"])  # no runs, must be omitted

    client = app.test_client()
    r = client.get("/ui/test-run-tree")
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)

    # Both Alpha and Beta visible; Gamma omitted.
    assert ">Alpha<" in html, "Alpha missing"
    assert ">Beta<" in html, "Beta missing"
    assert ">Gamma<" not in html, "Gamma should be omitted (no test-run/)"

    # Groups + runs both rendered.
    assert "release-1" in html, "Alpha group missing"
    assert "qa-cycle" in html, "Beta group missing"
    assert "sprint-a.yaml" in html, "Alpha run leaf missing"
    assert "cycle-1.yaml" in html, "Beta run leaf missing"

    # Each leaf has a /ui/run/... hx-get.
    assert 'hx-get="/ui/run/Alpha/release-1/sprint-a.yaml"' in html, "Alpha leaf URL wrong"
    assert 'hx-get="/ui/run/Beta/qa-cycle/cycle-1.yaml"' in html, "Beta leaf URL wrong"

    print("PASS 2.d Test run tab aggregates across projects, omits empties")
