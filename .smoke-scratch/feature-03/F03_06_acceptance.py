# Pattern: see .smoke-scratch/README.md
"""feature-03 / watcher-and-sse / Acceptance criteria (AC1-AC5)."""
import os
import pathlib
import queue
import tempfile
import time

from app import sse as sse_mod
from app.sse import sse_response
from app.storage import Storage
from app.watcher import DEBOUNCE_SECONDS, EventBus, Watcher


# --- AC1: a user-initiated save produces zero SSE events on any open tab ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    bus = EventBus()
    w = Watcher(s, bus)
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])
    w.start()
    try:
        q = bus.subscribe()
        try:
            # Drain any in-flight events from seeding (shouldn't be any since
            # the start() happened AFTER the seeding, but be defensive).
            time.sleep(0.2)
            while True:
                try:
                    q.get_nowait()
                except queue.Empty:
                    break

            # User-initiated save: every write below marks the target +
            # parent recent, AND uses a TEMP_FILE_RE-matching temp file.
            # The watcher must drop every resulting FS event.
            s.create_file(["proj", "mod", "ac1.feature"], "user save")
            s.write_raw(
                ["proj", "mod", "ac1.feature"],
                "Feature: y\n\n  Scenario: s\n    Given step\n",
            )
            s.delete_file(["proj", "mod", "ac1.feature"])

            # Wait well past DEBOUNCE_SECONDS plus FS-event slack.
            time.sleep(max(DEBOUNCE_SECONDS * 3, 0.5))

            received: list[str] = []
            while True:
                try:
                    received.append(q.get_nowait())
                except queue.Empty:
                    break
            assert received == [], (
                f"AC1: user-initiated saves must produce zero SSE events, got {received}"
            )
        finally:
            bus.unsubscribe(q)
    finally:
        w.stop()
print("PASS  AC1: a user-initiated save produces zero SSE events on any open tab")


# --- AC2: out-of-band edit -> exactly one "change", no sooner than DEBOUNCE_SECONDS ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    bus = EventBus()
    w = Watcher(s, bus)
    s.create_folder(["proj"])
    s.create_folder(["proj", "mod"])
    w.start()
    try:
        q = bus.subscribe()
        try:
            # Two open tabs -> two subscribers; both must receive the event.
            q2 = bus.subscribe()
            try:
                time.sleep(0.2)
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break
                while True:
                    try:
                        q2.get_nowait()
                    except queue.Empty:
                        break

                # External burst (bypass Storage so was_recently_written
                # doesn't suppress). A burst should collapse to ONE event.
                target_dir = root / "proj" / "mod"
                for i in range(5):
                    (target_dir / f"ext_{i}.feature").write_text(
                        f"Feature: ext_{i}\n\n  Scenario: s\n    Given step\n"
                    )
                t_last_write = time.monotonic()

                # Both subscribers receive exactly one "change".
                msg1 = q.get(timeout=3.0)
                t_msg = time.monotonic()
                msg2 = q2.get(timeout=3.0)
                assert msg1 == "change", f"AC2: q1 message must be 'change', got {msg1!r}"
                assert msg2 == "change", f"AC2: q2 message must be 'change', got {msg2!r}"

                # No additional events arrive in the next debounce window.
                time.sleep(DEBOUNCE_SECONDS * 3)
                extra1: list[str] = []
                extra2: list[str] = []
                while True:
                    try:
                        extra1.append(q.get_nowait())
                    except queue.Empty:
                        break
                while True:
                    try:
                        extra2.append(q2.get_nowait())
                    except queue.Empty:
                        break
                assert extra1 == [] and extra2 == [], (
                    f"AC2: burst must collapse to ONE event per tab, got extras q1={extra1}, q2={extra2}"
                )

                # Timing lower bound: the publish must arrive no sooner than
                # DEBOUNCE_SECONDS after the last write (10% slack approved).
                delta = t_msg - t_last_write
                assert delta >= DEBOUNCE_SECONDS * 0.9, (
                    f"AC2: 'change' arrived too early; delta={delta:.4f}s, "
                    f"expected >= DEBOUNCE_SECONDS * 0.9 = {DEBOUNCE_SECONDS * 0.9:.4f}s"
                )
            finally:
                bus.unsubscribe(q2)
        finally:
            bus.unsubscribe(q)
    finally:
        w.stop()
