"""S2.3 + S2.4 + S2.5 + S2.6 smoke — enums lifecycle through Storage.

Covers:
- S2.3 init_project_enums: writes exact bytes, returns parsed dict,
  refuses to overwrite, refreshes cache.
- S2.4 create_folder auto-init: project-create writes both folder and
  enums.yaml; module-create does NOT spawn a new enums.yaml.
- S2.5 _cross_check_enums: known kind+key passes; unknown kind / key
  rejected with 422 (ValidationError); missing-file with non-empty
  enums rejected; all-empty enums skip the cross-check entirely (no
  exception even when file missing); label-rename in YAML is a no-op.
- S2.6 list_tree filter: enums.yaml does NOT appear under the project.
"""
import pathlib
import tempfile

from app.errors import NameConflictError, ValidationError
from app.gherkin_io import serialize_feature
from app.models import Feature, Scenario, Step
from app.storage import Storage


def _mk_feature(enums: dict | None = None) -> Feature:
    return Feature(
        description="Smoke",
        scenario=Scenario(
            kind="scenario",
            name="s",
            steps=[Step(keyword="Given", text="x")],
        ),
        enums=dict(enums or {}),
    )


# ===========================================================================
# S2.4 — create_folder auto-init
# ===========================================================================
with tempfile.TemporaryDirectory() as td:
    s = Storage(pathlib.Path(td))
    s.create_folder(["Alpha"])
    enums_file = pathlib.Path(td) / "Alpha" / "enums.yaml"
    assert enums_file.exists(), "project create must auto-write enums.yaml"
    assert enums_file.read_bytes() == b"components:\n", enums_file.read_bytes()
    # Module creation must NOT write a new enums.yaml.
    s.create_folder(["Alpha", "Checkout"])
    assert not (pathlib.Path(td) / "Alpha" / "Checkout" / "enums.yaml").exists()
    # Sub-folder either.
    s.create_folder(["Alpha", "Checkout", "Deep"])
    assert not (
        pathlib.Path(td) / "Alpha" / "Checkout" / "Deep" / "enums.yaml"
    ).exists()
    print("PASS  S2.4 create_folder auto-init: project only, exact bytes")

# ===========================================================================
# S2.3 — init_project_enums
# ===========================================================================
with tempfile.TemporaryDirectory() as td:
    s = Storage(pathlib.Path(td))
    # Pre-create a project WITHOUT the auto-init (simulating a legacy
    # project) by hand-mkdir'ing the folder.
    (pathlib.Path(td) / "Legacy").mkdir()
    result = s.init_project_enums("Legacy")
    assert result == {"components": {}}, result
    target = pathlib.Path(td) / "Legacy" / "enums.yaml"
    assert target.read_bytes() == b"components:\n", target.read_bytes()
    # Second call must conflict.
    try:
        s.init_project_enums("Legacy")
    except NameConflictError as e:
        assert "enums.yaml" in e.message, e.message
        assert e.path == "Legacy/enums.yaml", e.path
    else:
        raise AssertionError("second init must raise NameConflictError")
    # Init for a missing project must raise FileNotFoundError.
    try:
        s.init_project_enums("Nope")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("init on missing project must raise FileNotFoundError")
    print("PASS  S2.3 init_project_enums: writes default, refuses overwrite, "
          "raises on missing project")

# ===========================================================================
# S2.6 — list_tree filter
# ===========================================================================
with tempfile.TemporaryDirectory() as td:
    s = Storage(pathlib.Path(td))
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    tree = s.list_tree()
    project = tree["children"][0]
    assert project["name"] == "Alpha"
    child_names = [c["name"] for c in project["children"]]
    assert "enums.yaml" not in child_names, child_names
    assert "Checkout" in child_names, child_names
    print("PASS  S2.6 list_tree hides enums.yaml from project subtree")

