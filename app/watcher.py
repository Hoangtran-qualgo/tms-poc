"""Watchdog observer + in-memory pub/sub + ``recent_writes`` TTL set.

Architecture per PLAN.md §7:

- A single :class:`watchdog.observers.Observer` watches the data root
  recursively in its own thread.
- All FS events pass through :class:`_DebouncedEmitter` so a burst (e.g.
  a folder rename touching many files) collapses to a single SSE
  notification after ``DEBOUNCE_SECONDS``.
- Self-write suppression: every successful write inside :class:`~app.storage.Storage`
  records its absolute path with a TTL of
  :data:`~app.storage.RECENT_WRITE_TTL_SECONDS`. The watcher consults
  :meth:`Storage.was_recently_written` before publishing so the SSE channel
  stays quiet during the user's own saves.
- Atomic-write temp files are filtered by the shared regex
  :data:`~app.storage.TEMP_FILE_RE`.
- Subscribers receive a short ``"change"`` string on per-request
  :class:`queue.Queue` instances; the SSE response generator in
  ``app.sse`` reads from them.
"""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .storage import TEMP_FILE_RE

if TYPE_CHECKING:
    from .storage import Storage


#: Debounce window for collapsing event bursts into a single SSE message.
DEBOUNCE_SECONDS: float = 0.1


class EventBus:
    """In-memory single-process pub/sub of ``"change"`` notifications.

    Each subscriber receives its own :class:`queue.Queue` instance; the
    watcher pushes a string onto every queue when an unsuppressed FS event
    has been observed. Subscribers are stored in a list guarded by a lock
    so concurrent subscribe/unsubscribe is safe.
    """

    def __init__(self) -> None:
        self._subscribers: list[queue.Queue[str]] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue[str]:
        q: queue.Queue[str] = queue.Queue()
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue[str]) -> None:
        with self._lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass  # already removed

    def publish(self, message: str) -> None:
        with self._lock:
            subs = list(self._subscribers)  # snapshot to avoid holding the lock
        for q in subs:
            try:
                q.put_nowait(message)
            except queue.Full:  # pragma: no cover - unbounded queue
                pass


class _DebouncedEmitter:
    """Coalesce a burst of ``trigger()`` calls into one publish after a delay.

    Each new trigger resets the timer; only the most recent trigger's
    deadline actually fires. Thread-safe.
    """

    def __init__(self, bus: EventBus, delay_seconds: float) -> None:
        self._bus = bus
        self._delay = delay_seconds
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def trigger(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._delay, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        with self._lock:
            self._timer = None
        self._bus.publish("change")

    def cancel(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None


class _Handler(FileSystemEventHandler):
    """Filter watchdog events and forward survivors to the debounced emitter."""

    def __init__(self, storage: "Storage", emitter: _DebouncedEmitter) -> None:
        self._storage = storage
        self._emitter = emitter

    def on_any_event(self, event: FileSystemEvent) -> None:
        if not self._should_emit(event):
            return
        self._emitter.trigger()

    def _should_emit(self, event: FileSystemEvent) -> bool:
        paths = self._event_paths(event)

        # 1. Skip if no path is *strictly* inside the data root. Reasons:
        #    - macOS FSEvents bubbles ``DirModifiedEvent`` to the watched
        #      root's parent and to the root itself; both are uninformative
        #      (modifications to root just reflect a child change which has
        #      its own event).
        #    - Other spurious events outside root should never reach us, but
        #      this is a cheap safety check.
        root = self._storage.root
        has_interesting = False
        for p in paths:
            try:
                rel = Path(p).relative_to(root)
            except ValueError:
                continue  # outside root
            if rel == Path("."):
                continue  # the root itself
            has_interesting = True
            break
        if not has_interesting:
            return False

        # 2. Atomic-write temp files always indicate an in-flight write that
        #    will resolve to a regular file shortly; ignore on either side
        #    of a rename event.
        for p in paths:
            if TEMP_FILE_RE.match(Path(p).name):
                return False

        # 3. Self-write suppression: skip events for paths the app itself
        #    just wrote (covers both sides of a rename).
        for p in paths:
            if self._storage.was_recently_written(p):
                return False

        return True

    @staticmethod
    def _event_paths(event: FileSystemEvent) -> list[str]:
        paths = [event.src_path]
        dest = getattr(event, "dest_path", None)
        if dest:
            paths.append(dest)
        return paths


class Watcher:
    """Owns the watchdog :class:`Observer` and the FS-event → SSE pipeline.

    Both :meth:`start` and :meth:`stop` are idempotent. The observer thread
    is started as a daemon so a CTRL-C from the dev server cleanly tears
    down the process even if ``stop`` was never called explicitly.
    """

    def __init__(self, storage: "Storage", bus: EventBus) -> None:
        self._storage = storage
        self._bus = bus
        self._emitter = _DebouncedEmitter(bus, DEBOUNCE_SECONDS)
        self._observer: Observer | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._observer is not None:
                return
            observer = Observer()
            observer.schedule(
                _Handler(self._storage, self._emitter),
                str(self._storage.root),
                recursive=True,
            )
            observer.daemon = True
            observer.start()
            self._observer = observer

    def stop(self) -> None:
        with self._lock:
            obs = self._observer
            self._observer = None
        if obs is not None:
            obs.stop()
            obs.join(timeout=2.0)
        self._emitter.cancel()
