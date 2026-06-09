# Pattern: see .smoke-scratch/README.md
"""feature-02 / storage-core / Name uniqueness (NU1-NU4)."""
import pathlib
import tempfile

from app.errors import NameConflictError
from app.storage import Storage


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)

    # --- NU1: name-uniqueness scoped to same parent only ---
    # Two projects each containing a module named "mod" — both succeed.
    s.create_folder(["A"])
    s.create_folder(["A", "mod"])
    s.create_folder(["B"])
    s.create_folder(["B", "mod"])  # same name, different parent => OK
    assert (root / "A" / "mod").is_dir(), "NU1: A/mod missing"
    assert (root / "B" / "mod").is_dir(), "NU1: B/mod missing"

    # Same-parent collision IS rejected.
    try:
        s.create_folder(["A", "mod"])
    except NameConflictError:
        pass
    else:
        raise AssertionError("NU1: same-parent same-name folder must conflict")

    # Same for files in different parents.
    s.create_file(["A", "mod", "x.feature"], "desc")
    s.create_file(["B", "mod", "x.feature"], "desc")  # different parent => OK
    assert (root / "A" / "mod" / "x.feature").is_file()
    assert (root / "B" / "mod" / "x.feature").is_file()
    print("PASS  NU1: name-uniqueness scoped to same parent only")


    # --- NU2: enforced via target.exists() — exact-name conflict ---
    # (Case-variation behaviour is host-fs-dependent and NOT asserted here;
    # the spec explicitly defers to the filesystem.)
    s.create_folder(["NU2proj"])
    s.create_folder(["NU2proj", "mod"])
    s.create_file(["NU2proj", "mod", "exact.feature"], "first")
    try:
        s.create_file(["NU2proj", "mod", "exact.feature"], "second")
    except NameConflictError:
        pass
    else:
        raise AssertionError("NU2: exact-name re-create must raise NameConflictError")
    print("PASS  NU2: name-uniqueness enforced via target.exists() (exact-name conflict)")


    # --- NU3: extension matching case-insensitive ---
    # MyTest.FEATURE accepted on any filesystem (no .lower() normalisation on the name).
    s.create_folder(["NU3proj"])
    s.create_folder(["NU3proj", "mod"])
    s.create_file(["NU3proj", "mod", "MyTest.FEATURE"], "desc")
    assert (root / "NU3proj" / "mod" / "MyTest.FEATURE").is_file(), (
        "NU3: MyTest.FEATURE (upper-case ext) must be accepted"
    )
    # Mixed-case extension also accepted.
    s.create_file(["NU3proj", "mod", "Other.FeAtUrE"], "desc")
    assert (root / "NU3proj" / "mod" / "Other.FeAtUrE").is_file(), (
        "NU3: mixed-case extension must be accepted"
    )
    print("PASS  NU3: extension matching is case-insensitive (.FEATURE / .FeAtUrE accepted)")


    # --- NU4: conflicts raise NameConflictError(path, message) ---
    s.create_folder(["NU4proj"])
    s.create_folder(["NU4proj", "mod"])
    s.create_file(["NU4proj", "mod", "dup.feature"], "first")
    try:
        s.create_file(["NU4proj", "mod", "dup.feature"], "second")
    except NameConflictError as e:
        assert hasattr(e, "path") and e.path, f"NU4: error must carry 'path' attribute, got {e!r}"
        assert hasattr(e, "message") and e.message, (
            f"NU4: error must carry 'message' attribute, got {e!r}"
        )
        assert "dup.feature" in e.message, (
            f"NU4: message must mention the conflicting name, got {e.message!r}"
        )
    else:
        raise AssertionError("NU4: conflict must raise NameConflictError")

    # Folder conflicts also use NameConflictError.
    try:
        s.create_folder(["NU4proj", "mod"])
    except NameConflictError as e:
        assert e.path and e.message
    else:
        raise AssertionError("NU4: folder conflict must raise NameConflictError")
    print("PASS  NU4: conflicts raise NameConflictError(path, message)")
