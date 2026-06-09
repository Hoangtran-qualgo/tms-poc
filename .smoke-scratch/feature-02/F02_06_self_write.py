# Pattern: see .smoke-scratch/README.md
"""feature-02 / storage-core / Self-write bookkeeping (SW1-SW2)."""
import pathlib
import tempfile
import time

from app.storage import RECENT_WRITE_TTL_SECONDS, Storage


# --- SW1: every successful mutation records target AND target.parent ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)

    def _check(label: str, target: pathlib.Path) -> None:
        assert s.was_recently_written(str(target)), (
            f"SW1[{label}]: target {target} not marked recent"
        )
        assert s.was_recently_written(str(target.parent)), (
            f"SW1[{label}]: target.parent {target.parent} not marked recent"
        )

    # create_folder (depth 1 = project; parent is data root).
    s.create_folder(["P"])
    _check("create_folder depth 1", root / "P")

    # create_folder (depth 2 = module).
    s.create_folder(["P", "M"])
    _check("create_folder depth 2", root / "P" / "M")

    # create_file.
    s.create_file(["P", "M", "a.feature"], "desc")
    _check("create_file", root / "P" / "M" / "a.feature")

    # write_feature (re-save).
    feat = s.read_feature(["P", "M", "a.feature"])
    s.write_feature(["P", "M", "a.feature"], feat)
    _check("write_feature", root / "P" / "M" / "a.feature")

    # write_raw.
    s.write_raw(
        ["P", "M", "a.feature"],
        "Feature: x\n\n  Scenario: y\n    Given step\n",
    )
    _check("write_raw", root / "P" / "M" / "a.feature")

    # rename_file (marks BOTH source and target).
    s.rename_file(["P", "M", "a.feature"], "b.feature")
    _check("rename_file (dst)", root / "P" / "M" / "b.feature")
    assert s.was_recently_written(str(root / "P" / "M" / "a.feature")), (
        "SW1[rename_file src]: source path not marked recent"
    )

    # duplicate_file.
    s.duplicate_file(["P", "M", "b.feature"], "c.feature")
    _check("duplicate_file", root / "P" / "M" / "c.feature")

    # delete_file.
    s.delete_file(["P", "M", "c.feature"])
    assert s.was_recently_written(str(root / "P" / "M" / "c.feature")), (
        "SW1[delete_file]: deleted path not marked recent"
    )
    assert s.was_recently_written(str(root / "P" / "M")), (
        "SW1[delete_file]: parent not marked recent"
    )
print("PASS  SW1: every successful mutation records target AND target.parent")


# --- SW2: entries expire after RECENT_WRITE_TTL_SECONDS; opportunistic cleanup ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    s.create_folder(["Q"])
    target_str = str(root / "Q")

    # Immediately after the write the entry is live.
    assert s.was_recently_written(target_str), "SW2: must be recent immediately after write"

    # After TTL elapses + small slack, the entry expires.
    time.sleep(RECENT_WRITE_TTL_SECONDS + 0.1)
    assert not s.was_recently_written(target_str), (
        f"SW2: entry must expire after {RECENT_WRITE_TTL_SECONDS}s"
    )

    # Opportunistic cleanup: an entry > 2*TTL old is removed on the next write.
    # Sleep > 2*TTL (= 1.0s), then trigger any mutation, then verify the stale
    # entry is gone from _recent_writes.
    s.create_folder(["R"])
    stale_key = str(root / "R")
    assert stale_key in s._recent_writes, "SW2: fresh write should be in _recent_writes"

    time.sleep(RECENT_WRITE_TTL_SECONDS * 2 + 0.1)
    s.create_folder(["S"])  # triggers opportunistic cleanup
    assert stale_key not in s._recent_writes, (
        f"SW2: stale entry {stale_key!r} should be cleaned up after a later write"
    )
print("PASS  SW2: entries expire after TTL; opportunistic cleanup on later writes")
