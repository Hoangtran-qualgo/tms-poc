# Pattern: see .smoke-scratch/README.md
"""feature-03 / watcher-and-sse / Debouncing (DB1-DB4).

Drives `_DebouncedEmitter` directly with an `EventBus` so the tests
don't depend on `watchdog.Observer` or real FS events.
"""
import pathlib
import queue
import tempfile
import threading
import time

from app.storage import Storage
from app.watcher import DEBOUNCE_SECONDS, EventBus, Watcher, _DebouncedEmitter


# --- DB1: single _DebouncedEmitter instance owned by Watcher ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    bus = EventBus()
    w = Watcher(s, bus)

    assert isinstance(w._emitter, _DebouncedEmitter), (
        f"DB1: Watcher must own a _DebouncedEmitter, got {type(w._emitter).__name__}"
    )
    # Repeated attribute access returns the same instance — there's exactly one.
    assert w._emitter is w._emitter, "DB1: _emitter must be stable across access"
print("PASS  DB1: single _DebouncedEmitter instance owned by Watcher")


# --- DB2: trigger() cancels pending Timer + starts fresh threading.Timer ---
bus = EventBus()
emitter = _DebouncedEmitter(bus, delay_seconds=10.0)  # long delay so timers don't fire mid-test

emitter.trigger()
t1 = emitter._timer
assert isinstance(t1, threading.Timer), (
    f"DB2: trigger() must install a threading.Timer, got {type(t1).__name__}"
)
assert t1.interval == 10.0, f"DB2: timer interval should be the configured delay, got {t1.interval}"
assert not t1.finished.is_set(), "DB2: fresh timer must not be marked finished"

emitter.trigger()
t2 = emitter._timer
assert t2 is not t1, "DB2: second trigger must install a NEW timer"
assert t1.finished.is_set(), (
    "DB2: previous timer must be cancelled by the second trigger (finished.is_set())"
)
assert not t2.finished.is_set(), "DB2: second timer must not be marked finished"

# Cancel cleans up so the daemon timer doesn't outlive the test.
emitter.cancel()
print("PASS  DB2: trigger() cancels pending Timer and starts a fresh threading.Timer(delay, _fire)")


# --- DB3: only the last deadline fires; bursts collapse to one publish ---
bus = EventBus()
q = bus.subscribe()
DELAY = 0.05  # short enough to keep the test fast, large enough to outrun a 10-trigger burst
emitter = _DebouncedEmitter(bus, delay_seconds=DELAY)

# Fire a burst of 10 triggers within ~5 ms (well under the 50 ms window).
for _ in range(10):
    emitter.trigger()

# Wait for the debounce window to elapse, then drain the bus.
time.sleep(DELAY * 3)
messages: list[str] = []
while True:
    try:
        messages.append(q.get_nowait())
    except queue.Empty:
        break

assert len(messages) == 1, (
    f"DB3: burst of 10 triggers must collapse to exactly 1 publish, got {len(messages)}: {messages}"
)
bus.unsubscribe(q)
print("PASS  DB3: burst of N triggers collapses to exactly one publish")


# --- DB4: _fire publishes the literal string "change" ---
bus = EventBus()
q = bus.subscribe()
emitter = _DebouncedEmitter(bus, delay_seconds=DELAY)
emitter.trigger()
msg = q.get(timeout=DELAY + 0.5)
assert msg == "change", f"DB4: published message must be the literal 'change', got {msg!r}"
bus.unsubscribe(q)
print("PASS  DB4: _fire publishes the literal string 'change' on the bus")


# Sanity: the module-level constant is the spec'd value (informational).
assert DEBOUNCE_SECONDS == 0.1, f"DEBOUNCE_SECONDS should be 0.1, got {DEBOUNCE_SECONDS}"
