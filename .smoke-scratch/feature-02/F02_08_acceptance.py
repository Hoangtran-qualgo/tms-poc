# Pattern: see .smoke-scratch/README.md
"""feature-02 / storage-core / Acceptance criteria (AC1-AC5)."""
import os
import pathlib
import tempfile
import threading

from app import storage as storage_mod
from app.storage import Storage, TEMP_FILE_RE, cleanup_orphan_temp_files


# --- AC1: reads/writes/renames stay inside data root ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])
    s.create_file(["proj", "mod", "x.feature"], "desc")

    bad_paths = [
        (["..", "etc"],                   "parent traversal"),
        (["proj", "..", ".."],            "double parent traversal"),
        ("/etc/passwd",                   "absolute string"),
    ]
    ops: list[tuple[str, callable]] = [
        ("read_feature",  lambda p: s.read_feature(p)),
        ("read_raw",      lambda p: s.read_raw(p)),
        ("write_raw",     lambda p: s.write_raw(p, "Feature: x\n  Scenario: y\n")),
        ("create_file",   lambda p: s.create_file(p, "desc")),
        ("create_folder", lambda p: s.create_folder(p)),
        ("delete_file",   lambda p: s.delete_file(p)),
        ("delete_folder", lambda p: s.delete_folder(p)),
    ]
    for path, label in bad_paths:
        for op_name, op in ops:
            try:
                op(path)
            except ValueError:
                continue
            except (FileNotFoundError, OSError):
                # Some ops (read_*) may raise FileNotFoundError if validation
                # is bypassed (e.g. a clean ".." that resolves to root). That
                # would be a leak; flag it.
                raise AssertionError(
                    f"AC1[{op_name}/{label}]: must raise ValueError, got non-ValueError"
                )
            else:
                raise AssertionError(
                    f"AC1[{op_name}/{label}]: must raise ValueError for {path!r}"
                )

    # rename_file source containing "..".
    try:
        s.rename_file(["proj", "..", "x.feature"], "y.feature")
    except ValueError:
        pass
    else:
        raise AssertionError("AC1[rename_file]: must reject '..' in source path")
print(f"PASS  AC1: reads/writes/renames stay inside data root ({len(ops) * len(bad_paths)} sub-cases + rename)")


# --- AC2: crash mid-write leaves target byte-identical; temp recovered by boot scan ---
class SimulatedCrash(Exception):
    pass

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])
    s.create_file(["proj", "mod", "x.feature"], "version_one_description")

    target = root / "proj" / "mod" / "x.feature"
    pre_crash_bytes = target.read_bytes()

    # Simulate a process kill BETWEEN fsync and os.replace (no unlink runs).
    # We monkey-patch os.replace to (a) leak the temp file deliberately by
    # snapshotting it and (b) raise an uncaught BaseException that the
    # storage layer cannot mask.
    real_replace = os.replace
    leaked_temp: dict = {}

    def kill_before_replace(src, dst):
        # Copy the temp aside (it's about to be unlinked by the except clause).
        leaked_temp["path"] = pathlib.Path(src)
        leaked_temp["bytes"] = pathlib.Path(src).read_bytes()
        raise SimulatedCrash("kill -9 between fsync and os.replace")

    storage_mod.os.replace = kill_before_replace
    try:
        try:
            s.write_raw(
                ["proj", "mod", "x.feature"],
                "Feature: version_two\n\n  Scenario: y\n    Given step\n",
            )
        except SimulatedCrash:
            pass
        else:
            raise AssertionError("AC2: SimulatedCrash must propagate")
    finally:
        storage_mod.os.replace = real_replace

    # Target byte-identical to pre-crash state.
    post_crash_bytes = target.read_bytes()
    assert post_crash_bytes == pre_crash_bytes, (
        "AC2: target must be byte-identical to pre-crash state after failed write"
    )

    # Re-plant the leaked temp (simulating that the kill prevented the
    # except-clause unlink from running). The boot scan must recover it.
    leaked_path = leaked_temp["path"]
    leaked_path.write_bytes(leaked_temp["bytes"])
    assert leaked_path.exists(), "AC2 setup: leaked temp must exist before boot scan"
    assert TEMP_FILE_RE.match(leaked_path.name), (
        f"AC2 setup: leaked temp {leaked_path.name!r} must match TEMP_FILE_RE"
    )

    count = cleanup_orphan_temp_files(root)
    assert count >= 1, f"AC2: boot scan must recover at least 1 temp file, got {count}"
    assert not leaked_path.exists(), "AC2: leaked temp must be unlinked by boot scan"
