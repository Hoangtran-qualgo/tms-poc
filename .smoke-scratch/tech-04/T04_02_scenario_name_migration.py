# Pattern: see .smoke-scratch/README.md
"""tech-04 / testcase-detail-revamp / D1 -- scenario-name backfill migration.

Exercises scripts/backfill_scenario_names.py:migrate() over a fixture set:
  A. empty scenario name + single-line description -> name = description;
     description left unchanged.
  B. empty scenario name + multi-line description  -> name = newlines joined
     with " / "; description left unchanged (newlines intact).
  C. already-named scenario                        -> untouched (idempotent).
  D. empty scenario name + empty description        -> untouched (nothing to move).
Then: re-running migrate() is a no-op (every file now skipped).
"""
import importlib.util
import pathlib
import tempfile

from app import create_app
from app.models import Scenario, Step


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "backfill_scenario_names", REPO_ROOT / "scripts" / "backfill_scenario_names.py"
)
_mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mig)


def _set(s, path, *, description=None, name=None, steps=True):
    """Read a feature, mutate selected fields, write it back."""
    f = s.read_feature(path)
    if description is not None:
        f.description = description
    if name is not None:
        f.scenario.name = name
    if steps:
        f.scenario = Scenario(
            kind="scenario", name=f.scenario.name,
            steps=[Step(keyword="Given", text="a step")],
        )
    s.write_feature(path, f)


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    app = create_app(data_root=root)
    s = app.extensions["storage"]
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Mod"])

    # A: single-line description, empty name.
    s.create_file(["Alpha", "Mod", "a.feature"], "Checkout with card")
    _set(s, "Alpha/Mod/a.feature", name="")
    # B: multi-line description, empty name.
    s.create_file(["Alpha", "Mod", "b.feature"], "Line one\nLine two\nLine three")
    _set(s, "Alpha/Mod/b.feature", name="")
    # C: already named.
    s.create_file(["Alpha", "Mod", "c.feature"], "Some description")
    _set(s, "Alpha/Mod/c.feature", name="Existing name")
    # D: empty description + empty name.
    s.create_file(["Alpha", "Mod", "d.feature"], "")
    _set(s, "Alpha/Mod/d.feature", name="")

    migrated, skipped, errored = _mig.migrate(s)

    assert not errored, f"no file should error, got {errored}"
    assert sorted(migrated) == ["Alpha/Mod/a.feature", "Alpha/Mod/b.feature"], (
        f"only A + B should migrate, got {sorted(migrated)}"
    )
    assert sorted(skipped) == ["Alpha/Mod/c.feature", "Alpha/Mod/d.feature"], (
        f"C (named) + D (empty desc) should skip, got {sorted(skipped)}"
    )
    print("PASS  D1: migrate moves only unnamed + non-empty-description files")

    # A: name == description; description unchanged.
    a = s.read_feature("Alpha/Mod/a.feature")
    assert a.scenario.name == "Checkout with card", a.scenario.name
    assert a.description == "Checkout with card", a.description
    print("PASS  D1: single-line description copied to scenario name verbatim")

    # B: newlines joined with " / "; description keeps its newlines.
    b = s.read_feature("Alpha/Mod/b.feature")
    assert b.scenario.name == "Line one / Line two / Line three", b.scenario.name
    assert b.description == "Line one\nLine two\nLine three", repr(b.description)
    print("PASS  D1: multi-line description joined with ' / ' for the name")

    # C: untouched.
    c = s.read_feature("Alpha/Mod/c.feature")
    assert c.scenario.name == "Existing name", c.scenario.name
    assert c.description == "Some description", c.description
    print("PASS  D1: already-named scenario left untouched")

    # D: untouched (still empty name + empty description).
    d = s.read_feature("Alpha/Mod/d.feature")
    assert d.scenario.name == "", d.scenario.name
    assert d.description == "", d.description
    print("PASS  D1: empty-description file left untouched")

    # Idempotence: a second pass migrates nothing.
    migrated2, skipped2, errored2 = _mig.migrate(s)
    assert migrated2 == [], f"second pass must migrate nothing, got {migrated2}"
    assert len(skipped2) == 4, f"all four files should skip on re-run, got {skipped2}"
    print("PASS  D1: migration is idempotent (re-run migrates nothing)")
