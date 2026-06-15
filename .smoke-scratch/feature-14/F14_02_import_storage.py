# Pattern: see .smoke-scratch/README.md
"""feature-14 / import test cases / Phase 2 storage (import_feature_cases).

Exercises Storage.create_feature_file + Storage.import_feature_cases:
all-or-nothing pre-flight (collect-all), 1-level-scope uniqueness (file +
scenario name, case-insensitive), within-batch vs on-disk conflicts,
name/steps required, enums-dropped persisted (bypasses cross-check),
description-blank allowed, Background shared persisted, filename
normalization + forbidden chars, depth/reserved-area rejection, and the
compensating rollback on a mid-write failure.
"""
import pathlib
import tempfile

from app import create_app
from app.errors import ImportValidationError, NameConflictError
from app.gherkin_io import split_feature_source
from app.models import Background, Feature, Scenario, Step


def _feature(name, steps=("Given a step",), description="", bg=()):
    return Feature(
        description=description,
        background=Background(steps=[Step(keyword="Given", text=t) for t in bg]),
        scenario=Scenario(
            kind="scenario",
            name=name,
            steps=[Step(keyword=s.split(" ", 1)[0], text=s.split(" ", 1)[1]) for s in steps],
        ),
    )


with tempfile.TemporaryDirectory() as td:
    s = create_app(data_root=pathlib.Path(td)).extensions["storage"]
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])

    # --- H1: happy multi-write from a real split source -------------------
    src = (
        "@feat\n"
        "Feature: shared desc\n\n"
        "  Background:\n    Given shared setup\n\n"
        "  @a\n  Scenario: alpha case\n    Given a1\n\n"
        "  @b\n  Scenario: beta case\n    Given b1\n"
    )
    feats = split_feature_source(src)
    created = s.import_feature_cases(
        ["proj", "mod"], [("alpha.feature", feats[0]), ("beta", feats[1])]
    )
    assert created == ["proj/mod/alpha.feature", "proj/mod/beta.feature"], (
        f"H1: created paths/order, got {created!r}"
    )
    a = s.read_feature(["proj", "mod", "alpha.feature"])
    b = s.read_feature(["proj", "mod", "beta.feature"])
    assert a.scenario.name == "alpha case" and b.scenario.name == "beta case", "H1: names"
    assert a.description == "shared desc" and b.description == "shared desc", "H1: shared desc"
    assert [st.text for st in a.background.steps] == ["shared setup"], "H1: shared Background persisted"
    assert [st.text for st in b.background.steps] == ["shared setup"], "H1: shared Background persisted"
    assert a.tags == ["feat"] and b.tags == ["feat"], "H1: feature tags shared"
    assert a.scenario.tags == ["a"] and b.scenario.tags == ["b"], "H1: scenario tags kept per-case"
    print("PASS  H1: happy multi-write persists shared desc/Background/tags, names, order")


with tempfile.TemporaryDirectory() as td:
    s = create_app(data_root=pathlib.Path(td)).extensions["storage"]
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])

    # --- H2: enum directives dropped persist + bypass cross-check ---------
    # No enums.yaml in the project; a source carrying an enum directive must
    # still import cleanly because the splitter drops enums.
    feats = split_feature_source(
        "# enum.priority: high\nFeature: f\n\n  Scenario: c\n    Given x\n"
    )
    assert feats[0].enums == {}, "H2: precondition - splitter drops enums"
    s.import_feature_cases(["proj", "mod"], [("c.feature", feats[0])])
    persisted = s.read_raw(["proj", "mod", "c.feature"])
    assert "enum." not in persisted, f"H2: enum directive leaked into file:\n{persisted}"
    print("PASS  H2: dropped enums persist (no directive written) and bypass cross-check")


with tempfile.TemporaryDirectory() as td:
    s = create_app(data_root=pathlib.Path(td)).extensions["storage"]
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])

    # --- H3: blank description allowed; filename auto-.feature ------------
    created = s.import_feature_cases(["proj", "mod"], [("noext", _feature("only"))])
    assert created == ["proj/mod/noext.feature"], f"H3: .feature appended, got {created!r}"
    assert s.read_feature(["proj", "mod", "noext.feature"]).description == "", "H3: blank desc"
    print("PASS  H3: blank description allowed; '.feature' auto-appended")


with tempfile.TemporaryDirectory() as td:
    s = create_app(data_root=pathlib.Path(td)).extensions["storage"]
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])

    # --- C1: scenario name required + steps required (collect-all) --------
    try:
        s.import_feature_cases(
            ["proj", "mod"],
            [
                ("a.feature", _feature("", steps=("Given x",))),     # no name
                ("b.feature", _feature("named", steps=())),           # no steps
            ],
        )
    except ImportValidationError as e:
        joined = " | ".join(e.reasons)
        assert "scenario name is required" in joined, f"C1: name reason, got {e.reasons!r}"
        assert "at least one step" in joined, f"C1: steps reason, got {e.reasons!r}"
        assert len(e.reasons) >= 2, f"C1: collect-all expected >=2 reasons, got {e.reasons!r}"
    else:
        raise AssertionError("C1: must abort on missing name/steps")
    assert s.list_folder(["proj", "mod"])["features"] == [], "C1: zero files written"
    print("PASS  C1: name+steps required, collected together, zero files written")


