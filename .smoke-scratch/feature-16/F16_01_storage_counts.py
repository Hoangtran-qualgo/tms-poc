# Pattern: see .smoke-scratch/README.md
"""feature-16 / storage scenario aggregation."""
from pathlib import Path
from tempfile import TemporaryDirectory

from app.storage import Storage


FEATURE_AUTO = """@AUTO
Feature: All scenarios

Scenario: First
  Given first

Scenario: Second
  Given second
"""

SCENARIO_AUTO = """Feature: Mixed scenarios

@aUtO
Scenario: Automated
  Given automated

Scenario: Manual
  Given manual
"""

MALFORMED = """Feature: Broken

Scenario: Broken
  Given
"""


with TemporaryDirectory() as td:
    root = Path(td)
    branch = root / "project" / "module" / "branch"
    branch.mkdir(parents=True)
    (branch / "feature-auto.feature").write_text(FEATURE_AUTO, encoding="utf-8")
    (branch / "scenario-auto.feature").write_text(SCENARIO_AUTO, encoding="utf-8")
    (branch / "broken.feature").write_text(MALFORMED, encoding="utf-8")
    (root / "project" / "module" / "manual.feature").write_text(
        "Feature: Manual\n\nScenario: Manual\n  Given manual\n",
        encoding="utf-8",
    )
    (root / "project" / "test-run").mkdir()
    (root / "project" / "test-run" / "hidden.feature").write_text(
        FEATURE_AUTO, encoding="utf-8"
    )

    tree = Storage(root).list_tree()
    project_node = tree["children"][0]
    module_node = project_node["children"][0]
    branch_node = module_node["children"][0]

    assert project_node["counts"] == {"total": 6, "auto": 3, "non_auto": 3}, (
        "TC1: project count must recursively sum scenarios, auto, and non-auto"
    )
    assert module_node["counts"] == {"total": 6, "auto": 3, "non_auto": 3}, (
        "TC2: module count must recursively sum scenarios, auto, and non-auto"
    )
    assert branch_node["counts"] == {"total": 5, "auto": 3, "non_auto": 2}, (
        "TC3: branch count must include feature-level and scenario-level auto"
    )
    assert module_node["counts"]["total"] == (
        module_node["counts"]["auto"] + module_node["counts"]["non_auto"]
    ), "TC4: count arithmetic must satisfy total == auto + non_auto"
    assert not any(
        child.get("path") == "project/test-run"
        for child in project_node["children"]
    ), "TC5: reserved test-run folder must remain hidden from directory tree"

print("PASS  TC1-TC5: recursive scenario counts, tag inheritance, malformed fallback, project count")