# ===========================================================================
# S2.5 — _cross_check_enums (via write_feature)
# ===========================================================================
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    s.create_folder(["Alpha"])
    s.create_folder(["Alpha", "Checkout"])
    # Seed a vocabulary
    (root / "Alpha" / "enums.yaml").write_bytes(
        b"components:\n"
        b"  - login: Login by credential\n"
        b"  - login_by_SSO: Login by SSO\n"
        b"priorities:\n"
        b"  - p0: Blocker\n"
    )
    # Seed an existing file
    seed = _mk_feature()
    feature_path = ["Alpha", "Checkout", "a.feature"]
    s.create_file(feature_path, description="initial")

    # 5a: Known kind + key → passes
    s.write_feature(feature_path, _mk_feature(enums={"components": "login"}))
    print("PASS  S2.5a write_feature with known (kind, key) passes")

    # 5b: Unknown kind → 422 ValidationError
    try:
        s.write_feature(feature_path, _mk_feature(enums={"team": "frontend"}))
    except ValidationError as e:
        assert e.field == "enums[team]", e.field
        assert "Unknown enum kind 'team'" in e.message, e.message
    else:
        raise AssertionError("unknown kind must raise ValidationError")
    print("PASS  S2.5b unknown kind raises ValidationError(enums[team])")

    # 5c: Unknown key for known kind → 422
    try:
        s.write_feature(feature_path, _mk_feature(enums={"components": "bogus"}))
    except ValidationError as e:
        assert e.field == "enums[components]", e.field
        assert "Unknown enum key 'bogus'" in e.message, e.message
    else:
        raise AssertionError("unknown key must raise ValidationError")
    print("PASS  S2.5c unknown key raises ValidationError(enums[components])")

    # 5d: All-empty enums on a feature → cross-check skipped (no file read).
    # Prove it by setting a tripwire: temporarily replace the YAML with
    # malformed content; if the cross-check still skips, the save passes.
    yaml_path = root / "Alpha" / "enums.yaml"
    backup = yaml_path.read_bytes()
    yaml_path.write_bytes(b"components: [unterminated\n")
    s._invalidate_enums_cache("Alpha")
    s.write_feature(feature_path, _mk_feature(enums={"components": ""}))
    yaml_path.write_bytes(backup)
    s._invalidate_enums_cache("Alpha")
    print("PASS  S2.5d all-empty enums skip the cross-check (no YAML read)")

    # 5e: Label-rename in YAML is a no-op for cross-check (keys only).
    yaml_path.write_bytes(
        b"components:\n"
        b"  - login: Sign in by credential\n"  # label renamed; key preserved
        b"  - login_by_SSO: Login by SSO\n"
        b"priorities:\n"
        b"  - p0: Blocker\n"
    )
    import os
    new_mtime_ns = os.stat(yaml_path).st_mtime_ns + 2_000_000_000
    os.utime(yaml_path, ns=(new_mtime_ns, new_mtime_ns))
    s.write_feature(feature_path, _mk_feature(enums={"components": "login"}))
    print("PASS  S2.5e label rename in enums.yaml does not break existing key save")

# 5f: Missing-file rule
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    s = Storage(root)
    # Hand-create a legacy project (NO enums.yaml).
    (root / "Legacy").mkdir()
    (root / "Legacy" / "Mod").mkdir()
    s.create_file(["Legacy", "Mod", "a.feature"], description="legacy")
    try:
        s.write_feature(
            ["Legacy", "Mod", "a.feature"],
            _mk_feature(enums={"components": "anything"}),
        )
    except ValidationError as e:
        assert e.field == "enums", e.field
        assert "no enums.yaml" in e.message.lower(), e.message
        assert "Initialize enums file" in e.message, e.message
    else:
        raise AssertionError("missing-file rule must reject non-empty enums save")
    # And the all-empty save still passes on the same legacy project.
    s.write_feature(
        ["Legacy", "Mod", "a.feature"],
        _mk_feature(enums={"components": ""}),
    )
    print("PASS  S2.5f missing-file rule: non-empty enums rejected, empty passes")
