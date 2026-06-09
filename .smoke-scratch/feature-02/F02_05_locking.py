# Pattern: see .smoke-scratch/README.md
"""feature-02 / storage-core / Locking (LK1-LK3)."""
import gc
import pathlib
import tempfile
import threading
import weakref
from weakref import WeakValueDictionary

from app.storage import Storage, _PathLock


# --- LK1: _lock_for returns _PathLock, kept in WeakValueDictionary ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)

    assert isinstance(s._locks, WeakValueDictionary), (
        f"LK1: _locks must be WeakValueDictionary, got {type(s._locks).__name__}"
    )

    lock = s._lock_for("some/key.feature")
    assert isinstance(lock, _PathLock), f"LK1: must return _PathLock, got {type(lock).__name__}"

    # Same key while a strong ref is held returns the same instance.
    same = s._lock_for("some/key.feature")
    assert lock is same, "LK1: same key must return same lock while held"

    # Weakref-able: drop the strong ref, GC, dict entry should disappear.
    ref = weakref.ref(lock)
    del lock, same
    gc.collect()
    assert ref() is None, "LK1: _PathLock must be weakref-collectable"
    assert "some/key.feature" not in s._locks, (
        "LK1: WeakValueDictionary must drop entry after GC"
    )
print("PASS  LK1: _lock_for returns _PathLock wrapper kept in WeakValueDictionary")


# --- LK2: single-target mutations acquire exactly one (the right) lock ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])
    s.create_file(["proj", "mod", "x.feature"], "first")

    # Externally hold the lock for the target key; a writer must block.
    held = s._lock_for("proj/mod/x.feature")
    held.__enter__()
    result: list[str] = []
    error: list[BaseException] = []

    def writer() -> None:
        try:
            s.write_raw(
                ["proj", "mod", "x.feature"],
                "Feature: y\n\n  Scenario: s\n    Given step\n",
            )
            result.append("done")
        except BaseException as e:  # pragma: no cover - test diagnostics
            error.append(e)

    t = threading.Thread(target=writer)
    t.start()
    t.join(timeout=0.3)
    assert t.is_alive(), "LK2: write must block while target lock is held externally"
    assert result == [], "LK2: writer should not have completed yet"

    held.__exit__(None, None, None)
    t.join(timeout=2.0)
    assert not t.is_alive(), "LK2: writer should unblock after lock release"
    assert error == [], f"LK2: writer raised unexpectedly: {error}"
    assert result == ["done"], "LK2: writer should complete after release"
print("PASS  LK2: single-target mutation blocks on the target's lock and unblocks on release")


# --- LK3: dual-target mutations acquire sorted([src_key, dst_key]) ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])
    s.create_file(["proj", "mod", "Z.feature"], "desc")

    acquisition_order: list[str] = []
    real_lock_for = s._lock_for

    def tracking_lock_for(key: str) -> _PathLock:
        acquisition_order.append(key)
        return real_lock_for(key)

    s._lock_for = tracking_lock_for  # type: ignore[method-assign]
    try:
        # Rename Z -> A. src_key = "proj/mod/Z.feature", dst_key = "proj/mod/A.feature".
        # Naive ordering would acquire src then dst (Z, A). Sorted ordering acquires A, Z.
        s.rename_file(["proj", "mod", "Z.feature"], "A.feature")
    finally:
        s._lock_for = real_lock_for  # type: ignore[method-assign]

    assert len(acquisition_order) == 2, (
        f"LK3: rename_file must acquire exactly 2 locks, got {acquisition_order}"
    )
    assert acquisition_order == sorted(acquisition_order), (
        f"LK3: lock acquisition order must be sorted, got {acquisition_order}"
    )
    src_key = "proj/mod/Z.feature"
    dst_key = "proj/mod/A.feature"
    assert acquisition_order == sorted([src_key, dst_key]), (
        f"LK3: expected sorted({src_key!r}, {dst_key!r}), got {acquisition_order}"
    )

    # Empirical no-deadlock check: N threads doing concurrent two-target ops
    # in opposing directions complete within timeout (would deadlock without sort).
    s.create_file(["proj", "mod", "A2.feature"], "desc")
    s.create_file(["proj", "mod", "B2.feature"], "desc")

    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def dup_a_to_c() -> None:
        try:
            barrier.wait(timeout=2.0)
            s.duplicate_file(["proj", "mod", "A2.feature"], "C2.feature")
        except BaseException as e:
            errors.append(e)

    def dup_b_to_a() -> None:
        try:
            barrier.wait(timeout=2.0)
            # This will fail with NameConflictError because A2 exists,
            # but the failure must come AFTER lock acquisition, not via deadlock.
            try:
                s.duplicate_file(["proj", "mod", "B2.feature"], "A2.feature")
            except Exception:
                pass
        except BaseException as e:
            errors.append(e)

    t1 = threading.Thread(target=dup_a_to_c)
    t2 = threading.Thread(target=dup_b_to_a)
    t1.start(); t2.start()
    t1.join(timeout=3.0); t2.join(timeout=3.0)
    assert not t1.is_alive() and not t2.is_alive(), (
        "LK3: dual-target mutations deadlocked (threads did not complete in 3s)"
    )
    assert errors == [], f"LK3: unexpected errors {errors}"
print("PASS  LK3: dual-target mutations acquire sorted lock order (no deadlock)")