with tempfile.TemporaryDirectory() as td:
    s = create_app(data_root=pathlib.Path(td)).extensions["storage"]
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])
    s.import_feature_cases(["proj", "mod"], [("Existing.feature", _feature("Existing Scenario"))])

    # --- C2: file-name conflict with existing (case-insensitive) ----------
    try:
        s.import_feature_cases(["proj", "mod"], [("EXISTING.feature", _feature("new name"))])
    except ImportValidationError as e:
        assert "already exists" in " ".join(e.reasons), f"C2: {e.reasons!r}"
    else:
        raise AssertionError("C2: case-insensitive file-name conflict must abort")
    assert len(s.list_folder(["proj", "mod"])["features"]) == 1, "C2: no new file written"

    # --- C3: scenario-name conflict with existing (case-insensitive) ------
    try:
        s.import_feature_cases(["proj", "mod"], [("fresh.feature", _feature("EXISTING scenario"))])
    except ImportValidationError as e:
        assert "scenario name" in " ".join(e.reasons), f"C3: {e.reasons!r}"
    else:
        raise AssertionError("C3: case-insensitive scenario-name conflict must abort")
    assert len(s.list_folder(["proj", "mod"])["features"]) == 1, "C3: no new file written"
    print("PASS  C2/C3: case-insensitive file + scenario name conflicts with existing abort")


with tempfile.TemporaryDirectory() as td:
    s = create_app(data_root=pathlib.Path(td)).extensions["storage"]
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])

    # --- C4: within-batch duplicate file name + scenario name -------------
    try:
        s.import_feature_cases(
            ["proj", "mod"],
            [
                ("dup.feature", _feature("scen one")),
                ("DUP.feature", _feature("scen two")),   # dup file (case-insensitive)
                ("other.feature", _feature("SCEN ONE")),  # dup scenario (case-insensitive)
            ],
        )
    except ImportValidationError as e:
        joined = " | ".join(e.reasons)
        assert "duplicate file name" in joined, f"C4: file dup, got {e.reasons!r}"
        assert "duplicate scenario name" in joined, f"C4: scenario dup, got {e.reasons!r}"
    else:
        raise AssertionError("C4: within-batch duplicates must abort")
    assert s.list_folder(["proj", "mod"])["features"] == [], "C4: zero files written"
    print("PASS  C4: within-batch duplicate file + scenario names (case-insensitive) abort")


with tempfile.TemporaryDirectory() as td:
    s = create_app(data_root=pathlib.Path(td)).extensions["storage"]
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])

    # --- C4b: source file with two scenarios of the SAME name -------------
    # Matches the USER example: split a real source whose scenarios share a
    # name -> the splitter keeps both; import must reject the duplicate.
    dup_src = (
        "Feature: f\n\n"
        "  Scenario: same name\n    Given a1\n\n"
        "  Scenario: same name\n    Given b1\n"
    )
    dup_feats = split_feature_source(dup_src)
    assert len(dup_feats) == 2, "C4b: splitter keeps both duplicate-named scenarios"
    try:
        s.import_feature_cases(
            ["proj", "mod"], [("one.feature", dup_feats[0]), ("two.feature", dup_feats[1])]
        )
    except ImportValidationError as e:
        assert "duplicate scenario name" in " ".join(e.reasons), f"C4b: {e.reasons!r}"
    else:
        raise AssertionError("C4b: duplicate scenario names in the source must abort")
    assert s.list_folder(["proj", "mod"])["features"] == [], "C4b: zero files written"
    print("PASS  C4b: source with two same-named scenarios is rejected (zero files)")


with tempfile.TemporaryDirectory() as td:
    s = create_app(data_root=pathlib.Path(td)).extensions["storage"]
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])

    # --- C5: invalid file name (forbidden char) ---------------------------
    try:
        s.import_feature_cases(["proj", "mod"], [("a/b.feature", _feature("scen"))])
    except ImportValidationError as e:
        assert any("Forbidden" in r or "segment" in r for r in e.reasons), f"C5: {e.reasons!r}"
    else:
        raise AssertionError("C5: forbidden-char file name must abort")
    print("PASS  C5: forbidden-character file name rejected")


with tempfile.TemporaryDirectory() as td:
    s = create_app(data_root=pathlib.Path(td)).extensions["storage"]
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])

    # --- C6: depth + reserved-area rejection ------------------------------
    try:
        s.import_feature_cases(["proj"], [("a.feature", _feature("x"))])
    except ValueError:
        pass
    else:
        raise AssertionError("C6: depth-1 destination must raise ValueError")
    try:
        s.import_feature_cases(["proj", "test-run"], [("a.feature", _feature("x"))])
    except NameConflictError:
        pass
    else:
        raise AssertionError("C6: reserved typed area must raise NameConflictError")
    print("PASS  C6: depth-1 and reserved typed-area destinations rejected")


with tempfile.TemporaryDirectory() as td:
    s = create_app(data_root=pathlib.Path(td)).extensions["storage"]
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])

    # --- R1: compensating rollback on mid-write failure -------------------
    original = s.create_feature_file
    calls = {"n": 0}

    def boom(parts, feature):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("simulated disk failure on 2nd write")
        return original(parts, feature)

    s.create_feature_file = boom
    try:
        s.import_feature_cases(
            ["proj", "mod"],
            [("first.feature", _feature("first")), ("second.feature", _feature("second"))],
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("R1: mid-write failure must propagate")
    finally:
        s.create_feature_file = original
    assert s.list_folder(["proj", "mod"])["features"] == [], (
        "R1: all-or-nothing - already-written file must be rolled back"
    )
    print("PASS  R1: mid-write failure rolls back already-written files (all-or-nothing)")
