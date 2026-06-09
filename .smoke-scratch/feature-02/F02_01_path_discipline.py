# Pattern: see .smoke-scratch/README.md
"""feature-02 / storage-core / Path discipline (PD1-PD4)."""
import pathlib
import tempfile

from app.storage import Storage


with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)

    # --- PD1: _split accepts list or string, rejects absolute, filters empty ---
    assert Storage._split(["a", "b"]) == ["a", "b"], "PD1: list pass-through failed"
    assert Storage._split("a/b/c") == ["a", "b", "c"], "PD1: string split failed"
    assert Storage._split("a//b") == ["a", "b"], "PD1: empty segments must be filtered from string form"
    try:
        Storage._split("/etc/passwd")
    except ValueError:
        pass
    else:
        raise AssertionError("PD1: absolute path must raise ValueError")
    print("PASS  PD1: _split accepts list/string, rejects absolute, filters empty")


    # --- PD2: _validate_segment rejections ---
    bad = [
        ("",          "empty"),
        (".",         "dot"),
        ("..",        "dot-dot"),
        ("a/b",       "slash"),
        ("a\\b",      "backslash"),
        ("a:b",       "colon"),
        ("a*b",       "star"),
        ("a?b",       "question"),
        ('a"b',       "quote"),
        ("a<b",       "lt"),
        ("a>b",       "gt"),
        ("a|b",       "pipe"),
        ("a\x00b",    "null char"),
        ("a\x1fb",    "control char 0x1F"),
    ]
    for seg, label in bad:
        try:
            Storage._validate_segment(seg)
        except ValueError:
            continue
        raise AssertionError(f"PD2[{label}]: {seg!r} must raise ValueError")
    Storage._validate_segment("normal-name_123.feature")  # sanity
    print(f"PASS  PD2: _validate_segment rejects {len(bad)} sub-cases of bad segments")


    # --- PD3: _resolve stays inside root; escape raises ValueError ---
    inside = s._resolve(["proj", "module"])
    assert inside.is_relative_to(root), f"PD3: inside path not under root, got {inside}"
    # Direct .. escape: blocked by _validate_segment before _resolve even tries.
    try:
        s._resolve(["..", "etc"])
    except ValueError:
        pass
    else:
        raise AssertionError("PD3: '..' escape must raise ValueError")
    print("PASS  PD3: _resolve stays inside data root; escape raises ValueError")


    # --- PD4: .feature extension auto-append + reject other + case-insensitive ---
    (root / "proj").mkdir()
    (root / "proj" / "mod").mkdir()
    # Auto-append when no extension
    s.create_file(["proj", "mod", "auto"], "desc")
    assert (root / "proj" / "mod" / "auto.feature").is_file(), "PD4: .feature not auto-appended"
    # Reject different extension
    try:
        s.create_file(["proj", "mod", "bad.txt"], "desc")
    except ValueError:
        pass
    else:
        raise AssertionError("PD4: .txt must be rejected")
    # Case-insensitive: .FEATURE accepted
    s.create_file(["proj", "mod", "Upper.FEATURE"], "desc")
    assert (root / "proj" / "mod" / "Upper.FEATURE").is_file(), "PD4: .FEATURE not accepted"
    print("PASS  PD4: .feature auto-appended, other extensions rejected, case-insensitive")
