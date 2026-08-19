# Pattern: see .smoke-scratch/README.md
"""feature-19 / enum-kind-label / stable IDs, labels, and inline forms."""
import pathlib
import tempfile

from app import create_app
from app.models import Feature, Scenario, Step
from app.storage import Storage


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def feature_with_component() -> Feature:
    return Feature(
        description="",
        scenario=Scenario(
            name="Scenario", steps=[Step(keyword="Given", text="a step")]
        ),
        enums={"components": "login"},
    )


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    storage = Storage(root)
    storage.create_folder(["Project"])
    storage.create_folder(["Project", "Module"])
    storage.write_project_enums("Project", {"components": {"login": "Login"}})
    storage.create_file(["Project", "Module", "case"], "", scenario_name="Scenario")
    storage.write_feature(
        ["Project", "Module", "case.feature"], feature_with_component()
    )
    enums_before = (root / "Project" / "enums.yaml").read_bytes()
    raw_before = storage.read_raw("Project/Module/case.feature")

    labels = storage.write_project_enum_kind_labels(
        "Project", {"components": "Components"}
    )
    assert labels == {"components": "Components"}, (
        "KL1: custom display label must round-trip"
    )
    assert storage.read_project_enum_kind_labels("Project") == labels, (
        "KL1: read must return the saved display label"
    )
    assert (root / "Project" / "enums.yaml").read_bytes() == enums_before, (
        "KL1: display-label write must not change the existing vocabulary schema"
    )
    assert storage.read_raw("Project/Module/case.feature") == raw_before, (
        "KL1: display-label write must not rewrite stable feature directives"
    )
    assert "# enum.components: login" in raw_before, (
        "KL1: stable kind ID must remain in the feature directive"
    )
    print("PASS  KL1: display label persists separately; enums.yaml and feature IDs stay unchanged")

    labels = storage.write_project_enum_kind_labels(
        "Project", {"components": "components"}
    )
    assert labels == {"components": "components"}, (
        "KL2: stable ID must be the legacy fallback label"
    )
    assert not (root / "Project" / "enum-kind-labels.yaml").exists(), (
        "KL2: default labels must not require a metadata file"
    )
    print("PASS  KL2: legacy projects fall back to the stable kind ID")


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    storage = Storage(root)
    storage.create_folder(["Project"])
    storage.write_project_enums("Project", {"components": {}, "sprint": {}})
    storage.write_project_enum_kind_labels(
        "Project", {"components": "Components", "sprint": "Sprint"}
    )
    storage.write_project_enums("Project", {"components": {}})
    assert storage.read_project_enum_kind_labels("Project") == {
        "components": "Components"
    }, "KL3: removing a kind must prune its display-label metadata"
    storage.clear_project_enums("Project")
    assert storage.read_project_enum_kind_labels("Project") == {
        "components": "components"
    }, "KL3: Clear must reset display labels with the vocabulary"
    print("PASS  KL3: removed kinds and Clear prune display-label metadata")


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    storage = Storage(root)
    storage.create_folder(["Project"])
    storage.write_project_enums("Project", {"components": {}, "sprint": {}})
    client = create_app(data_root=root).test_client()

    response = client.put(
        "/api/enums/Project/kind-labels",
        json={"components": "Components", "sprint": "Sprint"},
    )
    assert response.status_code == 200, (
        f"KL4: label PUT must return 200, got {response.status_code}"
    )
    assert response.get_json() == {"components": "Components", "sprint": "Sprint"}, (
        "KL4: label PUT response must return current display labels"
    )
    response = client.put(
        "/api/enums/Project/kind-labels",
        json={"components": "Components"},
    )
    assert response.status_code == 422, (
        "KL4: label PUT must reject a map missing a current kind"
    )
    print("PASS  KL4: label API requires one non-empty label per current kind")

    html = client.get("/ui/enums/Project").get_data(as_text=True)
    assert '"components": "Components"' in html, (
        "KL5: manager payload must include persisted kind labels"
    )
    assert 'id="enums-add-kind-form"' in html, (
        "KL5: manager must render the inline Add kind form"
    )
    assert 'id="enums-new-kind-id"' in html, (
        "KL5: inline Add kind form must identify the stable kind ID"
    )
    assert 'id="enums-new-kind-label"' in html, (
        "KL5: inline Add kind form must collect a display label"
    )
    print("PASS  KL5: manager renders label state and inline Add kind fields")


manager_js = (REPO_ROOT / "app" / "static" / "08_enums_manager.js").read_text()
for forbidden in [
    'window.prompt("New kind name (snake_case identifier):")',
    'window.prompt("New entry key (identifier; dash allowed):")',
    'window.prompt("Label for this entry:")',
]:
    assert forbidden not in manager_js, (
        f"IC1: inline create flow must not keep native prompt {forbidden!r}"
    )
for expected in [
    "_buildAddEntryForm(kind)",
    "this.state.kindLabels[kind]",
    "/kind-labels",
    "if (!ENUM_ID_RE.test(name))",
    "if (!ENUM_KEY_RE.test(key))",
]:
    assert expected in manager_js, (
        f"IC1: inline create/label flow must retain {expected!r}"
    )
print("PASS  IC1: kinds and entries use inline forms; IDs remain client-validated")