print("PASS  AC2: crash mid-write leaves target byte-identical; boot scan recovers temp")


# --- AC3: concurrent saves serialise; last-write-wins by lock release order ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])
    s.create_file(["proj", "mod", "race.feature"], "initial")

    target = root / "proj" / "mod" / "race.feature"
    content_a = "Feature: writer_a\n\n  Scenario: a\n    Given a\n"
    content_b = "Feature: writer_b\n\n  Scenario: b\n    Given b\n"
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def writer(content: str) -> None:
        try:
            barrier.wait(timeout=2.0)
            s.write_raw(["proj", "mod", "race.feature"], content)
        except BaseException as e:
            errors.append(e)

    t1 = threading.Thread(target=writer, args=(content_a,))
    t2 = threading.Thread(target=writer, args=(content_b,))
    t1.start(); t2.start()
    t1.join(timeout=3.0); t2.join(timeout=3.0)
    assert not t1.is_alive() and not t2.is_alive(), "AC3: writers deadlocked"
    assert errors == [], f"AC3: writers errored {errors}"

    final = target.read_text()
    # Last-write-wins: one of the two contents must be entirely present
    # (no torn / interleaved bytes).
    assert final in (content_a, content_b), (
        f"AC3: concurrent saves produced torn write, final={final!r}"
    )
print("PASS  AC3: concurrent saves serialise; last-write-wins (one content survives intact)")


# --- AC4: rename/move/duplicate never deadlock under any src/dst combination ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    s.create_folder(["proj"])
    s.create_folder(["proj", "src_mod"])
    s.create_folder(["proj", "dst_mod"])
    for n in range(6):
        s.create_file(["proj", "src_mod", f"f{n}.feature"], "desc")

    threads: list[threading.Thread] = []
    barrier = threading.Barrier(6)
    errors: list[BaseException] = []

    def do_rename(n: int) -> None:
        try:
            barrier.wait(timeout=2.0)
            # Rename f<n> -> r<n>; locks include both src and dst keys.
            s.rename_file(["proj", "src_mod", f"f{n}.feature"], f"r{n}.feature")
        except BaseException as e:
            errors.append(e)

    def do_move(n: int) -> None:
        try:
            barrier.wait(timeout=2.0)
            s.move_file(
                ["proj", "src_mod", f"r{n}.feature"],
                ["proj", "dst_mod"],
            )
        except BaseException as e:
            errors.append(e)

    # First pass: 6 concurrent renames (each picks dual locks).
    threads = [threading.Thread(target=do_rename, args=(n,)) for n in range(6)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=5.0)
    assert all(not t.is_alive() for t in threads), "AC4: rename pass deadlocked"
    assert errors == [], f"AC4: rename errors {errors}"

    # Second pass: 6 concurrent moves to a different parent.
    threads = [threading.Thread(target=do_move, args=(n,)) for n in range(6)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=5.0)
    assert all(not t.is_alive() for t in threads), "AC4: move pass deadlocked"
    assert errors == [], f"AC4: move errors {errors}"
print("PASS  AC4: rename + move passes complete without deadlock under concurrent load")


# --- AC5: _mark_write + TEMP_FILE_RE suppress storage's own writes ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])

    # Storage-side half 1: every successful mutation marks the target so the
    # watcher's `was_recently_written` check suppresses the target-modify event.
    s.create_file(["proj", "mod", "sup.feature"], "desc")
    target = root / "proj" / "mod" / "sup.feature"
    assert s.was_recently_written(str(target)), (
        "AC5: target must be marked recent so watcher suppresses modify event"
    )

    # Storage-side half 2: the temp file used during the write matches
    # TEMP_FILE_RE so the watcher (which imports the same regex) ignores
    # the create + delete events for the temp.
    captured_temp: dict = {}
    real_replace = os.replace

    def capture(src, dst):
        captured_temp["name"] = pathlib.Path(src).name
        return real_replace(src, dst)

    storage_mod.os.replace = capture
    try:
        s.write_raw(
            ["proj", "mod", "sup.feature"],
            "Feature: y\n\n  Scenario: s\n    Given step\n",
        )
    finally:
        storage_mod.os.replace = real_replace

    assert TEMP_FILE_RE.match(captured_temp["name"]), (
        f"AC5: temp name {captured_temp['name']!r} must match the shared TEMP_FILE_RE"
        " so the watcher filters its events"
    )
print("PASS  AC5: storage marks target as recent AND uses TEMP_FILE_RE-matching temps (watcher-suppression contract)")
