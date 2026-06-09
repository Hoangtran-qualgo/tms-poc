# Pattern: see .smoke-scratch/README.md
"""feature-03 / watcher-and-sse / Event filtering (EF1-EF3).

Drives `_Handler._should_emit` directly with synthetic watchdog events
so the tests are deterministic and don't depend on real FS-event
delivery jitter.
"""
import pathlib
import tempfile

from watchdog.events import (
    DirModifiedEvent,
    FileCreatedEvent,
    FileModifiedEvent,
    FileMovedEvent,
)

from app.storage import Storage
from app.watcher import EventBus, _DebouncedEmitter, _Handler


def _new_handler(root: pathlib.Path) -> tuple[_Handler, Storage]:
    s = Storage(root)
    emitter = _DebouncedEmitter(EventBus(), delay_seconds=0.1)
    return _Handler(s, emitter), s


# --- EF1: drop events whose paths are all outside root, or equal root itself ---
# `_should_emit` inspects path STRINGS only — files need not exist on disk
# and storage need not have written them. Synthesise paths directly so EF3
# (self-write suppression) doesn't shadow the EF1 assertion.
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    handler, _ = _new_handler(root)

    inside = root / "proj" / "mod" / "x.feature"
    outside = pathlib.Path("/tmp") / "definitely-not-under-root.feature"

    # Inside-root event MUST be emitted (the "don't drop" branch).
    assert handler._should_emit(FileModifiedEvent(str(inside))), (
        "EF1: in-root event must NOT be dropped"
    )

    # Outside-root event MUST be dropped.
    assert not handler._should_emit(FileModifiedEvent(str(outside))), (
        "EF1: outside-root event must be dropped"
    )

    # Event whose path EQUALS data root itself — macOS DirModifiedEvent
    # on the watched root. Must be dropped (uninformative).
    assert not handler._should_emit(DirModifiedEvent(str(root))), (
        "EF1: event with path == data root must be dropped"
    )

    # Moved event whose src AND dest are both outside root — dropped.
    other = pathlib.Path("/tmp") / "other.feature"
    assert not handler._should_emit(FileMovedEvent(str(outside), str(other))), (
        "EF1: moved event with both paths outside root must be dropped"
    )

    # Moved event with ONE leg inside root — kept.
    inside2 = root / "proj" / "mod" / "y.feature"
    assert handler._should_emit(FileMovedEvent(str(outside), str(inside2))), (
        "EF1: moved event with at least one leg inside root must be kept"
    )
print("PASS  EF1: drop events all-outside-root or equal-to-root; keep in-root events")


# --- EF2: drop events whose path basename matches TEMP_FILE_RE ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    handler, _ = _new_handler(root)

    tmp_path = root / "proj" / "mod" / "x.feature.tmp.12345.0123456789abcdef"
    final = root / "proj" / "mod" / "x.feature"

    assert not handler._should_emit(FileCreatedEvent(str(tmp_path))), (
        "EF2: file event with TEMP_FILE_RE-matching basename must be dropped"
    )
    # Both legs of the commit-rename: temp -> final AND final -> temp.
    assert not handler._should_emit(FileMovedEvent(str(tmp_path), str(final))), (
        "EF2: rename event where SRC matches TEMP_FILE_RE must be dropped"
    )
    assert not handler._should_emit(FileMovedEvent(str(final), str(tmp_path))), (
        "EF2: rename event where DST matches TEMP_FILE_RE must be dropped"
    )

    # Sanity: a normal .feature path with no temp marker passes EF2.
    plain = root / "proj" / "mod" / "untouched.feature"
    assert handler._should_emit(FileCreatedEvent(str(plain))), (
        "EF2 sanity: a plain .feature path must pass EF2 (regex not over-matching)"
    )
print("PASS  EF2: drop events whose basename matches TEMP_FILE_RE (both rename legs)")


# --- EF3: drop events whose path passes storage.was_recently_written ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    handler, s = _new_handler(root)
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])

    # A storage write marks the target + its parent recent. The watcher
    # must drop events for either.
    s.create_file(["proj", "mod", "self.feature"], "desc")
    target = root / "proj" / "mod" / "self.feature"
    parent = root / "proj" / "mod"

    assert s.was_recently_written(str(target)), "EF3 setup: target must be marked"
    assert s.was_recently_written(str(parent)), "EF3 setup: parent must be marked"

    assert not handler._should_emit(FileModifiedEvent(str(target))), (
        "EF3: event for self-written target must be dropped"
    )
    assert not handler._should_emit(DirModifiedEvent(str(parent))), (
        "EF3: event for self-written parent must be dropped"
    )

    # Rename event where EITHER leg passes was_recently_written -> drop.
    sibling = root / "proj" / "mod" / "sibling.feature"  # not yet written
    assert not handler._should_emit(FileMovedEvent(str(target), str(sibling))), (
        "EF3: rename event with SRC marked recent must be dropped"
    )
    assert not handler._should_emit(FileMovedEvent(str(sibling), str(target))), (
        "EF3: rename event with DST marked recent must be dropped"
    )

    # A path that is NOT marked recent passes EF3.
    # `external.feature` was never written by storage, so it's not in
    # recent_writes regardless of TTL. (No sleep needed.)
    untracked = root / "proj" / "external.feature"
    assert handler._should_emit(FileCreatedEvent(str(untracked))), (
        "EF3 negative: an event for a path that is NOT in recent_writes must pass"
    )
print("PASS  EF3: drop events whose path passes was_recently_written (both rename legs)")
