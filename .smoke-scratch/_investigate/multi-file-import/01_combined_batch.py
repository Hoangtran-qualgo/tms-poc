"""Spike: existing storage accepts a case list flattened from many sources."""
import pathlib
import tempfile

from app.errors import ImportValidationError
from app.gherkin_io import split_feature_source
from app.storage import Storage


SOURCE_A = "Feature: A\n  Scenario: Alpha\n    Given alpha\n"
SOURCE_B = "Feature: B\n  Scenario: Beta\n    Given beta\n"


with tempfile.TemporaryDirectory() as td:
    storage = Storage(pathlib.Path(td))
    storage.create_folder(["project"])
    storage.create_folder(["project", "module"])
    items = [
        ("alpha", split_feature_source(SOURCE_A)[0]),
        ("beta", split_feature_source(SOURCE_B)[0]),
    ]
    assert storage.import_feature_cases(["project", "module"], items) == [
        "project/module/alpha.feature",
        "project/module/beta.feature",
    ], "combined sources must create cases in one transaction"
    print("PASS combined source cases reuse existing storage import")


with tempfile.TemporaryDirectory() as td:
    storage = Storage(pathlib.Path(td))
    storage.create_folder(["project"])
    storage.create_folder(["project", "module"])
    duplicate_items = [
        ("first", split_feature_source(SOURCE_A)[0]),
        ("second", split_feature_source(SOURCE_A)[0]),
    ]
    try:
        storage.import_feature_cases(["project", "module"], duplicate_items)
    except ImportValidationError:
        pass
    else:
        raise AssertionError("cross-source duplicate scenario must abort")
    assert not storage.list_folder(["project", "module"])["features"], (
        "failed cross-source pre-flight must write no cases"
    )
    print("PASS cross-source duplicate aborts before any write")
