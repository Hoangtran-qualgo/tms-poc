"""Spike: stable kind IDs remain separate from editable display labels."""
import pathlib
import tempfile

from app.errors import EnumsParseError
from app.gherkin_io import parse_feature, serialize_feature
from app.models import Feature, Scenario, Step
from app.storage import Storage


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    storage = Storage(root)
    storage.create_folder(["Project"])
    assert storage.read_project_enums("Project") == {"components": {}}, (
        "new projects persist only a kind identifier; no kind label exists"
    )
    storage.write_project_enums(
        "Project", {"priority": {"p0": "Priority zero"}}
    )
    assert storage.read_project_enums("Project") == {
        "priority": {"p0": "Priority zero"}
    }, "current vocabulary exposes entry labels only"

    feature = Feature(
        description="",
        scenario=Scenario(
            name="Scenario", steps=[Step(keyword="Given", text="a step")]
        ),
        enums={"priority": "p0"},
    )
    source = serialize_feature(feature)
    assert source.startswith("# enum.priority: p0\n"), (
        "kind identifier is written into every assigned feature directive"
    )
    assert parse_feature(source).enums == {"priority": "p0"}, (
        "kind identifier round-trips through the feature format"
    )
    print("PASS kind is persisted in enums.yaml and assigned feature directives")

    try:
        storage._parse_project_enums(
            b"priority:\n  label: Priority\n  entries:\n    - p0: Priority zero\n"
        )
    except EnumsParseError:
        pass
    else:
        raise AssertionError(
            "current enums.yaml schema has no place for a kind display label"
        )
print("PASS current schema rejects a kind-label metadata shape")


js = (REPO_ROOT / "app" / "static" / "08_enums_manager.js").read_text()
assert "enums-add-kind-form" in js, (
    "Add kind must use the inline template form instead of a native prompt"
)
assert "_buildAddEntryForm(kind)" in js, (
    "Add entry must use an inline form instead of a native prompt"
)
assert "this.state.kindLabels[kind]" in js, (
    "manager must keep display labels separate from stable kind IDs"
)
print("PASS manager uses inline create forms and separate display-label state")