print(
    "PASS  AC2: out-of-band edit -> exactly one 'change' per open tab, "
    "no sooner than DEBOUNCE_SECONDS after last write"
)


# --- AC3: closing a browser tab unsubscribes its queue (EventBus._subscribers shrinks) ---
bus = EventBus()
assert len(bus._subscribers) == 0, "AC3 setup: bus must start empty"

# Two "tabs" open simultaneously.
r1 = sse_response(bus)
r2 = sse_response(bus)
assert len(bus._subscribers) == 2, (
    f"AC3: two SSE responses must subscribe two queues, got {len(bus._subscribers)}"
)

# Iterate each one chunk so the try: block is entered, then close one.
gen1 = r1.response
gen2 = r2.response
next(gen1)
next(gen2)
gen1.close()
assert len(bus._subscribers) == 1, (
    f"AC3: closing one SSE generator must unsubscribe exactly one queue; "
    f"_subscribers={len(bus._subscribers)}"
)
gen2.close()
assert len(bus._subscribers) == 0, (
    f"AC3: closing the second SSE generator must unsubscribe the remaining queue; "
    f"_subscribers={len(bus._subscribers)}"
)
print("PASS  AC3: closing a browser tab unsubscribes its queue (EventBus._subscribers length)")


# --- AC4: an idle connection receives `: heartbeat\n\n` every HEARTBEAT_INTERVAL_SECONDS ---
original = sse_mod.HEARTBEAT_INTERVAL_SECONDS
try:
    sse_mod.HEARTBEAT_INTERVAL_SECONDS = 0.08
    bus = EventBus()
    response = sse_response(bus)
    gen = response.response
    assert next(gen) == b": connected\n\n"

    intervals: list[float] = []
    t_prev = time.monotonic()
    for _ in range(3):
        chunk = next(gen)
        t_now = time.monotonic()
        assert chunk == b": heartbeat\n\n", (
            f"AC4: idle chunk must be b': heartbeat\\n\\n', got {chunk!r}"
        )
        intervals.append(t_now - t_prev)
        t_prev = t_now

    gen.close()

    for i, dt in enumerate(intervals):
        assert dt >= 0.08 * 0.9, (
            f"AC4: heartbeat #{i+1} arrived too early; dt={dt:.4f}s, "
            f"expected >= HEARTBEAT_INTERVAL_SECONDS * 0.9 = {0.08 * 0.9:.4f}s"
        )
finally:
    sse_mod.HEARTBEAT_INTERVAL_SECONDS = original
print("PASS  AC4: an idle connection receives ': heartbeat\\n\\n' every HEARTBEAT_INTERVAL_SECONDS")


# --- AC5: Watcher.start() and Watcher.stop() are idempotent ---
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td).resolve()
    s = Storage(root)
    bus = EventBus()
    w = Watcher(s, bus)

    # stop() before start() is a no-op (idempotent on the "stopped" side).
    w.stop()
    assert w._observer is None, "AC5: stop() before start() must be a no-op"

    # First start() creates the observer.
    w.start()
    obs_first = w._observer
    assert obs_first is not None and obs_first.is_alive(), "AC5 setup: first start must run"

    # Second start() must NOT create a second observer (the if-guard in start()).
    w.start()
    assert w._observer is obs_first, (
        "AC5: second start() must reuse the existing observer (no double-start)"
    )
    assert obs_first.is_alive(), "AC5: original observer must still be alive after second start()"

    # First stop() tears down.
    w.stop()
    assert w._observer is None, "AC5: stop() must reset _observer to None"
    assert not obs_first.is_alive(), "AC5: original observer thread must die on first stop()"

    # Second stop() must NOT raise.
    w.stop()
    assert w._observer is None, "AC5: second stop() must remain a no-op"
print("PASS  AC5: Watcher.start() and Watcher.stop() are idempotent")
