# Pattern: see .smoke-scratch/README.md
"""feature-02 / storage-core / Atomic write recipe (AW1-AW4)."""
import os
import pathlib
import tempfile

from app import storage as storage_mod
from app.storage import Storage, TEMP_FILE_RE, cleanup_orphan_temp_files


# --- AW1: temp name <target>.tmp.<pid>.<uuid_hex> in same dir as target ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])

    captured = {}
    real_replace = os.replace

    def capture_replace(src, dst):
        captured["src"] = str(src)
        captured["dst"] = str(dst)
        return real_replace(src, dst)

    storage_mod.os.replace = capture_replace
    try:
        s.create_file(["proj", "mod", "aw1.feature"], "desc")
    finally:
        storage_mod.os.replace = real_replace

    src_name = pathlib.Path(captured["src"]).name
    assert TEMP_FILE_RE.match(src_name), (
        f"AW1: temp name {src_name!r} must match TEMP_FILE_RE"
    )
    assert f".tmp.{os.getpid()}." in src_name, (
        f"AW1: temp name must embed pid {os.getpid()}, got {src_name!r}"
    )
    assert pathlib.Path(captured["src"]).parent == pathlib.Path(captured["dst"]).parent, (
        "AW1: temp must live in same directory as target"
    )
print("PASS  AW1: temp name <target>.tmp.<pid>.<uuid_hex> in same dir as target")


# --- AW2: open -> write -> fsync -> close -> os.replace ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])

    fsync_calls = []
    replace_calls = []
    real_fsync = os.fsync
    real_replace = os.replace

    def track_fsync(fd):
        fsync_calls.append(fd)
        return real_fsync(fd)

    def track_replace(src, dst):
        # By the time os.replace runs, fsync must already have happened.
        replace_calls.append((str(src), str(dst), len(fsync_calls)))
        return real_replace(src, dst)

    storage_mod.os.fsync = track_fsync
    storage_mod.os.replace = track_replace
    try:
        s.create_file(["proj", "mod", "aw2.feature"], "desc")
    finally:
        storage_mod.os.fsync = real_fsync
        storage_mod.os.replace = real_replace

    assert len(fsync_calls) >= 1, "AW2: os.fsync must be called during atomic write"
    assert len(replace_calls) == 1, f"AW2: os.replace called {len(replace_calls)}x, expected 1"
    _, _, fsync_count_at_replace = replace_calls[0]
    assert fsync_count_at_replace >= 1, "AW2: fsync must complete BEFORE os.replace"
print("PASS  AW2: open -> write -> fsync -> close -> os.replace sequence")


# --- AW3: on failure, temp is unlinked; original exception propagates ---
class SentinelError(Exception):
    pass

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])

    target_dir = root / "proj" / "mod"
    real_replace = os.replace

    def boom(src, dst):
        raise SentinelError("simulated mid-write crash at os.replace")

    storage_mod.os.replace = boom
    try:
        try:
            s.create_file(["proj", "mod", "aw3.feature"], "desc")
        except SentinelError:
            pass
        else:
            raise AssertionError("AW3: SentinelError must propagate")
    finally:
        storage_mod.os.replace = real_replace

    # Target must not exist (write never committed).
    assert not (target_dir / "aw3.feature").exists(), "AW3: target should not exist on failure"
    # No orphan temp files in target_dir (storage cleaned them up).
    orphans = [p for p in target_dir.iterdir() if TEMP_FILE_RE.match(p.name)]
    assert orphans == [], f"AW3: temp file not unlinked on failure, found {orphans}"
print("PASS  AW3: on failure, temp is unlinked and original exception propagates")


# --- AW4: cleanup_orphan_temp_files unlinks every TEMP_FILE_RE match ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    (root / "proj").mkdir()
    (root / "proj" / "mod").mkdir()

    # Create orphan temps matching the regex at multiple depths.
    orphans = [
        root / "x.feature.tmp.123.abcdef0123456789",
        root / "proj" / "y.feature.tmp.456.fedcba9876543210",
        root / "proj" / "mod" / "z.feature.tmp.789.0011223344556677",
    ]
    for p in orphans:
        p.write_bytes(b"")
    # Real files that must survive.
    keep = [
        root / "proj" / "keep.feature",
        root / "proj" / "mod" / "another.feature",
    ]
    for p in keep:
        p.write_text("Feature: x\n  Scenario: y\n")

    count = cleanup_orphan_temp_files(root)
    assert count == len(orphans), f"AW4: expected count {len(orphans)}, got {count}"
    for p in orphans:
        assert not p.exists(), f"AW4: orphan {p.name} should have been deleted"
    for p in keep:
        assert p.exists(), f"AW4: real file {p.name} must survive cleanup"
print("PASS  AW4: cleanup_orphan_temp_files unlinks every TEMP_FILE_RE match and returns count")
