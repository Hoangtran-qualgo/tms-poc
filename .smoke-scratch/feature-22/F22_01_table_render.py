"""feature-22 / shared folder table exposes sort and scenario filter hooks."""

from pathlib import Path
from tempfile import TemporaryDirectory

from app import create_app


with TemporaryDirectory() as td:
    app = create_app(data_root=Path(td))
    storage = app.extensions["storage"]
    storage.create_folder(["project"])
    storage.create_folder(["project", "module"])
    storage.create_folder(["project", "module", "branch"])
    storage.create_file(
        ["project", "module", "zebra.feature"], scenario_name="Checkout payment"
    )
    storage.create_file(
        ["project", "module", "branch", "alpha.feature"], scenario_name="Sign in"
    )
    client = app.test_client()
    try:
        module_html = client.get("/ui/folder/project/module").get_data(as_text=True)
        branch_html = client.get(
            "/ui/folder/project/module/branch"
        ).get_data(as_text=True)
    finally:
        app.extensions["watcher"].stop()

for html, file_name, scenario_name in (
    (module_html, "zebra.feature", "Checkout payment"),
    (branch_html, "alpha.feature", "Sign in"),
):
    assert 'data-role="scenario-filter"' in html
    assert 'data-role="file-sort"' in html
    assert 'data-role="file-sort-header" aria-sort="ascending"' in html
    assert 'data-sort-direction="asc"' in html
    assert f'data-file-name="{file_name}"' in html
    assert f'data-scenario-name="{scenario_name}"' in html

print("PASS  F22_01: module and nested tables render sort/filter hooks")
